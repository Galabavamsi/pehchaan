"""Deterministic demo scenarios (POST /v1/demo/scenario/{name}).

All people, numbers, banks and UPI handles are fictional. +44 7700 900xxx is
the UK regulator's reserved drama range; 'Bharat Demo Bank' and '@okdemo' /
'@bdb' handles do not exist.
"""
from __future__ import annotations

from .adapters import BANKS, contact_hash  # noqa: F401  (contact_hash kept for callers/tests)
from .risk import CaseService

BANK = "Bharat Demo Bank"
BANK_HI = "भारत डेमो बैंक"

PAYERS = {
    "u_sunita": {
        "id": "u_sunita", "name": "Sunita Sharma", "name_hi": "सुनीता शर्मा", "gender": "f", "age_band": "55-64",
        "city": "Jaipur", "phone": "+919812345210", "vpa": "sunita.sharma@bdb", "vpa_masked": "sunita.s•••@bdb",
        "bank_name": BANK, "bank_name_hi": BANK_HI, "lang": "hi",
        # She pays Rahul's UK rent and fees, so large amounts are not unusual for her.
        "amount_p95": 62000, "amount_p99": 95000, "recent_new_payees_30m": 0,
        "circle": [
            {"id": "rel_rahul", "name": "Rahul", "name_hi": "राहुल", "full_name": "Rahul Sharma", "relation": "son",
             "relation_hi": "बेटा", "pronoun": "he", "device_id": "dev_rahul", "saved_number": "+919829011223", "lives_in": "London",
             "calls_payer": "Mummy", "calls_payer_hi": "मम्मी"},
            {"id": "rel_priya", "name": "Priya", "name_hi": "प्रिया", "full_name": "Priya Sharma", "relation": "daughter",
             "relation_hi": "बेटी", "pronoun": "she", "device_id": "dev_priya", "saved_number": "+919772033445", "lives_in": "Pune",
             "calls_payer": "Mummy", "calls_payer_hi": "मम्मी"},
        ],
        "contacts": [("+919829011223", "Rahul (beta)"), ("+919772033445", "Priya"), ("+919414055667", "Meena Gupta")],
        "payees": [("rahul.s@bdb", 6, 40000), ("priya.sharma@okdemo", 5, 5000), ("jvvnl.bill@okdemo", 12, 2400),
                   ("meena.gupta@okdemo", 4, 1500)],
    },
    "u_ramesh": {
        "id": "u_ramesh", "name": "Ramesh Iyer", "name_hi": "रमेश अय्यर", "gender": "m", "age_band": "65+",
        "city": "Chennai", "phone": "+919444012345", "vpa": "ramesh.iyer@bdb", "vpa_masked": "ramesh.i•••@bdb",
        "bank_name": BANK, "bank_name_hi": BANK_HI, "lang": "en",
        "amount_p95": 40000, "amount_p99": 75000, "recent_new_payees_30m": 0,
        "circle": [{"id": "rel_anand", "name": "Anand", "name_hi": "आनंद", "full_name": "Anand Iyer", "relation": "son",
                    "relation_hi": "बेटा", "pronoun": "he", "device_id": "dev_anand", "saved_number": "+919840011122",
                    "calls_payer": "Appa", "calls_payer_hi": "अप्पा"}],
        "contacts": [("+919840011122", "Anand"), ("+914428001234", "Clinic")],
        "payees": [("anand.iyer@okdemo", 8, 15000), ("tneb.bill@okdemo", 10, 3100)],
    },
    "u_kamala": {
        "id": "u_kamala", "name": "Kamala Devi", "name_hi": "कमला देवी", "gender": "f", "age_band": "65+",
        "city": "Lucknow", "phone": "+919450067890", "vpa": "kamala.devi@bdb", "vpa_masked": "kamala.d•••@bdb",
        "bank_name": BANK, "bank_name_hi": BANK_HI, "lang": "hi",
        "amount_p95": 30000, "amount_p99": 60000, "recent_new_payees_30m": 0,
        "circle": [{"id": "rel_vikas", "name": "Vikas", "name_hi": "विकास", "full_name": "Vikas Verma", "relation": "son",
                    "relation_hi": "बेटा", "pronoun": "he", "device_id": "dev_vikas", "saved_number": "+919415022334",
                    "calls_payer": "Amma", "calls_payer_hi": "अम्मा"}],
        "contacts": [("+919415022334", "Vikas")],
        "payees": [("vikas.verma@okdemo", 7, 10000)],
    },
}

