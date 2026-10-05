"""SPEC v0.2 through the API: G7, claim split, registry-unknown, cue checklist, Cancel-primary."""
from conftest import ANALYST
from test_api import fv_answer, start


def ids(a):
    return [x["id"] for x in a["actions"]]


def test_g7_relative_denial_is_red_with_g7_note(client, device_factory):
    sc, a1 = start(client, "T1")
    cid = a1["case_id"]
    a2 = client.post("/v1/risk/assess", json={"case_id": cid, "claim": "family", "claim_target": "rel_rahul"}).json()
    assert a2["tier"] == "amber" and a2["p"] < a2["thresholds"]["red_at_or_above"]
    fv_answer(client, device_factory, sc, cid, "no")
    case = client.get(f"/v1/cases/{cid}", headers=ANALYST).json()
    assert case["tier"] == "red" and any(g["id"] == "G7" for g in case["guardrails"])
    assert "continue_anyway" not in [x["id"] for x in case["actions"]]


def test_scenarios_expose_bank_list(client):
    sc = client.post("/v1/demo/scenario/T2").json()
    banks = {b["id"]: b for b in sc["banks"]}
    assert banks["bdb"]["integrated"] and banks["bdb"]["yours"] and not banks["other"]["integrated"]


def test_registry_unknown_when_named_bank_not_integrated(client):
    sc, a1 = start(client, "T2")
    cid = a1["case_id"]
    a2 = client.post("/v1/risk/assess", json={"case_id": cid, "claim": "bank", "claim_target": "other"}).json()
    assert "bank_claim_not_1600" in a2["signals"]
    a3 = client.post(f"/v1/cases/{cid}/checks/bank_registry").json()
    assert "bank_registry_unknown" in a3["signals"] and "bank_no_active_call" not in a3["signals"]
    assert a3["tier"] == "amber" and not a3["hold"]
    txt = next(r for r in a3["reasons"] if r["code"] == "bank_registry_unknown")["text"]
    assert "not connected to Pehchaan" in txt["en"]
    assert "call_bank_official" in ids(a3)


def test_registry_no_call_for_integrated_named_bank_is_g7(client):
    sc, a1 = start(client, "T2")
    cid = a1["case_id"]
    client.post("/v1/risk/assess", json={"case_id": cid, "claim": "bank", "claim_target": "bdb"})
    a3 = client.post(f"/v1/cases/{cid}/checks/bank_registry").json()
    assert a3["tier"] == "red" and any(g["id"] == "G7" for g in a3["guardrails"])


def test_registry_active_1600_call_is_green(client):
    sc, a1 = start(client, "T2")
    cid = a1["case_id"]
    svc = client.app.state.svc
    svc.bank.start_call("u_ramesh", "+911600123456", svc.ts())
    client.post("/v1/risk/assess", json={"case_id": cid, "claim": "bank", "claim_target": "bdb"})
    a3 = client.post(f"/v1/cases/{cid}/checks/bank_registry").json()
    assert "bank_active_call_1600" in a3["signals"] and a3["tier"] == "green"


def test_claim_split_upi_or_shop(client):
    sc, a1 = start(client, "T2")
    cid = a1["case_id"]
    a2 = client.post("/v1/risk/assess", json={"case_id": cid, "claim": "upi_or_shop"}).json()
    assert "claim_upi_or_shop" in a2["signals"] and "bank_claim_not_1600" not in a2["signals"]
    assert "bank_registry" not in ids(a2)


def test_cue_checklist_for_coached_no_one(client):
    # T3 (digital arrest): the victim is coached to say "no one"; the context alone keeps it Amber
    sc, a1 = start(client, "T3")
    cid = a1["case_id"]
    a2 = client.post("/v1/risk/assess", json={"case_id": cid, "claim": "none"}).json()
    assert a2["tier"] == "amber" and ids(a2)[0] == "cue_checklist"
    a3 = client.post("/v1/risk/assess", json={"case_id": cid, "cues": ["cue_secrecy", "cue_otp_pin"], "checklist_done": True}).json()
    assert {"cue_secrecy", "cue_otp_pin"} <= set(a3["signals"]) and a3["p"] > a2["p"]
    assert "cue_checklist" not in ids(a3)
    # answering "none of these" also closes the checklist
    sc, b1 = start(client, "T3")
    client.post("/v1/risk/assess", json={"case_id": b1["case_id"], "claim": "other"})
    b3 = client.post("/v1/risk/assess", json={"case_id": b1["case_id"], "cues": [], "checklist_done": True}).json()
    assert "cue_checklist" not in ids(b3)


def test_user_reported_denial_makes_cancel_primary(client):
    # T2 context (domestic unknown caller) answered "someone else": a user-reported "not them" stays Amber
    sc, a1 = start(client, "T2")
    cid = a1["case_id"]
    client.post("/v1/risk/assess", json={"case_id": cid, "claim": "other"})
    a3 = client.post(f"/v1/cases/{cid}/checks/callback", json={"result": "denied"}).json()
    assert a3["tier"] == "amber" and not any(g["id"] == "G7" for g in a3["guardrails"])
    cancel = next(x for x in a3["actions"] if x["id"] == "cancel_payment")
    assert cancel["primary"] is True


def test_green_threshold_015_coached_no_one_on_t1_context_is_green(client):
    # documents the accepted trade-off of green_below = 0.15: T1 context (p 0.158) answered "no one"
    # (LR 0.8) falls to p 0.13 < 0.15 and proceeds; "someone else" (LR 1.0) stays Amber with the checklist
    sc, a1 = start(client, "T1")
    assert a1["tier"] == "amber" and a1["thresholds"]["green_below"] == 0.15
    a2 = client.post("/v1/risk/assess", json={"case_id": a1["case_id"], "claim": "none"}).json()
    assert a2["tier"] == "green"
    sc, b1 = start(client, "T1")
    b2 = client.post("/v1/risk/assess", json={"case_id": b1["case_id"], "claim": "other"}).json()
    assert b2["tier"] == "amber" and ids(b2)[0] == "cue_checklist"
