import json
import math

import pytest

from pehchaan import assess, default_config, load_config, should_ask_claim
from pehchaan.actions import actions_for
from pehchaan.explain import COPY, REASON_TEXT, format_inr, reason_text, violates_g6
from pehchaan.fusion import logit, sigmoid
from pehchaan.signals import ALL_SIGNALS
from pehchaan.trigger import TriggerInput, evaluate_trigger

CFG = default_config()
GUARDS = lambda a: [g.id for g in a.guardrails_applied]  # noqa: E731


# --------------------------------------------------------------------------- config
def test_config_covers_every_signal_with_basis_and_rationale():
    for code in ALL_SIGNALS:
        s = CFG.signals[code]
        assert s.basis in ("assumed", "measured")
        assert s.rationale.strip()
    assert CFG.prior.value == pytest.approx(1 / 400)
    assert {f: c.cap_lr for f, c in CFG.families.items()} == {"C": 60, "K": 30, "P": 30, "V": 8, "S": 30, "O": 300}


def test_math_matches_spec_formula():
    a = assess(["caller_unknown", "payee_new"])
    expected = logit(1 / 400) + math.log(4) + math.log(2.5)
    assert a.log_odds == pytest.approx(expected)
    assert a.p == pytest.approx(sigmoid(expected))
    assert sum(r.contribution for r in a.reasons) == pytest.approx(expected - a.prior_log_odds)


def test_family_cap_is_applied_on_ln_lr():
    # K raw = 4*6*3*30*3 = 6480 -> capped at 30
    a = assess(["caller_unknown", "caller_international", "caller_voip_unknown", "fri_very_high", "call_ongoing_long"])
    assert a.families["K"].capped
    assert a.families["K"].lr == pytest.approx(30)
    # watermark 50 is capped at 8 by V
    b = assess(["watermark_detected"])
    assert b.families["V"].lr == pytest.approx(8)


# --------------------------------------------------------------------------- guardrails
def test_voice_only_cannot_go_red_even_at_high_prior():
    a = assess(["voice_likely_synthetic", "watermark_detected"], prior=0.3)
    assert a.raw_tier == "red"
    assert a.tier == "amber"
    assert "G1" in GUARDS(a)


def test_voice_cannot_be_the_second_family_for_red():
    # K qualifies, V qualifies; without V counting there is only one family -> Amber (G1 + G2)
    a = assess(["caller_international", "caller_unknown", "voice_likely_synthetic"], prior=0.05)
    assert a.raw_tier == "red"
    assert a.tier == "amber"
    assert {"G1", "G2"} <= set(GUARDS(a))


def test_single_context_signal_cannot_go_red():
    a = assess(["payee_flagged_high"], prior=0.1)
    assert a.raw_tier == "red" and a.tier == "amber" and "G1" in GUARDS(a)
    b = assess(["fri_very_high"], prior=0.1)
    assert b.raw_tier == "red" and b.tier == "amber"


def test_single_family_saturated_cannot_go_red():
    a = assess(["caller_unknown", "caller_international", "fri_very_high", "call_ongoing_long"], prior=0.1)
    assert a.raw_tier == "red" and a.tier == "amber"


def test_fv_denied_plus_new_payee_is_red():
    a = assess(["fv_denied", "payee_new"])
    assert a.p >= 0.6
    assert a.tier == "red"
    assert "G1" not in GUARDS(a)


def test_t1_cloned_relative_full_flow_is_red():
    a = assess(["claim_family", "caller_unknown", "caller_international", "payee_new", "amount_gt_p95", "fv_denied"])
    assert a.tier == "red"


def test_fv_confirmed_is_green():
    a = assess(["claim_family", "caller_unknown", "caller_international", "payee_new", "amount_gt_p99", "fv_confirmed"])
    assert a.tier == "green"
    # and even when the score would otherwise be high
    b = assess(["claim_family", "payee_new", "fri_high", "caller_unknown", "fv_confirmed"], prior=0.2)
    assert b.tier == "green" and "G4" in GUARDS(b)


def test_callback_confirmed_is_green_but_flagged_payee_stays_amber():
    a = assess(["claim_family", "payee_new", "callback_confirmed"])
    assert a.tier == "green"
    b = assess(["claim_family", "payee_new", "payee_flagged_high", "fv_confirmed"])
    assert b.tier == "amber" and "G4" in GUARDS(b)


