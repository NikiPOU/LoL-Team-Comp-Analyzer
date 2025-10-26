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
                request.form.get("champ1"),
                request.form.get("champ2"),
                request.form.get("champ3"),
                request.form.get("champ4"),
                request.form.get("champ5"),
            ]
            champions = [c for c in champions if c]
            categories = sorted([get_category(c) for c in champions])
        elif search_mode == "category":
            categories = [
                request.form.get("role1"),
                request.form.get("role2"),
                request.form.get("role3"),
                request.form.get("role4"),
                request.form.get("role5"),
            ]
            categories = sorted([c for c in categories if c])
        else:
            categories = []


        if len(categories) == 5:
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
                    "categories": categories,
                    "wins": wins,
                    "losses": losses,
                    "winrate": f"{winrate * 100:.2f}%",
                    "games": total_games
                }
            else:
                message = "No data found for this composition."
        else:
            message = "Please select 5 champions or categories before searching."

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
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT comp, wins, losses, winrate, (wins + losses) AS games
        FROM team_comps
        WHERE wins + losses > 0
        ORDER BY winrate DESC
        LIMIT 20
    """)
    comps = cur.fetchall()
    conn.close()
    return render_template("leaderboard.html", comps=comps)


if __name__ == "__main__":
    app.run(debug=True)
