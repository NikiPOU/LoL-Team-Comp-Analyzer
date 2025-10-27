from flask import Flask, render_template, request
import sqlite3
from categorization import get_category, champion_roles

app = Flask(__name__)
DB_PATH = "team_comps.db"


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    message = None
    search_mode = None

    if request.method == "POST":
        search_mode = request.form.get("mode")

        if search_mode == "champion":
            champions = [
                request.form.get(f"champ{i}") for i in range(1, 6)
            ]
            champions = [c for c in champions if c]
            categories = sorted([get_category(c) for c in champions])

        elif search_mode == "category":
            categories = [
                request.form.get(f"category{i}") for i in range(1, 6)
            ]
            categories = sorted([c for c in categories if c])

        else:
            categories = []

        if len(categories) < 5:
            message = "Please select 5 champions or categories before searching."
        else:
            comp = str(categories)

            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT wins, losses, winrate FROM team_comps WHERE comp = ?", (comp,))
            row = cur.fetchone()
            conn.close()

            if row:
                wins, losses, winrate = row
                total_games = wins + losses
                result = {
                    "categories": ", ".join(categories),
                    "wins": wins,
                    "losses": losses,
                    "winrate": f"{winrate * 100:.2f}%",
                    "games": total_games
                }
            else:
                message = f"No data found for composition: {', '.join(categories)}"

    categories_list = sorted(set(champion_roles.values()))
    champions_list = sorted(champion_roles.keys())

    return render_template(
        "index.html",
        result=result,
        message=message,
        categories=categories_list,
        champions=champions_list,
        search_mode=search_mode
    )


@app.route("/leaderboard")
def leaderboard():
    sort_by = request.args.get("sort", "winrate")
    min_games = int(request.args.get("min_games", 0))
    limit = int(request.args.get("limit", 20))

    valid_sorts = {"winrate": "winrate DESC", "games": "games DESC"}
    sort_order = valid_sorts.get(sort_by, "winrate DESC")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(f"""
        SELECT comp, wins, losses, winrate, (wins + losses) AS games
        FROM team_comps
        WHERE (wins + losses) >= ?
        ORDER BY {sort_order}
        LIMIT ?
    """, (min_games, limit))
    comps = cur.fetchall()
    conn.close()

    comps = [
        (comp.strip("[]").replace("'", "").replace(",", ","), wins, losses, winrate, games)
        for comp, wins, losses, winrate, games in comps
    ]

    return render_template(
        "leaderboard.html",
        comps=comps,
        sort_by=sort_by,
        min_games=min_games,
        limit=limit
    )


if __name__ == "__main__":
    app.run(debug=True)