def test_conflicting_out_of_band_does_not_green():
    a = assess(["claim_family", "payee_new", "fv_confirmed", "callback_denied", "caller_unknown"])
    assert a.tier != "green"
    assert any(g.id == "G4" and g.effect == "not applied" for g in a.guardrails_applied)


def test_low_audio_quality_is_inconclusive_never_real():
    a = assess(["caller_unknown", "voice_no_strong_evidence"], voice_quality={"speech_sec": 2.5, "snr_db": 18})
    assert "voice_inconclusive" in a.signals and "voice_no_strong_evidence" not in a.signals
    assert "G3" in GUARDS(a)
    b = assess(["voice_likely_synthetic"], voice_quality={"speech_sec": 9, "snr_db": 6})
    assert b.signals == ["voice_inconclusive"]
    assert b.families["V"].ln_lr == pytest.approx(0)
    ok = assess(["voice_likely_synthetic"], voice_quality={"speech_sec": 9, "snr_db": 22})
    assert "G3" not in GUARDS(ok) and "voice_likely_synthetic" in ok.signals


def test_trusted_payee_bypass():
    trusted = {"prior_payments": 5, "usual_amount_inr": 20000, "amount_inr": 25000}
    a = assess(["caller_unknown", "caller_international", "amount_gt_p95", "claim_family"], trusted=trusted)
    assert a.tier == "green" and "G5" in GUARDS(a)
    assert not should_ask_claim(a)
    too_much = {"prior_payments": 5, "usual_amount_inr": 20000, "amount_inr": 40000}
    assert "G5" not in GUARDS(assess(["caller_unknown"], trusted=too_much))
    too_few = {"prior_payments": 2, "usual_amount_inr": 20000, "amount_inr": 20000}
    assert "G5" not in GUARDS(assess(["caller_unknown"], trusted=too_few))


def test_claim_authority_alone_is_not_red():
    a = assess(["claim_authority", "payee_new"])
    assert a.tier == "amber"
    # high prior: raw score is Red, but C is the only family with LR >= 3 (P = 2.5)
    a2 = assess(["claim_authority", "payee_new"], prior=0.05)
    assert a2.raw_tier == "red" and a2.tier == "amber" and "G1" in GUARDS(a2)
    # note: payee_new x amount_gt_p95 = 4.5 already qualifies P as a second family
    a3 = assess(["claim_authority", "payee_new", "amount_gt_p95"], prior=0.05)
    assert a3.tier == "red"


def test_claim_authority_red_with_another_qualifying_family():
    a = assess(["claim_authority", "caller_unknown", "caller_voip_unknown", "payee_new", "amount_gt_p95"])
    assert set(a.qualifying_families) >= {"C", "K"}
    assert a.tier == "red"


def test_claim_authority_red_with_out_of_band_negative():
    a = assess(["claim_authority", "payee_new", "bank_no_active_call"])
    assert a.tier == "red"


def test_t2_bank_claim_with_registry_negative_is_red():
    a = assess(["claim_bank", "caller_unknown", "bank_claim_not_1600", "payee_new", "bank_no_active_call"])
    assert a.tier == "red"


def test_genuine_1600_bank_call_is_low():
    a = assess(["claim_bank", "caller_unknown", "payee_new", "bank_active_call_1600"])
    assert a.tier == "green"


def test_l1_friend_on_call_is_green_and_not_asked():
    a = assess(["payee_new"])
    assert a.tier == "green"
    assert not should_ask_claim(a)


def test_unknown_caller_triggers_question():
    a = assess(["caller_unknown", "payee_new"])
    assert a.tier == "green" and should_ask_claim(a)


def test_exclusive_groups_do_not_double_count():
    a = assess(["fri_medium", "fri_very_high", "amount_gt_p95", "amount_gt_p99"])
    assert "fri_medium" not in a.signals and "amount_gt_p95" not in a.signals
    assert len(a.dropped) == 2


def test_unknown_signal_rejected():
    with pytest.raises(ValueError):
        assess(["definitely_not_a_signal"])


# --------------------------------------------------------------------------- text / G6
def test_every_signal_has_en_and_hi_text_without_accusation():
    for code in ALL_SIGNALS:
        en, hi = REASON_TEXT[code]
        assert en and hi
        assert any("ऀ" <= ch <= "ॿ" for ch in hi), f"{code} Hindi text has no Devanagari"
        assert not violates_g6(en), (code, violates_g6(en))
        assert not violates_g6(hi), (code, violates_g6(hi))
    for key, (en, hi) in COPY.items():
        assert not violates_g6(en) and not violates_g6(hi), key


