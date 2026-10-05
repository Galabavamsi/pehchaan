import copy

from pehchaan import assess
from pehchaan.evidence import (
    Signer,
    append_event,
    build_evidence_pack,
    chakshu_prefill,
    mask_phone,
    ncrp_prefill,
    verify_chain,
    verify_pack,
)


def _case():
    a = assess(["claim_family", "caller_unknown", "caller_international", "payee_new", "fv_denied"],
               params={"relative": "Rahul", "payee": "Arif Traders", "country": "+44 United Kingdom"})
    return {
        "case_id": "PCH-TEST-0001", "created_at_ist": "2026-10-06T10:30:00+05:30", "payer_name": "Sunita Sharma",
        "payer_phone": "+919812345210", "payer_vpa_masked": "sunita.s••@bdb", "payee_vpa": "ariftraders@okdemo",
        "payee_name": "Arif Traders", "amount_inr": 50000, "amount_display": "₹50,000", "status": "held",
        "caller_number": "+447700900123", "call_channel": "whatsapp", "claim": "family", "relative_name": "Rahul",
        "tier": a.tier, "p": a.p, "guardrails": [g.model_dump() for g in a.guardrails_applied],
        "reasons": [r.model_dump() for r in a.reasons], "config_version": a.config_version,
    }


def _events():
    chain = []
    append_event(chain, "payment_attempt", "payer_app", {"amount": 50000})
    append_event(chain, "claim", "payer_app", {"claim": "family"})
    append_event(chain, "fv_response", "relative_device", {"answer": "no", "sig_ok": True})
    append_event(chain, "hold_started", "risk_api", {"minutes": 30})
    return chain


def test_hash_chain_detects_tampering():
    chain = _events()
    assert verify_chain(chain) == (True, "ok")
    bad = copy.deepcopy(chain)
    bad[1]["data"]["claim"] = "bank"
    ok, msg = verify_chain(bad)
    assert not ok and "event 1" in msg
    dropped = chain[:1] + chain[2:]
    assert not verify_chain(dropped)[0]


def test_pack_signature_roundtrip_and_tamper():
    signer = Signer.ephemeral()
    pack = build_evidence_pack(_case(), _events(), signer)
    assert pack["signature"]["alg"] == "Ed25519"
    assert verify_pack(pack) == (True, "ok")
    tampered = copy.deepcopy(pack)
    tampered["payment"]["amount_inr"] = 5000
    assert verify_pack(tampered)[0] is False
    forged = copy.deepcopy(pack)
    forged["signature"]["public_key_b64"] = Signer.ephemeral().public_key_b64
    assert verify_pack(forged)[0] is False


def test_prefill_mappings():
    case = _case()
    n = ncrp_prefill(case)["fields"]
    assert n["Category of complaint"] == "Online Financial Fraud"
    assert n["Sub-category of complaint"] == "UPI Related Frauds"
    assert n["Suspect UPI ID / bank account"] == "ariftraders@okdemo"
    assert len(n["Additional information about the incident (min 200 characters)"]) >= 200
    c = chakshu_prefill(case)["fields"]
    assert c["Medium of suspected fraud communication"] == "WhatsApp"
    assert c["Suspected fraud communication category"] == "Impersonation as a relative / friend"
    assert c["Number from which communication received"] == "+447700900123"


def test_masking():
    assert mask_phone("+919812345210").endswith("210")
    assert "98123" not in mask_phone("+919812345210")


def test_signer_persists(tmp_path):
    s1 = Signer.load_or_create(tmp_path / "k.pem")
    s2 = Signer.load_or_create(tmp_path / "k.pem")
    assert s1.key_id == s2.key_id
