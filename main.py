# main.py
from categorization import get_category

import os
import requests

API_KEY = "RGAPI-c2136e39-47f7-4df0-8f85-d8f7b6bf5ae0"

if not API_KEY:
    raise ValueError("API key not found. Make sure it's set in .env as RIOT_API_KEY")

# ------------------------------
# CONFIG - CHANGE THESE
GAME_NAME = "penes envy"  # Riot ID (Game Name)
TAG_LINE = "eee"             # Riot ID Tagline
GAME_ID = "penes%20envy"
REGION = "europe"            # For Match-V5
PLATFORM = "euw1"            # For Account API
NUM_MATCHES = 5              # How many matches to fetch
# ------------------------------

# Step 1: Get PUUID from Riot ID
account_url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{GAME_ID}/{TAG_LINE}"
res = requests.get(account_url, headers={"X-Riot-Token": API_KEY})

if res.status_code != 200:
    raise Exception(f"Failed to get account info: {res.text}")

account_data = res.json()
puuid = account_data["puuid"]
print(f"PUUID for {GAME_NAME}#{TAG_LINE}: {puuid}")

# Step 2: Get Match IDs (Diamond Ranked Solo queueId=420)
matches_url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count={NUM_MATCHES}&queue=420"
res = requests.get(matches_url, headers={"X-Riot-Token": API_KEY})

if res.status_code != 200:
    raise Exception(f"Failed to get match IDs: {res.text}")

match_ids = res.json()
print(f"Found {len(match_ids)} Ranked Solo matches.")

# Step 3: Fetch match details
# Step 3: Fetch match details
for match_id in match_ids:
    match_url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    res = requests.get(match_url, headers={"X-Riot-Token": API_KEY})
    if res.status_code != 200:
        print(f"Failed to fetch match {match_id}")
        continue
    match_data = res.json()
    info = match_data["info"]

    # find our player
    me = next(p for p in info["participants"] if p["puuid"] == puuid)
    my_team_id = me["teamId"]

    # split teams
    allies = [p["championName"] for p in info["participants"] if p["teamId"] == my_team_id]
    enemies = [p["championName"] for p in info["participants"] if p["teamId"] != my_team_id]

    # convert champion names to categories
    allies_categories = [get_category(champ) for champ in allies]
    enemies_categories = [get_category(champ) for champ in enemies]

    # win/lose
    did_win = me["win"]

    print(f"\nMatch {match_id}")
    print(f"Played: {me['championName']} ({me['individualPosition']})")
    print(f"Allies (categories): {allies_categories}")
    print(f"Enemies (categories): {enemies_categories}")
    print(f"Result: {'WIN' if did_win else 'LOSS'}")