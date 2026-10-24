from datetime import timedelta

import pytest
from conftest import ANALYST
from pehchaan.evidence import ist_iso


def start(client, name):
    sc = client.post(f"/v1/demo/scenario/{name}").json()
    r = client.post("/v1/risk/assess", json={"payer_id": sc["payer"]["id"], "payment": sc["payment"],
                                             "call": sc["call"], "scenario": name})
    assert r.status_code == 200, r.text
    return sc, r.json()


def fv_answer(client, device_factory, sc, case_id, answer):
    """Answer the Family Verify push. Since SPEC v0.2 A19 it is usually auto-sent with the
    'Family member' claim; otherwise send it explicitly."""
    rel = sc["relative"]
    dev = device_factory(client, rel["device_id"], rel["id"])
    pending = [x for x in client.get(f"/v1/devices/{dev.device_id}/challenges").json() if x["case_id"] == case_id]
    if pending:
        ch = {"challenge_id": pending[0]["challenge_id"]}
    else:
        r = client.post("/v1/verify/family", json={"case_id": case_id, "relative_id": rel["id"]})
        assert r.status_code == 200, r.text
        ch = r.json()
    pending = client.get(f"/v1/devices/{dev.device_id}/challenges").json()
    assert pending and pending[0]["challenge_id"] == ch["challenge_id"]
    nonce = pending[0]["nonce"]
    assert "Arif Traders" in pending[0]["message"]["en"] or "Rahul Sharma" in pending[0]["message"]["en"]
    r = client.post(f"/v1/verify/family/{ch['challenge_id']}/respond",
                    json={"answer": answer, "device_id": dev.device_id, "signature_b64": dev.sign(ch["challenge_id"], nonce, answer)})
    assert r.status_code == 200, r.text
    return r.json()


def test_health_and_scenarios(client):
    h = client.get("/v1/health").json()
    assert h["ok"] and h["voice_service"] == "mock" and all(a.startswith("mock_") for a in h["adapters"])
    assert set(client.get("/v1/demo/scenarios").json()) == {"T1", "T2", "T3", "L1", "L2"}


def test_t1_cloned_son_flow_ends_red_with_hold(client, device_factory):
    sc, a1 = start(client, "T1")
    assert a1["triggered"] and a1["ask_claim"] and a1["tier"] == "amber"
    cid = a1["case_id"]
    codes = {r["code"] for r in a1["reasons"]}
    assert {"caller_unknown", "caller_international", "caller_voip_unknown", "payee_new"} <= codes
    a2 = client.post("/v1/risk/assess", json={"case_id": cid, "claim": "family", "claim_target": "rel_rahul"}).json()
    assert a2["tier"] == "amber"
    assert "payee_name_mismatch" in a2["signals"]
    # SPEC v0.2 A19: the push is already on Rahul's phone; the other checks stay available
    assert a2["auto_family_verify"]["auto"] is True and a2["checks"]["family_verify"]["status"] == "pending"
    assert [x["id"] for x in a2["actions"]][:2] == ["callback", "safeword"]
    top = [r["code"] for r in a2["top_reasons"]][:2]
    assert "payee_name_mismatch" in top
    res = fv_answer(client, device_factory, sc, cid, "no")
    assert res["result"] == "denied" and res["tier"] == "red"
    case = client.get(f"/v1/cases/{cid}", headers=ANALYST).json()
    assert case["status"] == "held" and case["hold"]["auto_send_on_expiry"] is False
    assert case["hold"]["release_requires"] == "analyst_review"  # >= Rs 50,000
    assert case["chain"]["verified"]
    types = [e["type"] for e in case["events"]]
    assert types[0] == "payment_attempt" and "fv_response" in types and "hold_started" in types
    # continue is refused while held
    assert client.post(f"/v1/cases/{cid}/user-action", json={"action": "continue"}).status_code == 409