def test_action_labels_without_accusation():
    for tier in ("green", "amber", "red"):
        for claim in ("family", "bank", "authority", "other", "none", None):
            for a in actions_for(tier, claim, amount_inr=50000, params={"relative": "Rahul", "bank": "Bharat Demo Bank"}):
                for txt in list(a.label.values()) + list((a.detail or {}).values()):
                    assert not violates_g6(txt), (tier, claim, a.id, txt)


def test_reason_templates_fill_params():
    t = reason_text("fv_denied", {"relative": "Rahul"})
    assert t["en"].startswith("Rahul said") and "Rahul" in t["hi"]
    t2 = reason_text("payee_new")
    assert t2["en"] == "You have never paid this person before."


def test_format_inr_indian_grouping():
    assert format_inr(50000) == "₹50,000"
    assert format_inr(150000) == "₹1,50,000"
    assert format_inr(12345678) == "₹1,23,45,678"


# --------------------------------------------------------------------------- actions / trigger
def test_actions_per_claim():
    ids = lambda acts: [a.id for a in acts]  # noqa: E731
    fam = ids(actions_for("amber", "family", params={"relative": "Rahul"}))
    assert fam[:3] == ["family_verify", "callback", "safeword"] and "continue_anyway" in fam
    assert "bank_registry" in ids(actions_for("amber", "bank"))
    assert "authority_fact" in ids(actions_for("amber", "authority"))
    cont = next(a for a in actions_for("amber", "family") if a.id == "continue_anyway")
    assert cont.enabled_after_sec == 5
    red = actions_for("red", "family", amount_inr=50000)
    rel = next(a for a in red if a.id == "release_early")
    assert rel.requires == "analyst_review"
    assert next(a for a in actions_for("red", "family", amount_inr=5000) if a.id == "release_early").requires == "positive_check"
    assert ids(actions_for("green", None)) == ["proceed"]


def test_trigger_rules():
    assert evaluate_trigger(TriggerInput(call_active=True, payee_new=True, amount_inr=500)).fired
    assert evaluate_trigger(TriggerInput(call_ended_sec_ago=540, amount_inr=10000)).fired
    assert not evaluate_trigger(TriggerInput(call_ended_sec_ago=660, amount_inr=50000, payee_new=True)).fired
    assert not evaluate_trigger(TriggerInput(call_active=True, amount_inr=900, amount_p95_inr=2000)).fired
    assert evaluate_trigger(TriggerInput(call_active=True, amount_inr=2500, amount_p95_inr=2000)).fired


# --------------------------------------------------------------------------- measured voice swap
def test_measured_voice_lr_swap(tmp_path):
    metrics = {"model_version": "xlsr-aasist-0.3", "held_out": {"band_rates": {
        "spoof": {"likely_synthetic": 0.55, "inconclusive": 0.30, "no_strong_evidence": 0.15},
        "bonafide": {"likely_synthetic": 0.05, "inconclusive": 0.20, "no_strong_evidence": 0.75}}}}
    mp = tmp_path / "metrics.json"
    mp.write_text(json.dumps(metrics))
    cfg = load_config(overrides={"voice": {"lr_source": str(mp)}})
    assert cfg.signals["voice_likely_synthetic"].basis == "measured"
    assert cfg.signals["voice_likely_synthetic"].lr == pytest.approx(11.0)
    assert cfg.signals["voice_inconclusive"].lr == pytest.approx(1.5)
    # 0.2 measured -> floored at 0.7 (G2 safety floor)
    assert cfg.signals["voice_no_strong_evidence"].lr == pytest.approx(0.7)
    assert cfg.voice.model_version == "xlsr-aasist-0.3"
    # the default config is untouched
    assert default_config().signals["voice_likely_synthetic"].basis == "assumed"


def test_measured_voice_direct_band_lr(tmp_path):
    mp = tmp_path / "m.json"
    mp.write_text(json.dumps({"fusion": {"band_lr": {"voice_likely_synthetic": 6.5, "voice_no_strong_evidence": 0.9}}}))
    cfg = load_config(overrides={"voice": {"lr_source": str(mp)}})
    assert cfg.signals["voice_likely_synthetic"].lr == pytest.approx(6.5)
    assert cfg.signals["voice_no_strong_evidence"].lr == pytest.approx(0.9)
