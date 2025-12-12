from flask import Flask, render_template, request, redirect
import sqlite3
import os

app = Flask(__name__)

# ---------------------------
# DATABASE INITIALIZATION
# ---------------------------

# Render: persistenter Speicherort
DB = "/var/data/database1.db"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    # Datenbank erzeugen falls noch NICHT existiert
    if not os.path.exists(DB):
        conn = get_db()
        conn.execute("""
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT
            );
        """)
        conn.execute("""
            CREATE TABLE steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                step_name TEXT,
                status TEXT,
                note TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );
        """)
        conn.commit()
        conn.close()


# ---------------------------
# ROUTES
# ---------------------------

@app.route("/")
def index():
    db = get_db()
    projects = db.execute("SELECT * FROM projects").fetchall()

    # Status-Priorität
    status_priority = {"fehler": 4, "hinweis": 3, "offen": 2, "erledigt": 1}
    project_statuses = []

    for p in projects:
        steps = db.execute("SELECT status FROM steps WHERE project_id=?", (p["id"],)).fetchall()
        worst_status = "erledigt"
        worst_priority = 1

        for s in steps:
            if status_priority[s["status"]] > worst_priority:
                worst_priority = status_priority[s["status"]]
                worst_status = s["status"]

        project_statuses.append({"project": p, "worst_status": worst_status})

    return render_template("index.html", project_statuses=project_statuses)


@app.route("/add_project", methods=["POST"])
def add_project():
    name = request.form["name"]
    db = get_db()
    cur = db.cursor()
    cur.execute("INSERT INTO projects (name) VALUES (?)", (name,))
    project_id = cur.lastrowid

    steps = [
        "Arbeitsschritt 1",
        "Arbeitsschritt 2",
        "Arbeitsschritt 3",
        "Arbeitsschritt 4",
        "Arbeitsschritt 5"
    ]

    for s in steps:
        cur.execute("INSERT INTO steps (project_id, step_name, status) VALUES (?, ?, ?)",
                    (project_id, s, "offen"))

    db.commit()
    return redirect("/")


@app.route("/project/<int:id>")
def project(id):
    db = get_db()
    project = db.execute("SELECT * FROM projects WHERE id=?", (id,)).fetchone()
    steps = db.execute("SELECT * FROM steps WHERE project_id=?", (id,)).fetchall()
    return render_template("project.html", project=project, steps=steps)


@app.route("/update_step", methods=["POST"])
def update_step():
    step_id = request.form["step_id"]
    status = request.form["status"]

    db = get_db()
    db.execute("UPDATE steps SET status=? WHERE id=?", (status, step_id))
    db.commit()

    project_id = request.form["project_id"]
    return redirect(f"/project/{project_id}")


@app.route("/save_steps", methods=["POST"])
def save_steps():
    project_id = request.form["project_id"]
    db = get_db()

    for key in request.form:
        if key.startswith("status_"):
            step_id = key.split("_")[1]
            new_status = request.form[key]
            note_key = f"note_{step_id}"
            note = request.form.get(note_key, "")
            db.execute("UPDATE steps SET status=?, note=? WHERE id=?", (new_status, note, step_id))

    db.commit()
    return redirect(f"/project/{project_id}")


@app.route("/delete_project", methods=["POST"])
def delete_project():
    project_id = request.form["project_id"]

    db = get_db()
    steps = db.execute(
        "SELECT status FROM steps WHERE project_id=?",
        (project_id,)
    ).fetchall()

    if any(s["status"] != "erledigt" for s in steps):
        return "Projekt kann nicht gelöscht werden: nicht alle Schritte sind erledigt.", 400

    db.execute("DELETE FROM steps WHERE project_id=?", (project_id,))
    db.execute("DELETE FROM projects WHERE id=?", (project_id,))
    db.commit()

    return redirect("/")


@app.route("/new_project", methods=["GET", "POST"])
def new_project():
    default_steps = [
        "V1 Messung",
        "V2 Messung",
        "V3 Messung",
        "Vormessungen",
        "Prüfung",
        "Nachmessung"
    ]

    if request.method == "POST":
        name = request.form["name"]
        steps_selected = request.form.getlist("default_step")
        extra_steps = request.form.getlist("extra_step")
        all_steps = steps_selected + [s.strip() for s in extra_steps if s.strip()]

        db = get_db()
        cur = db.cursor()
        cur.execute("INSERT INTO projects (name) VALUES (?)", (name,))
        project_id = cur.lastrowid

        for step in all_steps:
            cur.execute(
                "INSERT INTO steps (project_id, step_name, status) VALUES (?, ?, ?)",
                (project_id, step, "offen")
            )

        db.commit()
        return redirect(f"/project/{project_id}")

    return render_template("new_project.html", default_steps=default_steps)


# ----------------------
# RENDER STARTUP
# ----------------------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