def test_l2_real_son_confirms_green(client, device_factory):
    sc, a1 = start(client, "L2")
    cid = a1["case_id"]
    a2 = client.post("/v1/risk/assess", json={"case_id": cid, "claim": "family", "claim_target": "rel_rahul"}).json()
    assert a2["tier"] == "amber" and "payee_name_mismatch" not in a2["signals"]
    res = fv_answer(client, device_factory, sc, cid, "yes")
    assert res["tier"] == "green"
    r = client.post(f"/v1/cases/{cid}/user-action", json={"action": "pay"}).json()
    assert r["status"] == "sent" and r["utr"].startswith("DEMO")


def test_l1_friend_is_silent_green(client):
    sc, a1 = start(client, "L1")
    assert a1["triggered"] and a1["tier"] == "green" and a1["case_id"] is None and not a1["ask_claim"]


def test_t2_bank_claim_registry_says_no_call(client):
    sc, a1 = start(client, "T2")
    assert a1["ask_claim"]
    cid = a1["case_id"]
    a2 = client.post("/v1/risk/assess", json={"case_id": cid, "claim": "bank", "claim_target": "bdb"}).json()
    assert "bank_claim_not_1600" in a2["signals"] and a2["tier"] == "amber"
    assert a2["actions"][0]["id"] == "bank_registry"
    a3 = client.post(f"/v1/cases/{cid}/checks/bank_registry").json()
    assert "bank_no_active_call" in a3["signals"] and a3["tier"] == "red"
    txt = next(r for r in a3["reasons"] if r["code"] == "bank_no_active_call")["text"]
    assert txt["en"] == "Bharat Demo Bank is not calling you right now."
    assert "भारत डेमो बैंक" in txt["hi"]


def test_t3_digital_arrest_red_with_fact_card(client):
    sc, a1 = start(client, "T3")
    cid = a1["case_id"]
    a2 = client.post("/v1/risk/assess", json={"case_id": cid, "claim": "authority"}).json()
    assert a2["tier"] == "red"
    assert "call_ongoing_long" in a2["signals"]
    ids = [x["id"] for x in a2["actions"]]
    assert "hold" in ids and "release_early" in ids


def test_not_triggered_when_no_call(client):
    client.post("/v1/demo/scenario/T1")
    r = client.post("/v1/risk/assess", json={"payer_id": "u_sunita", "call": {"state": "none"},
                                             "payment": {"payee_vpa": "x@okdemo", "payee_name": "X", "amount_inr": 50000}}).json()
    assert r["triggered"] is False and r["tier"] == "green"


def test_trusted_payee_bypass(client):
    client.post("/v1/demo/scenario/T1")
    r = client.post("/v1/risk/assess", json={
        "payer_id": "u_sunita", "call": {"state": "active", "number": "+447700900999", "channel": "whatsapp"},
        "payment": {"payee_vpa": "rahul.s@bdb", "payee_name": "Rahul Sharma", "amount_inr": 45000}}).json()
    assert r["tier"] == "green" and r["case_id"] is None
    assert any(g["id"] == "G5" for g in r["guardrails"])


def test_fv_signature_and_device_binding_enforced(client, device_factory):
    sc, a1 = start(client, "T1")
    cid = a1["case_id"]
    ch = client.post("/v1/risk/assess", json={"case_id": cid, "claim": "family", "claim_target": "rel_rahul"}).json()[
        "auto_family_verify"]
    dev = device_factory(client, "dev_rahul", "rel_rahul")
    nonce = client.get("/v1/devices/dev_rahul/challenges").json()[0]["nonce"]
    bad = client.post(f"/v1/verify/family/{ch['challenge_id']}/respond",
                      json={"answer": "yes", "device_id": "dev_rahul", "signature_b64": dev.sign(ch["challenge_id"], nonce, "no")})
    assert bad.status_code == 403
    other = device_factory(client, "dev_priya", "rel_priya")
    wrong_dev = client.post(f"/v1/verify/family/{ch['challenge_id']}/respond",
                            json={"answer": "yes", "device_id": "dev_priya", "signature_b64": other.sign(ch["challenge_id"], nonce, "yes")})
    assert wrong_dev.status_code == 403
    # SPEC v0.3: an attacker can't re-bind Rahul's phone to their own key while the question is waiting
    with pytest.raises(AssertionError):
        device_factory(client, "dev_rahul", "rel_rahul")
    ok = client.post(f"/v1/verify/family/{ch['challenge_id']}/respond",
                     json={"answer": "yes", "device_id": "dev_rahul", "signature_b64": dev.sign(ch["challenge_id"], nonce, "yes")})
    assert ok.status_code == 200, ok.text


