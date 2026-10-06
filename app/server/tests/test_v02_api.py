import pytest
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


def test_a20_checklist_on_t1_when_context_was_amber(client):
    # green_below 0.15: T1's context (p 0.158, Amber) answered "No one" (LR 0.8) scores p 0.13 (Green),
    # but SPEC v0.2 A20 still shows the three questions because the context alone was Amber
    sc, a1 = start(client, "T1")
    assert a1["tier"] == "amber" and a1["thresholds"]["green_below"] == 0.15
    a2 = client.post("/v1/risk/assess", json={"case_id": a1["case_id"], "claim": "none"}).json()
    assert a2["tier"] == "green" and a2["context_tier"] == "amber"
    assert ids(a2)[0] == "cue_checklist" and "proceed" in ids(a2)
    assert {r["code"] for r in a2["top_reasons"]} & {"caller_international", "caller_voip_unknown", "caller_unknown"}
    a3 = client.post("/v1/risk/assess", json={"case_id": a1["case_id"], "cues": ["cue_secrecy"], "checklist_done": True}).json()
    assert a3["p"] > a2["p"] and a3["tier"] == "amber" and "cue_checklist" not in ids(a3)
    # "None of these" closes it and the payment can go ahead
    sc, b1 = start(client, "T1")
    client.post("/v1/risk/assess", json={"case_id": b1["case_id"], "claim": "none"})
    b3 = client.post("/v1/risk/assess", json={"case_id": b1["case_id"], "cues": [], "checklist_done": True}).json()
    assert b3["tier"] == "green" and ids(b3) == ["proceed"]
    # a Green context never gets it (L2-like: T2 context is Green at stage 1)
    sc, c1 = start(client, "T2")
    assert c1["tier"] == "green"
    c2 = client.post("/v1/risk/assess", json={"case_id": c1["case_id"], "claim": "none"}).json()
    assert ids(c2) == ["proceed"]


def test_a19_family_verify_is_auto_sent_and_can_be_cancelled(client, device_factory):
    sc, a1 = start(client, "T1")
    cid = a1["case_id"]
    a2 = client.post("/v1/risk/assess", json={"case_id": cid, "claim": "family", "claim_target": "rel_rahul"}).json()
    fv = a2["auto_family_verify"]
    assert fv["auto"] is True and fv["relative"]["id"] == "rel_rahul" and fv["timeout_sec"] > 0
    assert a2["status"] == "awaiting_verification" and "family_verify" not in ids(a2)
    dev = device_factory(client, "dev_rahul", "rel_rahul")
    assert [x["challenge_id"] for x in client.get("/v1/devices/dev_rahul/challenges").json()] == [fv["challenge_id"]]
    # a second explicit send while one is pending is refused
    assert client.post("/v1/verify/family", json={"case_id": cid}).status_code == 409
    # "Cancel request": the push is withdrawn, the payer is back on the Amber options, FV can be sent again by hand
    c = client.post(f"/v1/verify/family/{fv['challenge_id']}/cancel").json()
    assert c["checks"]["family_verify"]["status"] == "cancelled" and c["tier"] == "amber"
    assert "family_verify" in ids(c) and "fv_timeout" not in c["signals"]
    assert client.get("/v1/devices/dev_rahul/challenges").json() == []
    assert client.post(f"/v1/verify/family/{fv['challenge_id']}/cancel").status_code == 409
    again = client.post("/v1/verify/family", json={"case_id": cid}).json()
    assert again["auto"] is False and again["challenge_id"] != fv["challenge_id"]
    case = client.get(f"/v1/cases/{cid}", headers={"X-Role": "fraud_analyst", "X-Analyst": "a", "X-Access-Reason": "t"}).json()
    types = [e["type"] for e in case["events"]]
    assert "fv_cancelled" in types and types.count("fv_challenge_sent") == 2
    # re-assessing the claim does not re-send on its own after a cancel
    r = client.post("/v1/risk/assess", json={"case_id": cid, "claim": "family", "claim_target": "rel_rahul"}).json()
    assert "auto_family_verify" not in r


def test_voice_shadow_mode_saves_score_without_changing_the_decision(client):
    sc, a1 = start(client, "T1")
    cid = a1["case_id"]
    a2 = client.post("/v1/risk/assess", json={"case_id": cid, "claim": "other"}).json()
    wav = client.get("/v1/demo/audio/synthetic.wav").content
    v = client.post("/v1/voice/score", files={"file": ("c.wav", wav, "audio/wav")},
                    data={"demo_hint": "synthetic", "case_id": cid}).json()
    assert v["voice_mode"] == "shadow" and v["used_in_decision"] is False and v["band"] == "likely_synthetic"
    assert v["user_message"]["en"].startswith("Thanks — this is saved with your case.")
    a3 = v["assessment"]
    assert a3["tier"] == a2["tier"] and a3["p"] == pytest.approx(a2["p"])
    r = next(x for x in a3["reasons"] if x["code"] == "voice_likely_synthetic")
    assert r["basis"] == "shadow" and r["lr"] == 1.0 and r["direction"] == "neutral"
    assert "voice_likely_synthetic" not in {x["code"] for x in a3["top_reasons"]}
    case = client.get(f"/v1/cases/{cid}", headers=ANALYST).json()
    assert case["checks"]["voice"]["voice_mode"] == "shadow" and case["checks"]["voice"]["p_synthetic"] > 0.8


def test_watermark_stays_active_in_shadow_mode(client):
    sc, a1 = start(client, "T1")
    cid = a1["case_id"]
    a2 = client.post("/v1/risk/assess", json={"case_id": cid, "claim": "other"}).json()
    wav = client.get("/v1/demo/audio/synthetic.wav").content
    v = client.post("/v1/voice/score", files={"file": ("c.wav", wav, "audio/wav")},
                    data={"demo_hint": "watermark", "case_id": cid}).json()
    assert v["watermark"]["detected"] is True
    assert v["user_message"]["en"].startswith("This audio carries a marker used by AI voice tools.")
    assert v["assessment"]["p"] > a2["p"] and "watermark_detected" in v["assessment"]["signals"]
