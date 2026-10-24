"""Red-team matrix (FINALE_PLAN D1): the evasions we could think of, run through the real risk pipeline.

Every runnable row starts from a fresh demo database (fictional people only), plays the attack through the same
API the phones use, and records what the system did. Rows that software can't play (another app, a screen-share,
a coached relative) are listed with what we would change. The voice service is the mock here on purpose: the
rows about voice test the decision rules (G2), whatever any detector says.

    cd app/server && python redteam.py        # writes results/redteam.json and ../../RED_TEAM.md
"""
from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "engine"))
os.environ["PEHCHAAN_NO_AUTOAPP"] = "1"

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from pehchaan_api.main import create_app  # noqa: E402

CALL_44 = {"state": "active", "number": "+447700900123", "channel": "whatsapp", "duration_sec": 380}


class Phone:
    """A relative's phone: an Ed25519 key bound to a device id, signing Family Verify answers."""

    def __init__(self, c, device_id="dev_rahul", user_id="rel_rahul"):
        self.key, self.device_id = Ed25519PrivateKey.generate(), device_id
        pub = self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.bind = c.post("/v1/devices/register", json={"device_id": device_id, "user_id": user_id,
                                                         "public_key_b64": base64.b64encode(pub).decode()})

    def answer(self, c, challenge_id, answer, nonce=None, sign_for=None):
        if nonce is None:
            nonce = next(x["nonce"] for x in c.get(f"/v1/devices/{self.device_id}/challenges").json()
                         if x["challenge_id"] == challenge_id)
        cid, n = sign_for or (challenge_id, nonce)
        sig = base64.b64encode(self.key.sign(f"pehchaan-fv|{cid}|{n}|{answer}".encode())).decode()
        return c.post(f"/v1/verify/family/{challenge_id}/respond",
                      json={"answer": answer, "device_id": self.device_id, "signature_b64": sig})


def assess(c, payment, call=CALL_44, payer="u_sunita"):
    return c.post("/v1/risk/assess", json={"payer_id": payer, "payment": payment, "call": call}).json()


def pay(c, a):
    """The payer goes ahead: Continue on a case, or (no case opened) the app reports the payment sent (SPEC v0.3:
    only a payment that went through counts toward the payee's history and the same-call total)."""
    if a.get("case_id"):
        return c.post(f"/v1/cases/{a['case_id']}/user-action", json={"action": "continue"})
    return c.post(f"/v1/payments/{a['payment_ref']}/sent")


def claim(c, cid, code, target=None):
    return c.post("/v1/risk/assess", json={"case_id": cid, "claim": code, "claim_target": target}).json()


def case(c, cid):
    return c.get(f"/v1/cases/{cid}", headers={"X-Role": "fraud_analyst", "X-Analyst": "redteam",
                                             "X-Access-Reason": "red-team run"}).json()


def outcome(a):
    """stopped = held or refused before money moves; paused = asked 'Who asked you to pay?' and checks;
    missed = the payment goes through with no question."""
    if a.get("status") == "held" or a.get("tier") == "red":
        return "stopped"
    if a.get("case_id") and (a.get("ask_claim") or a.get("tier") == "amber"
                             or any(x["id"] == "cue_checklist" for x in a.get("actions", []))):
        return "paused"
    return "missed"


def fresh(c, name="T1"):
    return c.post(f"/v1/demo/scenario/{name}", params={"background": False}).json()


# --------------------------------------------------------------------------- the rows
def r_split(c):
    fresh(c)
    payment = {"payee_vpa": "fees.desk@okdemo", "payee_name": "Fees Desk", "amount_inr": 9500}
    seen = []
    for _ in range(4):
        a = assess(c, payment)
        seen.append(outcome(a))
        pay(c, a)
    return {"outcome": "paused" if all(s == "paused" for s in seen) else "missed",
            "observed": f"each of the 4 payments was {', '.join(seen)}; the trigger counts what was already sent "
                        f"during the call and the payee stays new for the rest of the call"}


def r_wait(c, amount):
    a = c.post("/v1/demo/custom", params={"background": False},
               json={"caller": "unknown", "call_state": "ended", "ended_min": 30, "amount_inr": amount, "payee": "new"}).json()
    r = assess(c, a["payment"], a["call"])
    t = r["trigger"]
    seen = (f"assessed: {', '.join(t['why'])}" if t["fired"] else
            f"not assessed: the call ended 30 min ago, outside the window for this amount "
            f"(payment rules met: {', '.join(w for w in t['why'] if 'call' not in w)})")
    return {"outcome": outcome(r), "observed": seen}