def test_fv_timeout_falls_back(client, device_factory):
    sc, a1 = start(client, "L2")
    cid = a1["case_id"]
    ch = client.post("/v1/risk/assess", json={"case_id": cid, "claim": "family", "claim_target": "rel_rahul"}).json()[
        "auto_family_verify"]
    device_factory(client, "dev_rahul", "rel_rahul")
    r = client.post(f"/v1/demo/fv/{ch['challenge_id']}/timeout").json()
    assert r["tier"] == "amber"
    a = client.get(f"/v1/cases/{cid}", headers=ANALYST).json()
    assert "fv_timeout" in a["signals"]
    assert {x["id"] for x in a["actions"]} >= {"callback", "safeword"}


def test_voice_mock_and_quality_gate(client):
    sc, a1 = start(client, "T1")
    cid = a1["case_id"]
    wav = client.get("/v1/demo/audio/synthetic.wav").content
    v = client.post("/v1/voice/score", files={"file": ("c.wav", wav, "audio/wav")},
                    data={"demo_hint": "synthetic", "case_id": cid}).json()
    assert v["mock"] is True and "NOT A DETECTOR" in v["model_version"]
    assert v["quality"]["ok"] and v["band"] == "likely_synthetic" and v["audio_retained"] is False
    assert "voice_likely_synthetic" in v["assessment"]["signals"]
    short = client.get("/v1/demo/audio/short.wav").content
    v2 = client.post("/v1/voice/score", files={"file": ("s.wav", short, "audio/wav")}, data={"demo_hint": "bonafide"}).json()
    assert v2["quality"]["ok"] is False and v2["band"] == "inconclusive"
    noisy = client.get("/v1/demo/audio/noisy.wav").content
    v3 = client.post("/v1/voice/score", files={"file": ("n.wav", noisy, "audio/wav")}).json()
    assert v3["quality"]["snr_db"] < 10 and v3["band"] == "inconclusive"
    # deterministic without hint
    v4 = client.post("/v1/voice/score", files={"file": ("c.wav", wav, "audio/wav")}).json()
    v5 = client.post("/v1/voice/score", files={"file": ("c.wav", wav, "audio/wav")}).json()
    assert v4["p_synthetic"] == v5["p_synthetic"]


def test_cases_rbac_and_access_log(client):
    start(client, "T1")
    assert client.get("/v1/cases", headers={"X-Role": "teller"}).status_code == 403
    lst = client.get("/v1/cases", headers=ANALYST).json()
    assert len(lst) >= 5 and {"red", "amber", "green"} >= {c["tier"] for c in lst}
    cid = lst[0]["case_id"]
    client.get(f"/v1/cases/{cid}", headers=ANALYST)
    log = client.get("/v1/access-log", headers=ANALYST).json()
    assert any(e["case_id"] == cid and e["action"] == "view_case" for e in log)
    r = client.post(f"/v1/cases/{cid}/decision", json={"decision": "false_positive"}, headers={"X-Role": "auditor"})
    assert r.status_code == 403


