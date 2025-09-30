import sqlite3

# Create (or open) the database file
conn = sqlite3.connect("team_comps.db")
cur = conn.cursor()

# Create the table to store unique comps and their win/loss counts
cur.execute("""
CREATE TABLE IF NOT EXISTS team_comps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comp TEXT UNIQUE,         -- stringified list of 5 categories
    wins INTEGER DEFAULT 0,   -- how many times this comp won
    losses INTEGER DEFAULT 0  -- how many times this comp lost
)
""")

conn.commit()
conn.close()

print("✅ Database team_comps.db initialized with table 'team_comps'")