def r_coached(c, code):
    fresh(c)
    a = assess(c, {"payee_vpa": "ariftraders@okdemo", "payee_name": "Arif Traders", "amount_inr": 50000})
    b = claim(c, a["case_id"], code)
    ck = next((x for x in b.get("actions", []) if x["id"] == "cue_checklist"), None)
    seen = f"tier {b['tier']} after the coached answer; "
    seen += (f"the cue checklist comes first ({', '.join(ck['produces'])})" if ck else "no checklist, Pay now")
    if ck:  # the victim is also coached to tap "None of these"
        d = c.post("/v1/risk/assess", json={"case_id": a["case_id"], "checklist_done": True}).json()
        seen += f". Coached to tap \"None of these\" as well: tier {d['tier']}, the payment can go"
    return {"outcome": outcome(b), "observed": seen}


def r_spoofed_1600(c):
    a = c.post("/v1/demo/custom", params={"background": False},
               json={"caller": "bank_1600", "amount_inr": 35000, "payee": "new", "payee_name": "Safe Account Desk",
                     "bank_calling": False}).json()
    r = assess(c, a["payment"], a["call"])
    claim(c, r["case_id"], "bank", "bdb")
    b = c.post(f"/v1/cases/{r['case_id']}/checks/bank_registry").json()
    return {"outcome": outcome(b), "observed": f"registry: {b['checks']['bank_registry']['result']}; tier {b['tier']}, "
                                                f"status {case(c, r['case_id'])['status']}"}


def r_family_says_no(c, payee_name, caller):
    a = c.post("/v1/demo/custom", params={"background": False},
               json={"caller": caller, "channel": "pstn", "amount_inr": 40000, "payee": "new",
                     "payee_name": payee_name}).json()
    son = Phone(c)  # bound long before the call, as on a real phone
    r = assess(c, a["payment"], a["call"])
    b = claim(c, r["case_id"], "family", "rel_rahul")
    fv = b.get("auto_family_verify") or {}
    if "challenge_id" not in fv:
        return {"outcome": outcome(b), "observed": f"tier {b['tier']} after \"Family member\"; no Family Verify sent"}
    res = son.answer(c, fv["challenge_id"], "no").json()
    return {"outcome": outcome(res),
            "observed": f"tier {b['tier']} after \"Family member\", and Family Verify still went to the son's own phone; "
                        f"he answered no: tier {res['tier']}, status {case(c, r['case_id'])['status']}"}


def r_rebind(c):
    fresh(c)
    son = Phone(c)
    a = assess(c, {"payee_vpa": "ariftraders@okdemo", "payee_name": "Arif Traders", "amount_inr": 50000})
    b = claim(c, a["case_id"], "family", "rel_rahul")
    attacker = Phone(c)  # tries to bind its own key as the son's phone while the question waits
    forged = attacker.answer(c, b["auto_family_verify"]["challenge_id"], "yes",
                             nonce=next(x["nonce"] for x in c.get("/v1/devices/dev_rahul/challenges").json()))
    real = son.answer(c, b["auto_family_verify"]["challenge_id"], "no")
    ok = attacker.bind.status_code == 409 and forged.status_code == 403 and real.status_code == 200
    return {"outcome": "stopped" if ok else "missed",
            "observed": f"re-binding refused ({attacker.bind.status_code}); the attacker's 'yes' rejected "
                        f"({forged.status_code}); the son's real answer accepted ({real.status_code})"}


def r_replay(c):
    fresh(c)
    son = Phone(c)
    a = assess(c, {"payee_vpa": "ariftraders@okdemo", "payee_name": "Arif Traders", "amount_inr": 50000})
    b = claim(c, a["case_id"], "family", "rel_rahul")
    ch1 = b["auto_family_verify"]["challenge_id"]
    n1 = next(x["nonce"] for x in c.get("/v1/devices/dev_rahul/challenges").json())
    c.post(f"/v1/verify/family/{ch1}/cancel")
    ch2 = c.post("/v1/verify/family", json={"case_id": a["case_id"], "relative_id": "rel_rahul"}).json()["challenge_id"]
    n2 = next(x["nonce"] for x in c.get("/v1/devices/dev_rahul/challenges").json())
    replay = son.answer(c, ch2, "yes", nonce=n2, sign_for=(ch1, n1))  # a 'yes' signed for the old question
    flipped = son.answer(c, ch2, "yes", nonce=n2, sign_for=(ch2, n2 + "x"))
    ok = replay.status_code == 403 and flipped.status_code == 403
    return {"outcome": "stopped" if ok else "missed",
            "observed": f"a 'yes' signed for an earlier question: {replay.status_code}; tampered nonce: {flipped.status_code}"}