SCENARIOS = {
    "T1": {
        "title": "Cloned son from a +44 WhatsApp number",
        "pattern": "T1 cloned relative",
        "payer_id": "u_sunita", "relative_id": "rel_rahul",
        "call": {"state": "active", "number": "+447700900123", "channel": "whatsapp", "duration_sec": 380},
        "payment": {"payee_vpa": "ariftraders@okdemo", "payee_name": "Arif Traders", "amount_inr": 50000},
        "script": "\"Mummy, accident ho gaya... police ne phone le liya. Papa ko mat batana, abhi ₹50,000 bhejo.\"",
        "expected": {"claim": "family", "claim_target": "rel_rahul", "fv_answer": "no", "final_tier": "red"},
    },
    "L2": {
        "title": "Real son on his new UK number asks for money; Family Verify confirms",
        "pattern": "genuine relative",
        "payer_id": "u_sunita", "relative_id": "rel_rahul",
        "call": {"state": "active", "number": "+447700900456", "channel": "whatsapp", "duration_sec": 240},
        "payment": {"payee_vpa": "rahul.sharma@okdemo", "payee_name": "Rahul Sharma", "amount_inr": 50000},
        "script": "\"Mumma, my old card got blocked here. Can you send this month's rent to my new account?\"",
        "expected": {"claim": "family", "claim_target": "rel_rahul", "fv_answer": "yes", "final_tier": "green"},
    },
    "L1": {
        "title": "Paying a friend while on a call",
        "pattern": "genuine friend",
        "payer_id": "u_sunita", "relative_id": None,
        "call": {"state": "active", "number": "+919414055667", "channel": "pstn", "duration_sec": 300},
        "payment": {"payee_vpa": "meena.g.kitty@okdemo", "payee_name": "Meena Gupta", "amount_inr": 2000},
        "script": "Meena: \"Kitty ka paisa is naye UPI ID pe bhej dena.\"",
        "expected": {"claim": None, "final_tier": "green"},
    },
    "T2": {
        "title": "Fake 'fraud department' of your bank from a 10-digit mobile (not 1600)",
        "pattern": "T2 fake bank official",
        "payer_id": "u_ramesh", "relative_id": None,
        "call": {"state": "active", "number": "+918765432109", "channel": "pstn", "duration_sec": 540},
        "payment": {"payee_vpa": "kavya.ent.secure@okdemo", "payee_name": "Kavya Enterprises", "amount_inr": 35000},
        "script": "\"Sir, fraud department se bol raha hoon. Account block ho jayega, abhi safe account mein transfer kariye.\"",
        "expected": {"claim": "bank", "claim_target": "bdb", "registry": "no_active_call", "final_tier": "red"},
        "fri": {"+918765432109": "medium"},
    },
    "T3": {
        "title": "Digital arrest: fake CBI officer, long video call",
        "pattern": "T3 digital-arrest hybrid",
        "payer_id": "u_kamala", "relative_id": "rel_vikas",
        "call": {"state": "active", "number": "+917012345678", "channel": "whatsapp", "duration_sec": 2820},
        "payment": {"payee_vpa": "sharma.logistics88@okdemo", "payee_name": "Sharma Logistics", "amount_inr": 180000},
        "script": "\"CBI se baat kar rahe hain. Aapke bete ka naam money laundering case mein hai. Settlement abhi bhejiye.\"",
        "expected": {"claim": "authority", "final_tier": "red"},
        "i4c": {"sharma.logistics88@okdemo": "medium"},
    },
}

# Historic cases so the analyst queue looks like a real morning. Each is run
# through the real pipeline (reasons and guardrails are genuine engine output).
BACKGROUND = [
    {"payer": "u_ramesh", "call": {"number": "+919123456780", "channel": "pstn", "duration_sec": 700},
     "payment": {"payee_vpa": "rbi.kyc.update@okdemo", "payee_name": "Suresh Kumar", "amount_inr": 75000},
     "claim": "bank", "claim_target": "bdb", "checks": [("bank_registry", None)], "after": "release", "ago_min": 41},
    {"payer": "u_kamala", "call": {"number": "+919988776655", "channel": "pstn", "duration_sec": 200},
     "payment": {"payee_vpa": "fresh.mart@okdemo", "payee_name": "Fresh Mart", "amount_inr": 12000},
     "claim": "other", "after": "continue", "ago_min": 128},
    {"payer": "u_sunita", "call": {"number": "+971501234567", "channel": "whatsapp", "duration_sec": 300},
     "payment": {"payee_vpa": "priyanka.n@okdemo", "payee_name": "Priyanka Nair", "amount_inr": 25000},
     "claim": "family", "claim_target": "rel_priya", "checks": [("callback", "denied")], "after": "report", "ago_min": 96},
    {"payer": "u_ramesh", "call": {"number": "+919840011122", "channel": "pstn", "duration_sec": 150, "in_contacts": False},
     "payment": {"payee_vpa": "anand.flat.rent@okdemo", "payee_name": "Anand Iyer", "amount_inr": 30000},
     "claim": "family", "claim_target": "rel_anand", "checks": [("callback", "confirmed")], "after": "pay", "ago_min": 77},
    {"payer": "u_kamala", "call": {"number": "+918899001122", "channel": "whatsapp", "duration_sec": 2400},
     "payment": {"payee_vpa": "court.fee.desk@okdemo", "payee_name": "Gupta Traders", "amount_inr": 250000},
     "claim": "authority", "after": None, "analyst": "confirm_fraud", "ago_min": 165},
    {"payer": "u_ramesh", "call": {"number": "+16465550100", "channel": "whatsapp", "duration_sec": 420},
     "payment": {"payee_vpa": "global.edu.fees@okdemo", "payee_name": "Global Edu Services", "amount_inr": 45000},
     "claim": "none", "voice": "noisy", "after": None, "ago_min": 18},
]


