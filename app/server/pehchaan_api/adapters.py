"""Context adapters. ALL ARE MOCKS in the prototype (SPEC section 7).

Production counterparts (access is limited to regulated entities):
  mock_fri            -> DoT Financial Fraud Risk Indicator via the Digital Intelligence Platform (DIP)
  mock_i4c            -> I4C Suspect Registry + PSP mule score (MuleHunter-style)
  mock_bank_registry  -> the bank's outbound-call registry (contact-centre dialer / Amazon Connect)
  mock_contacts       -> on-device contact-hash matcher (the server only ever sees match: true/false)
  mock_payer_history  -> the bank/PSP's own payee history and amount percentiles
"""
from __future__ import annotations

import hashlib
import re

from .db import Store

COUNTRY = {
    "+44": ("United Kingdom", "यूनाइटेड किंगडम"), "+1": ("USA / Canada", "अमेरिका / कनाडा"),
    "+971": ("UAE", "यूएई"), "+65": ("Singapore", "सिंगापुर"), "+61": ("Australia", "ऑस्ट्रेलिया"),
    "+92": ("Pakistan", "पाकिस्तान"), "+880": ("Bangladesh", "बांग्लादेश"), "+977": ("Nepal", "नेपाल"),
    "+855": ("Cambodia", "कंबोडिया"), "+95": ("Myanmar", "म्यांमार"), "+856": ("Laos", "लाओस"),
    "+86": ("China", "चीन"), "+63": ("Philippines", "फ़िलीपींस"), "+62": ("Indonesia", "इंडोनेशिया"),
}


def normalise_number(num: str | None) -> str:
    if not num:
        return ""
    num = num.strip()
    plus = num.startswith("+")
    digits = re.sub(r"\D", "", num)
    if plus:
        return "+" + digits
    if len(digits) == 10:
        return "+91" + digits
    return digits


def is_international(num: str) -> bool:
    n = normalise_number(num)
    return n.startswith("+") and not n.startswith("+91")


def is_1600_series(num: str) -> bool:
    """TRAI 1600-series for BFSI service/transactional calls (national part starts with 1600)."""
    n = normalise_number(num)
    national = n[3:] if n.startswith("+91") else n.lstrip("+")
    return national.startswith("1600")


def country_of(num: str) -> tuple[str, str] | None:
    n = normalise_number(num)
    for code in sorted(COUNTRY, key=len, reverse=True):
        if n.startswith(code):
            return code, COUNTRY[code][0] + "|" + COUNTRY[code][1]
    return None


def pretty_number(num: str | None) -> str:
    n = normalise_number(num)
    if not n:
        return ""
    if n.startswith("+91") and len(n) == 13:
        d = n[3:]
        if d.startswith("1600"):
            return f"1600 {d[4:7]} {d[7:]}"
        return f"+91 {d[:5]} {d[5:]}"
    if n.startswith("+44") and len(n) == 13:
        d = n[3:]
        return f"+44 {d[:4]} {d[4:]}"
    return n


def contact_hash(user_id: str, number: str) -> str:
    """Salted hash as the device would compute it; raw contact lists never leave the phone."""
    return hashlib.sha256(f"{user_id}|{normalise_number(number)}".encode()).hexdigest()


class mock_contacts:  # noqa: N801 - "mock_*" naming is deliberate
    """On-device hash matcher (mock). The real SDK compares hashes on the phone and sends only a boolean."""

    def __init__(self, store: Store):
        self.s = store

    def add(self, user_id: str, number: str, label: str) -> None:
        self.s.x("INSERT OR REPLACE INTO contacts(user_id, contact_hash, label) VALUES(?,?,?)",
                 (user_id, contact_hash(user_id, number), label))

    def match(self, user_id: str, number: str) -> bool:
        return self.s.one("SELECT 1 FROM contacts WHERE user_id=? AND contact_hash=?",
                          (user_id, contact_hash(user_id, number))) is not None


class mock_fri:  # noqa: N801
    """DoT FRI tier lookup (mock). Returns None | 'medium' | 'high' | 'very_high'."""

    def __init__(self, store: Store):
        self.s = store

    def set(self, number: str, tier: str) -> None:
        self.s.x("INSERT OR REPLACE INTO mock_fri(number, tier) VALUES(?,?)", (normalise_number(number), tier))

    def lookup(self, number: str) -> str | None:
        r = self.s.one("SELECT tier FROM mock_fri WHERE number=?", (normalise_number(number),))
        return r["tier"] if r else None


