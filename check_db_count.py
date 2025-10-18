import sqlite3

conn = sqlite3.connect("match_data.db")
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM matches")
count = cur.fetchone()[0]

print(f"Number of matches stored: {count}")

conn.close()