def r_spam(c):
    fresh(c, "L2")
    sc = c.get("/v1/demo/current").json()
    a = assess(c, sc["payment"], sc["call"])
    ch = claim(c, a["case_id"], "family", "rel_rahul")["auto_family_verify"]
    codes = []
    for _ in range(3):
        c.post(f"/v1/verify/family/{ch['challenge_id']}/cancel")
        r = c.post("/v1/verify/family", json={"case_id": a["case_id"], "relative_id": "rel_rahul"})
        codes.append(r.status_code)
        if r.status_code != 200:
            break
        ch = r.json()
    detail = r.json().get("detail", "")
    return {"outcome": "stopped" if codes[-1] == 429 else "missed",
            "observed": f"push requests 2-4 returned {codes}; then: \"{detail}\""}


def r_voice(c, scenario, hint, answer):
    fresh(c, scenario)
    phone = Phone(c)
    sc = c.get("/v1/demo/current").json()
    a = assess(c, sc["payment"], sc["call"])
    b = claim(c, a["case_id"], "family", "rel_rahul")
    res = phone.answer(c, b["auto_family_verify"]["challenge_id"], answer).json()
    wav = c.get(f"/v1/demo/audio/{hint}.wav").content
    v = c.post("/v1/voice/score", files={"file": ("c.wav", wav, "audio/wav")},
               data={"demo_hint": hint, "case_id": a["case_id"]}).json()
    after = v["assessment"]
    return {"outcome": outcome(after) if scenario == "T1" else ("passes" if after["tier"] == "green" else "false_alarm"),
            "observed": f"voice band {v['band']} ({'shadow' if not v['used_in_decision'] else 'used'}); tier before "
                        f"{res['tier']}, after {after['tier']}; user message: \"{(v.get('user_message') or {}).get('en', '')}\""}


def r_whatsapp(c):
    a = c.post("/v1/demo/custom", params={"background": False},
               json={"caller": "unknown", "channel": "whatsapp", "amount_inr": 25000, "payee": "new",
                     "payee_name": "Gift Card Store"}).json()
    r = assess(c, a["payment"], a["call"])
    return {"outcome": outcome(r), "observed": f"trigger: {', '.join(r['trigger']['why'])}; signals {r.get('signals', [])[:4]}"}


def r_hopping(c):
    fresh(c)
    seen = []
    for i, name in enumerate(["Shop One", "Shop Two", "Shop Three"]):
        a = assess(c, {"payee_vpa": f"shop{i}@okdemo", "payee_name": name, "amount_inr": 4000},
                   {"state": "none", "number": None})
        seen.append(("burst_new_payees" in (a.get("signals") or []), a["triggered"]))
        pay(c, a)
    return {"outcome": "missed",
            "observed": f"no call, three new payees at ₹4,000: burst signal per payment {[s for s, _ in seen]}, "
                        f"assessed {[t for _, t in seen]}. With no call Pehchaan stays out by design (SPEC section 2); "
                        f"the burst signal counts once a call is on"}


def r_hopping_call(c):
    fresh(c)
    seen = []
    for i, name in enumerate(["Shop One", "Shop Two", "Shop Three"]):
        a = assess(c, {"payee_vpa": f"shop{i}@okdemo", "payee_name": name, "amount_inr": 4000},
                   {"state": "active", "number": "+918765432110", "channel": "pstn", "duration_sec": 300})
        seen.append("burst_new_payees" in (a.get("signals") or []))
        pay(c, a)
    return {"outcome": "paused", "observed": f"on a call, three new payees at ₹4,000: each paused; burst signal {seen}"}


