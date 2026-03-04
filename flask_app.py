# app = Flask(__name__)

# @app.get("/")
# def consignes():
#      return render_template('consignes.html')

# if __name__ == "__main__":
#     # utile en local uniquement
#     app.run(host="0.0.0.0", port=5000, debug=True)

from flask import Flask, render_template_string, render_template, jsonify, request, redirect, url_for, session
from flask import render_template
from flask import json
from urllib.request import urlopen
from werkzeug.utils import secure_filename
import sqlite3
from storage import init_db, list_runs, get_run






app = Flask(__name__)


init_db()

@app.get("/")
def dashboard():
    runs = list_runs(limit=30)
    last = runs[0] if runs else None
    last_full = get_run(last["id"]) if last else None
    return render_template("dashboard.html", runs=runs, last_run=last_full)


@app.get("/run/<int:run_id>")
def run_detail(run_id: int):
    r = get_run(run_id)
    if not r:
        return "Not found", 404
    runs = list_runs(limit=30)
    return render_template("dashboard.html", runs=runs, last_run=r)


@app.get("/api/last")
def api_last():
    runs = list_runs(limit=1)
    if not runs:
        return jsonify({"error": "no runs yet"})
    r = get_run(runs[0]["id"])
    return jsonify(r)


if __name__ == "__main__":
    app.run(debug=True)