def test_analyst_decisions(client, device_factory):
    sc, a1 = start(client, "T1")
    cid = a1["case_id"]
    client.post("/v1/risk/assess", json={"case_id": cid, "claim": "family", "claim_target": "rel_rahul"})
    fv_answer(client, device_factory, sc, cid, "no")
    r = client.post(f"/v1/cases/{cid}/decision", json={"decision": "confirm_fraud", "note": "relative denied"},
                    headers=ANALYST).json()
    assert r["status"] == "confirmed_fraud"
    # release on another held case
    lst = client.get("/v1/cases", headers=ANALYST).json()
    other = next(c for c in lst if c["hold"] and c["case_id"] != cid and c["status"] == "held")
    assert other["payee_name"] == "Suresh Kumar"
    r2 = client.post(f"/v1/cases/{other['case_id']}/decision", json={"decision": "release_hold"}, headers=ANALYST).json()
    assert r2["status"] == "released"


def test_evidence_pack_signed_and_prefilled(client, device_factory):
    sc, a1 = start(client, "T1")
    cid = a1["case_id"]
    client.post("/v1/risk/assess", json={"case_id": cid, "claim": "family", "claim_target": "rel_rahul"})
    fv_answer(client, device_factory, sc, cid, "no")
    client.post(f"/v1/cases/{cid}/user-action", json={"action": "report"})
    pack = client.post(f"/v1/cases/{cid}/evidence-pack").json()
    assert pack["verification"]["ok"]
    assert pack["signature"]["alg"] == "Ed25519"
    assert pack["prefill"]["chakshu"]["fields"]["Suspected fraud communication category"] == "Impersonation as a relative / friend"
    assert pack["prefill"]["ncrp"]["fields"]["Suspect mobile number"] == "+447700900123"
    assert pack["payer"]["phone_masked"].endswith("210") and "98123" not in pack["payer"]["phone_masked"]
    assert pack["hash_chain"]["verified"] and pack["hash_chain"]["length"] >= 6


def test_voice_panel_needs_the_real_service_and_long_uploads_are_not_cut(client, monkeypatch):
    monkeypatch.delenv("VOICE_SERVICE_URL", raising=False)
    wav = client.get("/v1/demo/audio/bonafide.wav").content
    r = client.post("/v1/voice/panel", files={"file": ("k.wav", wav, "audio/wav")})
    assert r.status_code == 503 and "unavailable" in r.json()["detail"]   # never a mock panel
    long = wav * 4                                                          # > 12 s: used to be cut mid-stream
    v = client.post("/v1/voice/score", files={"file": ("l.wav", long, "audio/wav")}).json()
    assert v["audio_retained"] is False and "band" in v


def test_split_payments_during_one_call_are_still_assessed(client):
    """SPEC v0.3: Rs 9,500 again and again to one payee during one call. Every payment after the first is still
    assessed (the running total reaches Rs 10,000, and a payee first paid during this call stays new), and the
    payments made during the call never earn the trusted bypass (G5)."""
    client.post("/v1/demo/scenario/T1")
    call = {"state": "active", "number": "+919000012345", "channel": "pstn"}
    pay = {"payee_vpa": "split.test@okdemo", "payee_name": "Split Test", "amount_inr": 9500}

    def assess(c=call):
        return client.post("/v1/risk/assess", json={"payer_id": "u_sunita", "call": c, "payment": pay}).json()

    for i in range(4):
        a = assess()
        assert a["triggered"] and a["ask_claim"] and a["case_id"], (i, a)
        assert "new payee" in a["trigger"]["why"]
        assert ("split payments" in " ".join(a["trigger"]["why"])) == (i > 0)
        assert not any(g["id"] == "G5" for g in a.get("guardrails", []))
        assert client.post(f"/v1/cases/{a['case_id']}/user-action", json={"action": "continue"}).json()["status"] == "sent"
    # a later, different call: the payee was paid before it, and Rs 9,500 alone is below every rule
    assert assess(dict(call, number="+919000054321"))["triggered"] is False


