import sqlite3
import os
from typing import Any, Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "api_monitor.db")


def _connect():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    con = _connect()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS runs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      started_at TEXT NOT NULL,
      finished_at TEXT NOT NULL,
      ok INTEGER NOT NULL,
      total_requests INTEGER NOT NULL,
      error_requests INTEGER NOT NULL,
      lat_avg_ms REAL,
      lat_p95_ms REAL,
      error_rate REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS requests (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      run_id INTEGER NOT NULL,
      name TEXT NOT NULL,
      method TEXT NOT NULL,
      path TEXT NOT NULL,
      status_code INTEGER,
      latency_ms REAL,
      ok INTEGER NOT NULL,
      error_type TEXT,
      error_message TEXT,
      FOREIGN KEY(run_id) REFERENCES runs(id)
    )
    """)

    con.commit()
    con.close()


def save_run(run: Dict[str, Any]) -> int:
    """
    run = {
      "started_at": str, "finished_at": str,
      "ok": bool,
      "metrics": {"lat_avg_ms":float|None, "lat_p95_ms":..., "error_rate":...},
      "checks": [ {name, method, path, status_code, latency_ms, ok, error_type, error_message}, ...]
    }
    """
    init_db()

    con = _connect()
    cur = con.cursor()

    checks = run["checks"]
    total = len(checks)
    errors = sum(1 for c in checks if not c["ok"])

    m = run["metrics"]
    cur.execute(
        """INSERT INTO runs(started_at, finished_at, ok, total_requests, error_requests, lat_avg_ms, lat_p95_ms, error_rate)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            run["started_at"],
            run["finished_at"],
            1 if run["ok"] else 0,
            total,
            errors,
            m.get("lat_avg_ms"),
            m.get("lat_p95_ms"),
            m.get("error_rate"),
        ),
    )
    run_id = cur.lastrowid

    cur.executemany(
        """INSERT INTO requests(run_id, name, method, path, status_code, latency_ms, ok, error_type, error_message)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        [
            (
                run_id,
                c["name"],
                c["method"],
                c["path"],
                c.get("status_code"),
                c.get("latency_ms"),
                1 if c["ok"] else 0,
                c.get("error_type"),
                c.get("error_message"),
            )
            for c in checks
        ],
    )

    con.commit()
    con.close()
    return run_id


def list_runs(limit: int = 50) -> List[Dict[str, Any]]:
    init_db()
    con = _connect()
    cur = con.cursor()
    cur.execute(
        """SELECT id, started_at, finished_at, ok, total_requests, error_requests, lat_avg_ms, lat_p95_ms, error_rate
           FROM runs ORDER BY id DESC LIMIT ?""",
        (limit,),
    )
    rows = cur.fetchall()
    con.close()

    out = []
    for r in rows:
        out.append({
            "id": r[0],
            "started_at": r[1],
            "finished_at": r[2],
            "ok": bool(r[3]),
            "total_requests": r[4],
            "error_requests": r[5],
            "lat_avg_ms": r[6],
            "lat_p95_ms": r[7],
            "error_rate": r[8],
        })
    return out


def get_run(run_id: int) -> Optional[Dict[str, Any]]:
    init_db()
    con = _connect()
    cur = con.cursor()

    cur.execute(
        """SELECT id, started_at, finished_at, ok, total_requests, error_requests, lat_avg_ms, lat_p95_ms, error_rate
           FROM runs WHERE id=?""",
        (run_id,),
    )
    row = cur.fetchone()
    if not row:
        con.close()
        return None

    cur.execute(
        """SELECT name, method, path, status_code, latency_ms, ok, error_type, error_message
           FROM requests WHERE run_id=? ORDER BY id ASC""",
        (run_id,),
    )
    reqs = cur.fetchall()
    con.close()

    return {
        "id": row[0],
        "started_at": row[1],
        "finished_at": row[2],
        "ok": bool(row[3]),
        "total_requests": row[4],
        "error_requests": row[5],
        "lat_avg_ms": row[6],
        "lat_p95_ms": row[7],
        "error_rate": row[8],
        "requests": [
            {
                "name": rr[0],
                "method": rr[1],
                "path": rr[2],
                "status_code": rr[3],
                "latency_ms": rr[4],
                "ok": bool(rr[5]),
                "error_type": rr[6],
                "error_message": rr[7],
            }
            for rr in reqs
        ],
    }