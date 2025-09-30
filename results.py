import sqlite3

conn = sqlite3.connect("team_comps.db")
cur = conn.cursor()

rows = cur.execute("""
    SELECT comp, wins, losses, winrate, (wins+losses) as games
    FROM team_comps
    ORDER BY games DESC
    LIMIT 50
""").fetchall()

for row in rows:
    print(row)

conn.close()