def test_family_verify_rate_limit(client):
    """SPEC v0.3 section 6: at most 3 Family Verify pushes per payer per hour. After that the payer is told to call
    the relative, and the auto-sent push is skipped instead of failing the assessment."""
    sc, a1 = start(client, "L2")
    cid = a1["case_id"]
    ch = client.post("/v1/risk/assess", json={"case_id": cid, "claim": "family", "claim_target": "rel_rahul"}).json()[
        "auto_family_verify"]
    for _ in range(2):
        assert client.post(f"/v1/verify/family/{ch['challenge_id']}/cancel").status_code == 200
        r = client.post("/v1/verify/family", json={"case_id": cid, "relative_id": "rel_rahul"})
        assert r.status_code == 200, r.text
        ch = r.json()
    assert client.post(f"/v1/verify/family/{ch['challenge_id']}/cancel").status_code == 200
    r = client.post("/v1/verify/family", json={"case_id": cid, "relative_id": "rel_rahul"})
    assert r.status_code == 429 and "saved number" in r.json()["detail"]
    a2 = client.post("/v1/risk/assess", json={"payer_id": sc["payer"]["id"], "payment": sc["payment"], "call": sc["call"]}).json()
    a3 = client.post("/v1/risk/assess", json={"case_id": a2["case_id"], "claim": "family", "claim_target": "rel_rahul"})
    assert a3.status_code == 200 and "saved number" in a3.json()["auto_family_verify"]["skipped"]


def test_jury_builds_their_own_case(client):
    """FINALE_PLAN B1: the jury sets the inputs; the case runs through the same pipeline as the fixed scenarios."""
    def custom(**kw):
        r = client.post("/v1/demo/custom", params={"background": False}, json=kw)
        assert r.status_code == 200, r.text
        sc = r.json()
        a = client.post("/v1/risk/assess", json={"payer_id": sc["payer"]["id"], "payment": sc["payment"],
                                                 "call": sc["call"], "scenario": sc["scenario"]}).json()
        return sc, a

    sc, a = custom(caller="international", channel="whatsapp", amount_inr=50000, payee="new", payee_name="Arif Traders")
    assert sc["scenario"] == "CUSTOM" and sc["payee_new"] and sc["relative"]["id"] == "rel_rahul"
    assert a["triggered"] and a["ask_claim"]
    a2 = client.post("/v1/risk/assess", json={"case_id": a["case_id"], "claim": "family", "claim_target": "rel_rahul"}).json()
    assert "payee_name_mismatch" in a2["signals"] and a2["auto_family_verify"]["auto"] is True
    # Restart rebuilds the same case
    assert client.post("/v1/demo/scenario/CUSTOM", params={"background": False}).json()["payment"] == sc["payment"]

    # 1600 number: the registry tells a real bank call from a spoofed one
    for calling, want in ((True, "active_call_1600"), (False, "no_active_call")):
        sc, a = custom(caller="bank_1600", amount_inr=35000, payee="new", payee_name="Safe Account Desk", bank_calling=calling)
        client.post("/v1/risk/assess", json={"case_id": a["case_id"], "claim": "bank", "claim_target": "bdb"})
        r = client.post(f"/v1/cases/{a['case_id']}/checks/bank_registry").json()
        assert r["checks"]["bank_registry"]["result"] == want, (calling, r["checks"])
        assert (r["tier"] == "red") == (not calling)

    # SPEC v0.3: half an hour after the call, a large amount is still assessed and a smaller one isn't
    _, a = custom(caller="unknown", call_state="ended", ended_min=30, amount_inr=60000, payee="new")
    assert a["triggered"] and a["trigger"]["call_condition"]
    _, a = custom(caller="unknown", call_state="ended", ended_min=30, amount_inr=40000, payee="new")
    assert not a["triggered"] and not a["trigger"]["call_condition"]
    _, a = custom(caller="saved", payee="usual", amount_inr=45000)
    assert a["tier"] == "green" and a["case_id"] is None


