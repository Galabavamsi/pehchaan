"""Consent registry: who may be called, recorded and cloned. Every dial and every tape goes through here."""
import datetime as dt
import hashlib
import os
from pathlib import Path

import yaml

from realcall.settings import HERE, REPO, config


def _norm(num: str) -> str:
    d = "".join(ch for ch in str(num) if ch.isdigit())
    return "+" + d


def hash_number(num: str) -> str:
    salt = config().get("hash_salt", "")
    return hashlib.sha256((salt + _norm(num)).encode()).hexdigest()[:16]


class Registry:
    def __init__(self, path=None):
        p = Path(path or os.environ.get("REALCALL_PARTICIPANTS") or HERE / "participants.yaml")
        if not p.exists():
            raise SystemExit(f"{p} missing: copy participants.example.yaml and fill it in")
        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        self.participants = d.get("participants", {})
        self.devices = d.get("devices", {})

    def _consent(self, pid: str) -> dict:
        p = self.participants.get(pid)
        if not p:
            raise PermissionError(f"{pid} is not a registered participant")
        c = p.get("consent", {})
        exp = c.get("expires")
        if exp and dt.date.fromisoformat(str(exp)) < dt.date.today():
            raise PermissionError(f"{pid}: consent expired on {exp}")
        ev = c.get("evidence")
        if not ev or not (Path(ev) if Path(ev).is_absolute() else REPO / ev).exists():
            raise PermissionError(f"{pid}: consent evidence file missing ({ev}); save the signed form there first")
        return c

    def require_record(self, pid: str):
        if not self._consent(pid).get("record"):
            raise PermissionError(f"{pid} has not consented to being recorded")

    def require_clone(self, pid: str):
        if not self._consent(pid).get("clone"):
            raise PermissionError(f"{pid} has not consented to voice cloning")

    def can_clone(self, pid: str) -> bool:
        try:
            self.require_clone(pid)
            return True
        except PermissionError:
            return False

    def device(self, did: str) -> dict:
        d = self.devices.get(did)
        if not d:
            raise PermissionError(f"device {did} is not registered")
        if "X" in str(d.get("phone", "")):
            raise PermissionError(f"device {did} still has a placeholder number")
        self.require_record(d["owner"])
        return {"device_id": did, **d}

    def dialable(self, did: str) -> str:
        """The E.164 number for a registered device whose owner consented to recording; raises otherwise."""
        return _norm(self.device(did)["phone"])