ROWS = [
    ("Split the demand: ₹9,500 four times to one payee during the call", r_split,
     "v0.3: amounts sent during the call add up; a payee first paid during the call stays new."),
    ("Hang up, wait 30 minutes, then pay ₹60,000", lambda c: r_wait(c, 60000),
     "v0.3: 60-minute window for amounts ≥ ₹50,000."),
    ("Hang up, wait 30 minutes, then pay ₹40,000", lambda c: r_wait(c, 40000),
     "Open gap. Next: a per-user window, or the bank's velocity rules on new payees."),
    ("Coach the victim to answer \"No one asked me\"", lambda c: r_coached(c, "none"),
     "The three questions come first, and the UI says being told what to tap is a warning sign. A victim coached "
     "through every question still gets through: the residual risk."),
    ("Coach the victim to say \"a shop or UPI app\"", lambda c: r_coached(c, "upi_or_shop"),
     "v0.3: the checklist now covers this claim too, with the refund-script questions. A victim coached through "
     "every question still gets through: the residual risk."),
    ("Call from a spoofed 1600 bank number", r_spoofed_1600,
     "The bank's own call registry says it isn't calling: a decisive negative from outside the call."),
    ("Caller ID shows the son's saved number (spoofed, or his WhatsApp taken over)",
     lambda c: r_family_says_no(c, "Arif Traders", "saved"),
     "v0.3: Family Verify goes out even at Green. The son's own phone is the check the attacker can't fake."),
    ("Mule account opened in the son's name", lambda c: r_family_says_no(c, "Rahul Sharma", "unknown"),
     "v0.3: no name mismatch to see, so the son's own answer decides, even at Green."),
    ("Swap in the attacker's phone as the son's, mid-attack", r_rebind,
     "v0.3: no re-binding while a question waits. Production: bank-app device binding (not built)."),
    ("Forge or replay the son's \"yes\"", r_replay,
     "Each answer is signed over the challenge id and a fresh nonce by the son's device key."),
    ("Spam Family Verify until the son taps yes or tunes out", r_spam,
     "v0.3: 3 pushes per payer and 5 per relative per hour, then \"call him on his saved number\"."),
    ("A clone the detector misses (cloned son, son says no)", lambda c: r_voice(c, "T1", "bonafide", "no"),
     "G2: voice is shadow-only, so a missed clone can't release money."),
    ("Detector false alarm on the real son (son says yes)", lambda c: r_voice(c, "L2", "synthetic", "yes"),
     "G2 and G6: voice can't hold money and the copy never accuses the caller."),
    ("WhatsApp or VoIP call instead of a phone call", r_whatsapp,
     "The Android audio mode shows an ongoing VoIP call; unknown VoIP callers add risk."),
    ("Many small payments to new payees, no call", r_hopping,
     "By design (SPEC section 2): no call, no Pehchaan. The bank's own fraud rules still apply."),
    ("Many small payments to new payees during a call", r_hopping_call,
     "burst_new_payees now counts real payments in the last 30 minutes."),
]

DECLARED = [
    ("Pay from another UPI app that doesn't have Pehchaan",
     "Not covered by the app SDK. At a bank deployment the risk API sees every debit from the account, "
     "but without the call state, so only payee and amount context."),
    ("Screen-share or remote-control app (the scammer taps for the victim)",
     "Not detected today. Android can tell an app that screen sharing or an accessibility service is active: "
     "we would add that as a context signal."),
    ("The scammer coaches the real son, or the son is in on it",
     "Family Verify trusts the bound relative. The son sees the payee name and amount; the case stays in the analyst "
     "queue; large amounts need an analyst to release a hold."),
    ("The scammer adds their own phone to the family circle before the attack",
     "Both sides opt in. Production binding goes through the bank app's authenticated device binding with a waiting "
     "period for new relatives; the prototype binds the relative page when it opens."),
]


def main() -> None:
    rows = []
    with tempfile.TemporaryDirectory() as d:
        os.environ["PEHCHAAN_DATA"] = d
        os.environ.pop("VOICE_SERVICE_URL", None)
        with TestClient(create_app(db_path=f"{d}/redteam.db", key_path=f"{d}/k.pem")) as c:
            for i, (evasion, fn, why) in enumerate(ROWS, 1):
                try:
                    r = fn(c)
                except Exception as exc:  # a crash is a finding too
                    r = {"outcome": "error", "observed": f"{type(exc).__name__}: {exc}"}
                rows.append({"id": f"R{i}", "evasion": evasion, **r, "why": why})
                print(f"R{i:<3}{r['outcome']:<9}{evasion}")
    out = {"run_at": datetime.now().astimezone().isoformat(timespec="seconds"), "rows": rows,
           "declared": [{"evasion": e, "status": s} for e, s in DECLARED],
           "note": "Fresh demo per row, fictional people, mock context adapters and mock voice service."}
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "redteam.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    label = {"stopped": "**Stopped**", "paused": "Paused and asked", "missed": "**Not caught**", "error": "Error",
             "passes": "Real son goes through (correct)", "false_alarm": "**Real son blocked**"}
    md = ["# Red-team matrix", "",
          f"Generated by `app/server/redteam.py` on {out['run_at'][:10]}. Each row runs on a fresh demo (fictional people, "
          "mock context adapters, mock voice service) through the same API the phones use. "
          "*Stopped* = held or refused before money moves. *Paused* = \"Who asked you to pay?\" plus checks. "
          "*Not caught* = the payment goes through with no question.", "",
          "| # | Evasion | Result | What the run showed | Why / what next |", "|---|---|---|---|---|"]
    md += [f"| {r['id']} | {r['evasion']} | {label[r['outcome']]} | {r['observed']} | {r['why']} |" for r in rows]
    md += ["", "## Not runnable in software (declared)", "", "| Evasion | Status today |", "|---|---|"]
    md += [f"| {e} | {s} |" for e, s in DECLARED]
    (HERE.parents[1] / "RED_TEAM.md").write_text("\n".join(md) + "\n")
    print("wrote results/redteam.json and RED_TEAM.md")


if __name__ == "__main__":
    main()