def test_call_from_a_circle_members_saved_number_is_still_asked(client, device_factory):
    """SPEC v0.3 (red-team run): the caller ID shows the son's saved number (spoofed, or his WhatsApp taken over).
    The context alone is Green, yet the payer is asked, and "Family member" gets the son's own phone to confirm."""
    sc = client.post("/v1/demo/custom", params={"background": False},
                     json={"caller": "saved", "amount_inr": 40000, "payee": "new", "payee_name": "Arif Traders"}).json()
    son = device_factory(client, "dev_rahul", "rel_rahul")  # bound long before the call
    a = client.post("/v1/risk/assess", json={"payer_id": "u_sunita", "payment": sc["payment"], "call": sc["call"]}).json()
    assert a["tier"] == "green" and a["ask_claim"] and a["case_id"]
    b = client.post("/v1/risk/assess", json={"case_id": a["case_id"], "claim": "family", "claim_target": "rel_rahul"}).json()
    ch = b["auto_family_verify"]
    assert b["tier"] == "green" and ch["auto"] is True   # v0.3: the push goes out at Green too
    nonce = client.get("/v1/devices/dev_rahul/challenges").json()[0]["nonce"]
    r = client.post(f"/v1/verify/family/{ch['challenge_id']}/respond",
                    json={"answer": "no", "device_id": "dev_rahul", "signature_b64": son.sign(ch["challenge_id"], nonce, "no")})
    assert r.json()["tier"] == "red"
    # "No one asked me" on the same call: no push to the son, so his honest "no" can't hold her own payment
    a2 = client.post("/v1/risk/assess", json={"payer_id": "u_sunita", "payment": dict(sc["payment"], payee_vpa="shop@okdemo"),
                                              "call": sc["call"]}).json()
    b2 = client.post("/v1/risk/assess", json={"case_id": a2["case_id"], "claim": "none"}).json()
    assert b2["tier"] == "green" and "auto_family_verify" not in b2


def test_redteam_results_are_served(client):
    r = client.get("/v1/redteam")
    assert r.status_code == 200
    rows = r.json()["rows"]
    assert len(rows) >= 16 and all({"id", "evasion", "outcome", "observed", "why"} <= set(x) for x in rows)


def test_voice_hit_goes_to_analyst_review_only(client):
    """SPEC v0.3: a likely-synthetic voice result flags the case for analyst review; the payer's side is untouched."""
    sc, a1 = start(client, "T1")
    cid = a1["case_id"]
    before = client.post("/v1/risk/assess", json={"case_id": cid, "claim": "family", "claim_target": "rel_rahul"}).json()
    wav = client.get("/v1/demo/audio/synthetic.wav").content
    v = client.post("/v1/voice/score", files={"file": ("c.wav", wav, "audio/wav")},
                    data={"demo_hint": "synthetic", "case_id": cid}).json()
    assert v["band"] == "likely_synthetic" and v["used_in_decision"] is False
    assert v["assessment"]["tier"] == before["tier"] and "review" not in v["assessment"]   # G2, G6
    case = client.get(f"/v1/cases/{cid}", headers=ANALYST).json()
    assert case["review"]["reason"] == "voice_likely_synthetic" and case["review"]["voice_mode"] == "shadow"
    assert any(c["case_id"] == cid and c["review"] for c in client.get("/v1/cases", headers=ANALYST).json())
    assert "review_flagged" in [e["type"] for e in case["events"]]


