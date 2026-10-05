"""SPEC v0.2 rules: G7 decisive floor, strict G2, G1 trigger-exclusion, registry-unknown, claim split."""
import math

import pytest

from pehchaan import assess, default_config
from pehchaan.actions import actions_for
from pehchaan.signals import DECISIVE_NEGATIVE, DECISIVE_POSITIVE, USER_REPORTED_NEGATIVE

CFG = default_config()


def G(a):
    return [g.id for g in a.guardrails_applied]


def IDS(acts):
    return [x.id for x in acts]


def test_config_v02_values():
    assert CFG.version.startswith("0.2")
    assert 0.6 <= CFG.tiers.red_at_or_above <= 0.95
    assert CFG.signals["callback_denied"].lr == 30
    assert CFG.signals["bank_active_call_1600"].lr == pytest.approx(0.05)
    assert CFG.signals["bank_registry_unknown"].lr == 1.0
    assert CFG.signals["claim_upi_or_shop"].lr == pytest.approx(0.8)
    assert DECISIVE_NEGATIVE == {"fv_denied", "bank_no_active_call"}
    assert USER_REPORTED_NEGATIVE == {"callback_denied", "safeword_failed"}
    assert "bank_active_call_1600" in DECISIVE_POSITIVE


# ---------------------------------------------------------------- G7
def test_g7_fv_denied_is_red_regardless_of_p():
    a = assess(["claim_family", "fv_denied"])  # known payee, no amount flag: p ~ 0.53
    assert a.p < CFG.tiers.red_at_or_above
    assert a.raw_tier == "amber" and a.tier == "red" and "G7" in G(a)
    assert "continue_anyway" not in IDS(actions_for(a.tier, "family"))


def test_g7_bank_no_active_call_is_red_regardless_of_p():
    a = assess(["claim_bank", "bank_no_active_call"])
    assert a.p < CFG.tiers.red_at_or_above and a.tier == "red" and "G7" in G(a)


def test_g7_beats_trusted_bypass():
    a = assess(["claim_family", "fv_denied"], trusted={"prior_payments": 5, "usual_amount_inr": 20000, "amount_inr": 25000})
    assert a.tier == "red" and "G5" not in G(a)


def test_user_reported_negatives_are_strong_not_decisive():
    a = assess(["claim_family", "payee_new", "callback_denied"])
    assert a.tier == "amber" and "G7" not in G(a)
    assert math.isclose(a.families["O"].lr, 30)
    b = assess(["claim_family", "payee_new", "safeword_failed"])
    assert b.tier == "amber"
    acts = actions_for("amber", "family", signals=a.signals)
    cancel = next(x for x in acts if x.id == "cancel_payment")
    assert cancel.primary and not any(x.primary for x in acts if x.kind == "check")


def test_user_reported_negative_counts_as_a_g1_family():
    a = assess(["claim_family", "caller_unknown", "caller_international", "payee_new", "callback_denied"])
    assert a.p >= CFG.tiers.red_at_or_above
    assert {"K", "O"} <= set(a.qualifying_families) and a.tier == "red" and "G7" not in G(a)


# ---------------------------------------------------------------- G1 trigger-exclusion
def test_g1_trigger_implied_payment_context_does_not_count():
    a = assess(["claim_authority", "payee_new", "amount_gt_p95"], prior=0.05)
    assert a.raw_tier == "red" and a.tier == "amber" and "G1" in G(a)
    assert "P" not in a.qualifying_families


@pytest.mark.parametrize("p_signal", ["payee_name_mismatch", "payee_flagged_medium", "payee_flagged_high", "burst_new_payees"])
def test_g1_payment_context_qualifies_only_via_non_trigger_signals(p_signal):
    a = assess(["claim_authority", "payee_new", p_signal], prior=0.05)
    assert "P" in a.qualifying_families
    assert a.tier == "red"


# ---------------------------------------------------------------- strict G2
def test_strict_g2_voice_cannot_be_what_tips_red():
    sig = ["claim_bank", "caller_unknown", "bank_claim_not_1600", "payee_new"]
    base = assess(sig)
    assert base.tier == "amber" and set(base.qualifying_families) >= {"C", "K"}
    a = assess(sig + ["voice_likely_synthetic"])
    assert a.raw_tier == "red" and a.tier == "amber"
    assert any(g.id == "G2" and "strict" in g.effect for g in a.guardrails_applied)


def test_strict_g2_allows_red_when_red_without_voice():
    sig = ["claim_authority", "caller_unknown", "caller_voip_unknown", "payee_new", "payee_flagged_medium"]
    assert assess(sig).tier == "red"
    assert assess(sig + ["voice_likely_synthetic"]).tier == "red"


# ---------------------------------------------------------------- registry
def test_registry_unknown_is_neutral_and_never_red():
    sig = ["claim_bank", "caller_unknown", "bank_claim_not_1600", "payee_new"]
    a = assess(sig + ["bank_registry_unknown"])
    b = assess(sig)
    assert a.p == pytest.approx(b.p) and a.tier == "amber" and "G7" not in G(a)


def test_registry_confirms_1600_call_is_decisive_positive():
    a = assess(["claim_bank", "caller_unknown", "payee_new", "amount_gt_p99", "payee_flagged_medium",
                "bank_active_call_1600"], prior=0.2)
    assert a.tier == "green" and "G4" in G(a)
    b = assess(["claim_bank", "payee_new", "payee_flagged_high", "bank_active_call_1600"])
    assert b.tier == "amber"


def test_registry_group_is_exclusive():
    a = assess(["claim_bank", "bank_no_active_call", "bank_registry_unknown"])
    assert "bank_registry_unknown" not in a.signals and a.tier == "red"


# ---------------------------------------------------------------- claim split + checklist
def test_claim_split_upi_or_shop_is_reassuring_and_gets_no_bank_checks():
    merchant = assess(["caller_unknown", "payee_new", "claim_upi_or_shop"])
    assert merchant.tier == "green"
    assert merchant.families["C"].lr == pytest.approx(0.8)
    acts = IDS(actions_for("amber", "upi_or_shop"))
    assert "bank_registry" not in acts and "callback_known" in acts
    bank = IDS(actions_for("amber", "bank", params={"bank": "Bharat Demo Bank"}))
    assert bank[0] == "bank_registry"


def test_cue_checklist_offered_for_coached_none_and_other_only():
    for claim in ("none", "other"):
        acts = actions_for("amber", claim)
        assert acts[0].id == "cue_checklist" and acts[0].primary
        assert "cue_checklist" not in IDS(actions_for("amber", claim, signals=["cue_secrecy"]))
    for claim in ("family", "bank", "upi_or_shop", "authority"):
        assert "cue_checklist" not in IDS(actions_for("amber", claim))
    assert "cue_checklist" not in IDS(actions_for("green", "none"))


def test_checklist_answers_raise_risk():
    base = assess(["caller_unknown", "caller_voip_unknown", "payee_new", "amount_gt_p95", "claim_none"])
    with_cues = assess(base.signals + ["cue_secrecy", "cue_otp_pin"])
    assert with_cues.p > base.p and with_cues.families["S"].lr == pytest.approx(30)  # 4 x 8 = 32 -> cap 30
