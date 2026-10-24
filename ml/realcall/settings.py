"""Paths, config and secrets for the real-call pipeline.

config.yaml (gitignored) holds non-secret settings; secrets come from the repo-root .env.
"""
import json
import os
import sys
import time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ML = HERE.parent
REPO = ML.parent
sys.path.insert(0, str(ML))

WORK = Path(os.environ.get("REALCALL_WORK", HERE / "work"))
SRC = WORK / "src"                # genuine/, clone/<gen>/, team_bona.csv
TAPES = WORK / "tapes"            # <tape_id>.wav (8 kHz, what Vobiz plays), <tape_id>.ref.wav (16 kHz), <tape_id>.json
CAPTURE = WORK / "capture"        # laptop-mic sessions and live calls
UPLINK = WORK / "uplink"          # network-side streams
UPLOADS = WORK / "device_uploads"  # dialer recordings copied off phones, per device
ATTACK = WORK / "attack"          # <call_id>.wav: the 8 kHz clone clip for one live-demo attack call (never ingested)
SEGMENTS = WORK / "segments"
MANIFESTS = WORK / "manifests"
REPORTS = WORK / "reports"
LEDGER = WORK / "ledger.jsonl"

DEFAULTS = {
    "public_base_url": "",          # https URL of the tunnel to server.py
    "server_port": 8600,
    "vobiz_number": "",             # E.164 caller ID owned by the Vobiz account
    "vobiz_api": "https://api.vobiz.ai/api/v1",
    "record_session": True,         # also keep Vobiz's own session recording of tape calls (QC)
    "call_time_limit_s": 600,
    "gap_between_calls_s": 15,
    "hash_salt": "",                # random string; phone numbers are only ever logged as salted hashes
}


def config() -> dict:
    cfg = dict(DEFAULTS)
    p = HERE / "config.yaml"
    if p.exists():
        cfg.update(yaml.safe_load(p.read_text(encoding="utf-8")) or {})
    return cfg


def env(name: str, required: bool = True) -> str:
    """Read a secret from the process env, then the repo-root .env. Never printed or logged."""
    v = os.environ.get(name)
    if not v:
        f = REPO / ".env"
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(f"{name}="):
                    v = line.split("=", 1)[1].strip().strip('"').strip("'")
    if required and not v:
        raise SystemExit(f"{name} is not set (add it to {REPO / '.env'})")
    return v or ""


def ensure_dirs():
    for d in (SRC, TAPES, CAPTURE, UPLINK, UPLOADS, ATTACK, SEGMENTS, MANIFESTS, REPORTS):
        d.mkdir(parents=True, exist_ok=True)


def log_event(ev: str, **fields):
    """Append one event to the ledger (the single source of truth for what happened on which call)."""
    ensure_dirs()
    rec = {"t": time.time(), "ev": ev, **fields}
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def read_ledger() -> list:
    if not LEDGER.exists():
        return []
    out = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def calls() -> dict:
    """Fold the ledger into one dict per call_id."""
    by = {}
    for e in read_ledger():
        cid = e.get("call_id")
        if not cid:
            continue
        c = by.setdefault(cid, {"call_id": cid, "events": []})
        c["events"].append(e)
        if e["ev"] == "call_registered":
            c.update({k: v for k, v in e.items() if k not in ("t", "ev")})
            c["registered_t"] = e["t"]
        elif e["ev"] == "answered":
            c["answered_t"] = e["t"]
            c["call_uuid"] = e.get("call_uuid")
        elif e["ev"] == "hangup":
            c["hangup_t"] = e["t"]
            c["hangup_cause"] = e.get("cause")
            c["duration_s"] = e.get("duration_s")
            if e.get("capture_file"):
                c["capture_file"] = e["capture_file"]
        elif e["ev"] == "recording":
            c["vobiz_recording_url"] = e.get("url")
        elif e["ev"] == "live_call":
            c.update({k: v for k, v in e.items() if k not in ("t", "ev")})
        elif e["ev"] == "uplink_done":
            c.update({k: v for k, v in e.items() if k not in ("t", "ev")})
    return by