def test_voice_audio_is_never_written_to_disk(client, tmp_path):
    """SPEC section 6 / FINALE_PLAN C1: a voice check leaves no audio behind on the server."""
    sc, a1 = start(client, "T1")
    before = {p for p in tmp_path.rglob("*") if p.is_file()}
    wav = client.get("/v1/demo/audio/synthetic.wav").content
    v = client.post("/v1/voice/score", files={"file": ("c.wav", wav, "audio/wav")}, data={"case_id": a1["case_id"]}).json()
    assert v["audio_retained"] is False
    new = {p for p in tmp_path.rglob("*") if p.is_file()} - before
    audio = [p for p in tmp_path.rglob("*") if p.is_file() and (p.suffix.lower() in {".wav", ".mp3", ".m4a", ".ogg", ".webm", ".flac"}
                                                                or p.read_bytes()[:4] == b"RIFF")]
    assert not audio, audio
    assert all(p.suffix in {".db", ".db-wal", ".db-shm", ".json", ".pem"} for p in new), new


def no_call_payment(client, vpa, amount=5000):
    return client.post("/v1/risk/assess", json={"payer_id": "u_sunita", "call": {"state": "none"},
                                                "payment": {"payee_vpa": vpa, "payee_name": "Shop", "amount_inr": amount}}).json()


def test_abandoned_assessments_leave_no_history(client):
    """SPEC v0.3: assessing a payment records nothing. A payment that opens no case gets a payment_ref and counts only
    when the app reports it sent; abandoned or retried attempts leave the payee new."""
    sc, a = start(client, "L1")   # silent Green on a call
    assert a["case_id"] is None and a["status"] == "cleared_silently" and a["payment_ref"]
    for _ in range(3):            # tapped Pay with no call, then backed out at the PIN, three times
        r = no_call_payment(client, "never.paid@okdemo")
        assert r["triggered"] is False and r["payment_ref"]
    svc = client.app.state.svc
    for vpa in (sc["payment"]["payee_vpa"], "never.paid@okdemo"):
        assert svc.history.payee("u_sunita", vpa) is None
        assert svc.s.one("SELECT COUNT(*) AS n FROM sent_payments WHERE payee_vpa=?", (vpa,))["n"] == 0


def test_unpaid_attempts_never_earn_the_trusted_bypass(client):
    """The review's attack: three no-call attempts to a payee who was never paid used to make it 'paid three times',
    so a later scam call paying it got the trusted bypass (G5). Only confirmed payments count now."""
    client.post("/v1/demo/scenario/T1", params={"background": False})
    for _ in range(3):
        no_call_payment(client, "unpaid.desk@okdemo", 12000)
    call = {"state": "active", "number": "+447700900123", "channel": "whatsapp", "duration_sec": 300}
    pay = {"payee_vpa": "unpaid.desk@okdemo", "payee_name": "Unpaid Desk", "amount_inr": 12000}
    a = client.post("/v1/risk/assess", json={"payer_id": "u_sunita", "call": call, "payment": pay}).json()
    assert a["triggered"] and "new payee" in a["trigger"]["why"] and a["case_id"]
    assert not any(g["id"] == "G5" for g in a["guardrails"])
    # three payments that really went through, before the call, do make the payee familiar
    for _ in range(3):
        ref = no_call_payment(client, "paid.desk@okdemo", 12000)["payment_ref"]
        assert client.post(f"/v1/payments/{ref}/sent").json() == {"recorded": True}
    b = client.post("/v1/risk/assess", json={"payer_id": "u_sunita", "call": call,
                                             "payment": dict(pay, payee_vpa="paid.desk@okdemo")}).json()
    assert b["tier"] == "green" and b["case_id"] is None and any(g["id"] == "G5" for g in b["guardrails"])


