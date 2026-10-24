"""SQLite store (stdlib sqlite3). One file for the prototype; production is
DynamoDB + S3 Object Lock (SPEC section 7). Writes are serialised with a lock."""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS contacts (user_id TEXT, contact_hash TEXT, label TEXT, PRIMARY KEY(user_id, contact_hash));
CREATE TABLE IF NOT EXISTS payee_history (user_id TEXT, payee_vpa TEXT, count INTEGER, usual_amount REAL,
    PRIMARY KEY(user_id, payee_vpa));
CREATE TABLE IF NOT EXISTS devices (device_id TEXT PRIMARY KEY, user_id TEXT, public_key_b64 TEXT, bound_at TEXT);
CREATE TABLE IF NOT EXISTS mock_fri (number TEXT PRIMARY KEY, tier TEXT);
CREATE TABLE IF NOT EXISTS mock_i4c (vpa TEXT PRIMARY KEY, level TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS mock_bank_calls (customer_id TEXT, number TEXT, active INTEGER, started_at TEXT);
CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, created_at TEXT, updated_at TEXT, payer_id TEXT,
    status TEXT, tier TEXT, p REAL, amount REAL, scenario TEXT, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events (case_id TEXT, seq INTEGER, ts TEXT, type TEXT, actor TEXT, data TEXT,
    prev_hash TEXT, hash TEXT, PRIMARY KEY(case_id, seq));
CREATE TABLE IF NOT EXISTS challenges (id TEXT PRIMARY KEY, case_id TEXT, relative_id TEXT, device_id TEXT,
    nonce TEXT, created_at TEXT, expires_at TEXT, status TEXT, answer TEXT, signature TEXT, message TEXT);
CREATE TABLE IF NOT EXISTS access_log (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, actor TEXT, role TEXT,
    case_id TEXT, action TEXT, reason TEXT);
CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, case_id TEXT, label TEXT,
    analyst TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS counters (name TEXT PRIMARY KEY, value INTEGER);
CREATE TABLE IF NOT EXISTS sent_payments (payer_id TEXT, ts TEXT, amount REAL, payee_vpa TEXT, caller TEXT);
CREATE TABLE IF NOT EXISTS payment_refs (ref TEXT PRIMARY KEY, payer_id TEXT, created_at TEXT, amount REAL,
    payee_vpa TEXT, caller TEXT, sent_at TEXT);
"""

RESETTABLE = ["users", "contacts", "payee_history", "mock_fri", "mock_i4c", "mock_bank_calls", "cases",
              "events", "challenges", "feedback", "counters", "sent_payments", "payment_refs"]


class Store:
    def __init__(self, path: str | Path = ":memory:"):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL" if path != ":memory:" else "PRAGMA journal_mode=MEMORY")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.lock = threading.RLock()
        self.conn.executescript(SCHEMA)

    # generic -----------------------------------------------------------
    def x(self, sql: str, args: tuple | list = ()) -> sqlite3.Cursor:
        with self.lock:
            return self.conn.execute(sql, args)

    def one(self, sql: str, args: tuple | list = ()) -> sqlite3.Row | None:
        with self.lock:
            return self.conn.execute(sql, args).fetchone()

    def all(self, sql: str, args: tuple | list = ()) -> list[sqlite3.Row]:
        with self.lock:
            return self.conn.execute(sql, args).fetchall()

    def reset(self, keep_devices: bool = True) -> None:
        with self.lock:
            for t in RESETTABLE:
                self.conn.execute(f"DELETE FROM {t}")
            if not keep_devices:
                self.conn.execute("DELETE FROM devices")

    def next_counter(self, name: str) -> int:
        with self.lock:
            row = self.conn.execute("SELECT value FROM counters WHERE name=?", (name,)).fetchone()
            v = (row["value"] if row else 0) + 1
            self.conn.execute("INSERT OR REPLACE INTO counters(name, value) VALUES(?,?)", (name, v))
            return v

    # users ---------------------------------------------------------------
    def put_user(self, user: dict) -> None:
        self.x("INSERT OR REPLACE INTO users(id, data) VALUES(?,?)", (user["id"], json.dumps(user, ensure_ascii=False)))

    def get_user(self, uid: str) -> dict | None:
        r = self.one("SELECT data FROM users WHERE id=?", (uid,))
        return json.loads(r["data"]) if r else None

    # cases ---------------------------------------------------------------
    def put_case(self, case: dict) -> None:
        self.x(
            "INSERT OR REPLACE INTO cases(id, created_at, updated_at, payer_id, status, tier, p, amount, scenario, data)"
            " VALUES(?,?,?,?,?,?,?,?,?,?)",
            (case["case_id"], case["created_at_ist"], case.get("updated_at_ist"), case.get("payer_id"),
             case.get("status"), case.get("tier"), case.get("p"), case.get("amount_inr"), case.get("scenario"),
             json.dumps(case, ensure_ascii=False)),
        )

    def get_case(self, cid: str) -> dict | None:
        r = self.one("SELECT data FROM cases WHERE id=?", (cid,))
        return json.loads(r["data"]) if r else None

    def list_cases(self) -> list[dict]:
        return [json.loads(r["data"]) for r in self.all("SELECT data FROM cases ORDER BY created_at DESC")]

    # events --------------------------------------------------------------
    def events(self, cid: str) -> list[dict]:
        rows = self.all("SELECT * FROM events WHERE case_id=? ORDER BY seq", (cid,))
        return [{"seq": r["seq"], "ts": r["ts"], "type": r["type"], "actor": r["actor"], "data": json.loads(r["data"]),
                 "prev_hash": r["prev_hash"], "hash": r["hash"]} for r in rows]

    def put_event(self, cid: str, ev: dict) -> None:
        self.x("INSERT INTO events(case_id, seq, ts, type, actor, data, prev_hash, hash) VALUES(?,?,?,?,?,?,?,?)",
               (cid, ev["seq"], ev["ts"], ev["type"], ev["actor"], json.dumps(ev["data"], ensure_ascii=False),
                ev["prev_hash"], ev["hash"]))

    def log_access(self, ts: str, actor: str, role: str, case_id: str | None, action: str, reason: str | None) -> None:
        self.x("INSERT INTO access_log(ts, actor, role, case_id, action, reason) VALUES(?,?,?,?,?,?)",
               (ts, actor, role, case_id, action, reason))

    def access_log(self, case_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        if case_id:
            rows = self.all("SELECT * FROM access_log WHERE case_id=? ORDER BY id DESC LIMIT ?", (case_id, limit))
        else:
            rows = self.all("SELECT * FROM access_log ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows]