class mock_i4c:  # noqa: N801
    """I4C Suspect Registry / payee mule score (mock). Returns None | 'medium' | 'high'."""

    def __init__(self, store: Store):
        self.s = store

    def set(self, vpa: str, level: str, note: str = "") -> None:
        self.s.x("INSERT OR REPLACE INTO mock_i4c(vpa, level, note) VALUES(?,?,?)", (vpa.lower(), level, note))

    def lookup(self, vpa: str) -> str | None:
        r = self.s.one("SELECT level FROM mock_i4c WHERE vpa=?", (vpa.lower(),))
        return r["level"] if r else None


# Banks whose outbound-call registry is connected to Pehchaan (mock). SPEC v0.2: a lookup against
# any other bank returns 'unknown' (LR 1), never 'no active call'.
BANKS = {
    "bdb": {"id": "bdb", "name": "Bharat Demo Bank", "name_hi": "भारत डेमो बैंक", "integrated": True,
            "label": "Bharat Demo Bank", "label_hi": "भारत डेमो बैंक"},
    "other": {"id": "other", "name": "that bank", "name_hi": "वो बैंक", "integrated": False,
              "label": "Another bank", "label_hi": "कोई दूसरा बैंक"},
}


class mock_bank_registry:  # noqa: N801
    """Bank outbound-call registry (mock): is the bank calling this customer right now, from a 1600 number?"""

    def __init__(self, store: Store):
        self.s = store

    @staticmethod
    def bank(bank_id: str | None) -> dict | None:
        return BANKS.get(bank_id or "")

    def integrated(self, bank_id: str | None) -> bool:
        b = BANKS.get(bank_id or "")
        return bool(b and b["integrated"])

    def start_call(self, customer_id: str, number: str, started_at: str) -> None:
        self.s.x("INSERT INTO mock_bank_calls(customer_id, number, active, started_at) VALUES(?,?,1,?)",
                 (customer_id, normalise_number(number), started_at))

    def active_call(self, customer_id: str) -> dict | None:
        r = self.s.one("SELECT number, started_at FROM mock_bank_calls WHERE customer_id=? AND active=1",
                       (customer_id,))
        return {"number": r["number"], "started_at": r["started_at"], "is_1600": is_1600_series(r["number"])} if r else None


class mock_payer_history:  # noqa: N801
    """Payee history + amount percentiles (mock of the bank/PSP's own data)."""

    def __init__(self, store: Store):
        self.s = store

    def add_payee(self, user_id: str, vpa: str, count: int, usual_amount: float) -> None:
        self.s.x("INSERT OR REPLACE INTO payee_history(user_id, payee_vpa, count, usual_amount) VALUES(?,?,?,?)",
                 (user_id, vpa.lower(), count, usual_amount))

    def payee(self, user_id: str, vpa: str) -> dict | None:
        r = self.s.one("SELECT count, usual_amount FROM payee_history WHERE user_id=? AND payee_vpa=?",
                       (user_id, vpa.lower()))
        return {"count": r["count"], "usual_amount": r["usual_amount"]} if r else None

    def record_sent(self, user_id: str, vpa: str, amount: float) -> None:
        """A payment went through: the payee is no longer new (as in the bank's own history)."""
        h = self.payee(user_id, vpa)
        n = (h["count"] if h else 0) + 1
        usual = amount if not h else (h["usual_amount"] * h["count"] + amount) / n
        self.add_payee(user_id, vpa, n, usual)


def name_tokens(name: str | None) -> set[str]:
    stop = {"mr", "mrs", "ms", "shri", "smt", "kumar", "kumari", "devi", "the", "and", "&"}
    return {t for t in re.findall(r"[a-z]+", (name or "").lower()) if len(t) > 1 and t not in stop}


def names_match(payee_name: str | None, relative: dict | None) -> bool:
    if not relative:
        return True
    rel = name_tokens(relative.get("full_name") or relative.get("name"))
    return bool(rel & name_tokens(payee_name))
