import os
import requests
import sqlite3
from dotenv import load_dotenv

from categorization import get_category

load_dotenv()
API_KEY = os.getenv("RIOT_API_KEY")

if not API_KEY:
    raise ValueError("API key not found. Make sure it's set in .env as RIOT_API_KEY")

# ------------------------------
# CONFIG - CHANGE THESE
GAME_NAME = "Myoutaros"  # Riot ID (Game Name)
TAG_LINE = "EUW"          # Riot ID Tagline
NUM_MATCHES = 5           # How many matches to fetch
# ------------------------------

URL_GAME_NAME = GAME_NAME.replace(" ", "%20")

# Step 1: Get PUUID from Riot ID
account_url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{URL_GAME_NAME}/{TAG_LINE}"
res = requests.get(account_url, headers={"X-Riot-Token": API_KEY})
if res.status_code != 200:
    raise Exception(f"Failed to get account info: {res.text}")

account_data = res.json()
puuid = account_data["puuid"]
print(f"PUUID for {GAME_NAME}#{TAG_LINE}: {puuid}")

# Step 2: Get Match IDs (Ranked Solo queueId=420)
matches_url = f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count={NUM_MATCHES}&queue=420"
res = requests.get(matches_url, headers={"X-Riot-Token": API_KEY})
if res.status_code != 200:
    raise Exception(f"Failed to get match IDs: {res.text}")

match_ids = res.json()
print(f"Found {len(match_ids)} Ranked Solo matches.")

# ------------------------------
# Database: match_data.db (raw matches)
# ------------------------------
conn = sqlite3.connect("match_data.db")
cur = conn.cursor()
cur.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        Match TEXT PRIMARY KEY,
        BlueTeam TEXT,
        RedTeam TEXT,
        Result INTEGER
    )
""")
conn.commit()

# ------------------------------
# Database: team_comps.db (aggregated comps)
# ------------------------------
team_conn = sqlite3.connect("team_comps.db")
team_cur = team_conn.cursor()
team_cur.execute("""
    CREATE TABLE IF NOT EXISTS team_comps (
        comp TEXT PRIMARY KEY,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        winrate REAL DEFAULT 0
    )
""")
team_cur.execute("""
    CREATE TABLE IF NOT EXISTS processed_matches (
        match_id TEXT PRIMARY KEY
    )
""")
team_conn.commit()

# ------------------------------
# Step 3: Process matches
# ------------------------------
for match_id in match_ids:
    # Skip if already processed in team_comps
    team_cur.execute("SELECT 1 FROM processed_matches WHERE match_id = ?", (match_id,))
    if team_cur.fetchone():
        print(f"Skipping match {match_id}, already processed in team_comps.")
        continue

    # Fetch match details
    match_url = f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}"
    res = requests.get(match_url, headers={"X-Riot-Token": API_KEY})
    if res.status_code != 200:
        print(f"Failed to fetch match {match_id}")
        continue

    match_data = res.json()
    info = match_data["info"]

    # Split teams into blue and red
    blue_team = [p["championName"] for p in info["participants"] if p["teamId"] == 100]
    red_team = [p["championName"] for p in info["participants"] if p["teamId"] == 200]

    # Convert champion names to categories
    blue_team_categories = sorted([get_category(champ) for champ in blue_team])
    red_team_categories = sorted([get_category(champ) for champ in red_team])

    # Determine winner: 0 = blue win, 1 = red win
    game_result = 0 if info["participants"][0]["win"] else 1

    print(f"\nMatch {match_id}")
    print(f"Blue team (categories): {blue_team_categories}")
    print(f"Red team (categories): {red_team_categories}")
    print(f"Result: {'RED WIN' if game_result else 'BLUE WIN'} --> {game_result}")

    # Store match info in raw DB
    cur.execute("INSERT OR IGNORE INTO matches (Match, BlueTeam, RedTeam, Result) VALUES (?, ?, ?, ?)",
                (match_id, str(blue_team_categories), str(red_team_categories), game_result))
    conn.commit()

    # Update team_comps
    blue_comp = str(blue_team_categories)
    red_comp = str(red_team_categories)

    if game_result == 0:  # blue won
        team_cur.execute("""
            INSERT INTO team_comps (comp, wins, losses)
            VALUES (?, 1, 0)
            ON CONFLICT(comp) DO UPDATE SET wins = wins + 1
        """, (blue_comp,))
        team_cur.execute("""
            INSERT INTO team_comps (comp, wins, losses)
            VALUES (?, 0, 1)
            ON CONFLICT(comp) DO UPDATE SET losses = losses + 1
        """, (red_comp,))
    else:  # red won
        team_cur.execute("""
            INSERT INTO team_comps (comp, wins, losses)
            VALUES (?, 0, 1)
            ON CONFLICT(comp) DO UPDATE SET losses = losses + 1
        """, (blue_comp,))
        team_cur.execute("""
            INSERT INTO team_comps (comp, wins, losses)
            VALUES (?, 1, 0)
            ON CONFLICT(comp) DO UPDATE SET wins = wins + 1
        """, (red_comp,))

    # Update winrates
    team_cur.execute("""
        UPDATE team_comps
        SET winrate = CAST(wins AS REAL) / (wins + losses)
        WHERE wins + losses > 0;
    """)

    # Mark match as processed
    team_cur.execute("INSERT INTO processed_matches (match_id) VALUES (?)", (match_id,))

    team_conn.commit()

# Close databases
conn.close()
team_conn.close()
