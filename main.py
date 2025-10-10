import os
import requests
import sqlite3
import random
import time
from dotenv import load_dotenv

from categorization import get_category

load_dotenv()
API_KEY = os.getenv("RIOT_API_KEY")
if not API_KEY:
    raise ValueError("API key not found. Make sure it's set in .env as RIOT_API_KEY")

# ------------------------------
GAME_NAME = "Tbiggy"  # Riot ID (Game Name)
TAG_LINE = "77777"          # Riot ID Tagline
NUM_MATCHES = 5           # How many matches to fetch per account
# ------------------------------

collected_matches = set() #?
players = set()
ids_to_process = [(GAME_NAME, TAG_LINE)] #?

#Store raw match data gathered from match
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

#  Team compositions data
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
team_conn.commit()

while len(collected_matches) < 2000 and ids_to_process:
    GAME_NAME, TAG_LINE = random.choice(ids_to_process)
    ids_to_process.remove((GAME_NAME, TAG_LINE))
    if (GAME_NAME, TAG_LINE) in players:
        continue
    players.add((GAME_NAME, TAG_LINE))

    URL_GAME_NAME = GAME_NAME.replace(" ", "%20")
    account_url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{URL_GAME_NAME}/{TAG_LINE}"
    
    res = requests.get(account_url, headers={"X-Riot-Token": API_KEY})
    
    if res.status_code == 429:
        print("Rate limit exceeded, sleeping for two minutes.")
        time.sleep(120)
        continue
    
    if res.status_code != 200:
        print(f"Failed to get account info: {res.text}")
        continue

    puuid = res.json()["puuid"]
    print(f"PUUID for {GAME_NAME}#{TAG_LINE}: {puuid}")
    # ------------------------------
    # Step 2: Get Match IDs
    # ------------------------------
    matches_url = f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count={NUM_MATCHES}&queue=420"
    res = requests.get(matches_url, headers={"X-Riot-Token": API_KEY})
    
    if res.status_code == 429:
        print("Rate limit exceeded, sleeping for two minutes")
        time.sleep(120)
        continue
    
    if res.status_code != 200:
        raise Exception(f"Failed to get match IDs: {res.text}")
    match_ids = res.json()
    print(f"Found {len(match_ids)} Ranked Solo matches.")

    # ------------------------------
    # Step 4: Fetch & Store Matches
    # ------------------------------
    for match_id in match_ids:
        # Skip if match already exists in raw DB
        cur.execute("SELECT 1 FROM matches WHERE Match = ?", (match_id,))
        if cur.fetchone():
            print(f"Skipping match {match_id}, already in match_data.db")
            continue
        
        if match_id in collected_matches:
            continue
    
        # Fetch match details
        match_url = f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}"
        res = requests.get(match_url, headers={"X-Riot-Token": API_KEY})
        
        if res.status_code == 429:
            print("Rate limit exceeded, sleeping for two minutes")
            time.sleep(120)
            continue
        
        if res.status_code != 200:
            print(f"Failed to fetch match {match_id}")
            continue

        info = res.json()["info"]

        blue_team = [p["championName"] for p in info["participants"] if p["teamId"] == 100]
        red_team = [p["championName"] for p in info["participants"] if p["teamId"] == 200]

        blue_categories = sorted([get_category(c) for c in blue_team])
        red_categories = sorted([get_category(c) for c in red_team])

        # 0 = blue win, 1 = red win
        #I redid this because order is not guaranteed and the first person in the list is not guaranteed to be blue/red
        #game_result = 0 if info["participants"][0]["win"] else 1

        # Find which team won first
        team_that_won = next(team for team in info["teams"] if team["win"])

        # 0 = blue win, 1 = red win
        game_result = 0 if team_that_won["teamId"] == 100 else 1

        print(f"\nMatch {match_id}")
        print(f"Blue: {blue_categories}")
        print(f"Red: {red_categories}")
        print(f"Result: {'RED WIN' if game_result else 'BLUE WIN'} --> {game_result}")

        for player in info["participants"]:
            player_id = (player["riotIdGameName"], player["riotIdTagline"])
            if player_id not in players and player_id not in ids_to_process:
                ids_to_process.append(player_id)
        
        collected_matches.add(match_id)

        # Store in raw DB
        cur.execute(
            "INSERT OR IGNORE INTO matches (Match, BlueTeam, RedTeam, Result) VALUES (?, ?, ?, ?)",
            (match_id, str(blue_categories), str(red_categories), game_result)
        )
        conn.commit()

# ------------------------------
# Step 5: Rebuild team_comps from all matches
# ------------------------------
team_cur.execute("DELETE FROM team_comps")  # clear old aggregated data

all_matches = cur.execute("SELECT BlueTeam, RedTeam, Result FROM matches").fetchall()
for blue_str, red_str, result in all_matches:
    blue_comp = blue_str
    red_comp = red_str

    if result == 0:  # blue won
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
WHERE wins + losses > 0
""")

team_conn.commit()

# ------------------------------
# Step 6: Close DBs
# ------------------------------
conn.close()
team_conn.close()