def seed_people(svc: CaseService) -> None:
    for p in PAYERS.values():
        user = {k: v for k, v in p.items() if k not in ("contacts", "payees")}
        svc.s.put_user(user)
        for num, label in p["contacts"]:
            svc.contacts.add(p["id"], num, label)
        for vpa, n, usual in p["payees"]:
            svc.history.add_payee(p["id"], vpa, n, usual)
    svc.fri.set("+919123456780", "high")
    svc.fri.set("+918899001122", "very_high")
    svc.i4c.set("rbi.kyc.update@okdemo", "high", "I4C suspect registry (mock)")
    svc.i4c.set("court.fee.desk@okdemo", "high", "I4C suspect registry (mock)")


def seed_background(svc: CaseService) -> None:
    from datetime import timedelta

    from .voice import demo_wav, mock_score

    for b in sorted(BACKGROUND, key=lambda b: -b.get("ago_min", 0)):
        svc._clock_offset = -timedelta(minutes=b.get("ago_min", 0))
        call = {"state": "active", **b["call"]}
        r = svc.assess({"payer_id": b["payer"], "payment": b["payment"], "call": call, "scenario": "background"})
        cid = r["case_id"]
        if not cid:
            continue
        svc.assess({"case_id": cid, "claim": b["claim"], "claim_target": b.get("claim_target")})
        for kind, res in b.get("checks", []):
            if kind == "bank_registry":
                svc.bank_registry_check(cid)
            else:
                svc.user_check(cid, kind, res)
        if b.get("voice"):
            svc.attach_voice(cid, mock_score(demo_wav(b["voice"]), None))
        if b.get("after"):
            try:
                svc.user_action(cid, b["after"])
            except Exception:
                pass
        if b.get("analyst"):
            svc._clock_offset += timedelta(minutes=9)
            svc.analyst_decision(cid, b["analyst"], "r.iyer", "fraud_analyst", "Customer confirmed on callback; payee flagged to PSP")
    svc._clock_offset = timedelta(0)


def load_scenario(svc: CaseService, name: str, with_background: bool = True) -> dict:
    name = name.upper()
    if name not in SCENARIOS:
        raise KeyError(name)
    sc = SCENARIOS[name]
    svc.s.reset(keep_devices=True)
    seed_people(svc)
    for num, tier in sc.get("fri", {}).items():
        svc.fri.set(num, tier)
    for vpa, level in sc.get("i4c", {}).items():
        svc.i4c.set(vpa, level)
    if with_background:
        seed_background(svc)
    payer = svc.s.get_user(sc["payer_id"])
    rel = next((r for r in payer.get("circle", []) if r["id"] == sc.get("relative_id")), None)
    saved_as = next((label for num, label in PAYERS[sc["payer_id"]]["contacts"]
                     if num == sc["call"]["number"]), None)
    payee_known = svc.history.payee(sc["payer_id"], sc["payment"]["payee_vpa"]) is not None
    return {
        "caller_saved_as": saved_as, "payee_new": not payee_known,
        "scenario": name, "title": sc["title"], "pattern": sc["pattern"], "script": sc["script"],
        "payer": payer, "relative": rel, "call": sc["call"], "payment": sc["payment"], "expected": sc["expected"],
        "bank": {"name": BANK, "name_hi": BANK_HI},
        "banks": [{**b, "yours": b["id"] == "bdb"} for b in BANKS.values()],
        "note": "All people, numbers, banks and UPI IDs are fictional. Context adapters are mocks.",
    }