def test_payment_confirmation_counts_once(client):
    """POST /v1/payments/{ref}/sent records a payment once; a case's payment counts on the move to 'sent', once."""
    client.post("/v1/demo/scenario/T1", params={"background": False})
    svc = client.app.state.svc
    ref = no_call_payment(client, "once@okdemo", 3000)["payment_ref"]
    first = client.post(f"/v1/payments/{ref}/sent")
    assert first.status_code == 200 and first.json() == {"recorded": True}
    again = client.post(f"/v1/payments/{ref}/sent")
    assert again.status_code == 200 and again.json() == {"recorded": False, "already": True}
    assert svc.history.payee("u_sunita", "once@okdemo") == {"count": 1, "usual_amount": 3000}
    assert client.post("/v1/payments/pay_0000000000000000/sent").status_code == 404
    sc, a = start(client, "T1")
    r1 = client.post(f"/v1/cases/{a['case_id']}/user-action", json={"action": "continue"}).json()
    r2 = client.post(f"/v1/cases/{a['case_id']}/user-action", json={"action": "continue"}).json()
    assert r1["status"] == r2["status"] == "sent" and r1["utr"] == r2["utr"]
    assert svc.history.payee("u_sunita", sc["payment"]["payee_vpa"])["count"] == 1


def test_a_long_call_keeps_its_earlier_payments(client):
    """SPEC v0.3: 'this call' runs from the call's start. 75 minutes into one call (digital arrest runs long), the
    ₹9,500 sent at its start still counts: the running total reaches ₹10,000 and the payee is still new."""
    client.post("/v1/demo/scenario/T1", params={"background": False})
    svc = client.app.state.svc
    call = {"state": "active", "number": "+447700900123", "channel": "whatsapp", "duration_sec": 300}
    pay = {"payee_vpa": "settlement.desk@okdemo", "payee_name": "Settlement Desk", "amount_inr": 9500}

    def assess(c):
        return client.post("/v1/risk/assess", json={"payer_id": "u_sunita", "call": c, "payment": pay}).json()

    a = assess(call)
    assert client.post(f"/v1/cases/{a['case_id']}/user-action", json={"action": "continue"}).json()["status"] == "sent"
    svc._clock_offset = timedelta(minutes=75)
    started = ist_iso(svc.now() - timedelta(seconds=300 + 75 * 60))
    for c in (dict(call, duration_sec=300 + 75 * 60),                          # the live duration
              {**call, "duration_sec": None, "started_at": started},           # or the start time
              {**call, "duration_sec": 300 + 75 * 60,                          # a start in the future is ignored
               "started_at": ist_iso(svc.now() + timedelta(hours=3))}):
        b = assess(c)
        assert b["triggered"] and "new payee" in b["trigger"]["why"], (c, b["trigger"])
        assert any("split payments" in w for w in b["trigger"]["why"])
    # with neither start nor duration the server can only look back an hour, which misses the first payment
    assert assess({**call, "duration_sec": None})["triggered"] is False


def test_analyst_decision_resolves_the_voice_review(client):
    """A decision on a case in the Needs review queue resolves the review and keeps the voice evidence."""
    sc, a1 = start(client, "T1")
    cid = a1["case_id"]
    wav = client.get("/v1/demo/audio/synthetic.wav").content
    client.post("/v1/voice/score", files={"file": ("c.wav", wav, "audio/wav")}, data={"demo_hint": "synthetic", "case_id": cid})
    assert "resolved" not in client.get(f"/v1/cases/{cid}", headers=ANALYST).json()["review"]
    r = client.post(f"/v1/cases/{cid}/decision", json={"decision": "false_positive", "note": "real son"}, headers=ANALYST)
    rv = r.json()["review"]
    assert rv["resolved"]["decision"] == "false_positive" and rv["resolved"]["by"] == "a.verma" and rv["resolved"]["at"]
    assert rv["reason"] == "voice_likely_synthetic" and rv["p_synthetic"] is not None and rv["model_version"]
    listed = next(c for c in client.get("/v1/cases", headers=ANALYST).json() if c["case_id"] == cid)
    assert listed["review"]["resolved"]["decision"] == "false_positive"
    case = client.get(f"/v1/cases/{cid}", headers=ANALYST).json()
    assert case["checks"]["voice"]["p_synthetic"] == rv["p_synthetic"]
    assert next(e for e in case["events"] if e["type"] == "analyst_decision")["data"]["review_resolved"] is True
