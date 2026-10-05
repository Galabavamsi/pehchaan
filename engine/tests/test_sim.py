import json

import numpy as np
import pytest

from pehchaan import assess, default_config, should_ask_claim
from pehchaan.sim import IDX, SIG, BatchEngine, base_rate_prior, load_assumptions, simulate

CFG = default_config()
TIER = {"green": 0, "amber": 1, "red": 2}
V02_CODES = ["claim_upi_or_shop", "bank_registry_unknown", "bank_active_call_1600", "bank_no_active_call",
             "fv_denied", "callback_denied", "safeword_failed", "fv_confirmed", "callback_confirmed"]


def _random_sets(rng, n):
    """Random signal sets incl. exclusive-group collisions, voice/quality and trusted flags."""
    X = rng.random((n, len(SIG))) < rng.uniform(0.04, 0.3, size=(n, 1))
    quality_ok = rng.random(n) < 0.6
    trusted = rng.random(n) < 0.08
    return X, quality_ok, trusted


def _check_parity(X, prior, q=None, t=None, cfg=CFG):
    eng = BatchEngine(cfg)
    r = eng.assess(X, prior, quality_ok=q, trusted=t)
    for i in range(X.shape[0]):
        codes = [SIG[j] for j in np.flatnonzero(X[i])]
        vq = None if (q is None or q[i]) else {"speech_sec": 2.0, "snr_db": 20.0}
        tr = {"prior_payments": 5, "usual_amount_inr": 10000, "amount_inr": 10000} if (t is not None and t[i]) else None
        a = assess(codes, prior=prior, voice_quality=vq, trusted=tr, cfg=cfg)
        assert r.p[i] == pytest.approx(a.p, rel=1e-9, abs=1e-12), (i, codes)
        assert r.raw_tier[i] == TIER[a.raw_tier], (i, codes)
        assert r.tier[i] == TIER[a.tier], (i, codes, a.guardrails_applied)
        assert bool(r.ask[i]) == should_ask_claim(a, cfg), (i, codes)
        assert set(SIG[j] for j in np.flatnonzero(r.X[i])) == set(a.signals), (i, codes)
    return r


@pytest.mark.parametrize("prior", [1 / 2000, 1 / 400, 1 / 100, 0.05, 0.3])
def test_vectorised_fusion_matches_engine(prior):
    rng = np.random.default_rng(7 + int(prior * 1e6))
    X, q, t = _random_sets(rng, 2000)
    _check_parity(X, prior, q, t)


def test_vectorised_fusion_matches_engine_on_realistic_sets():
    """Sparser, scenario-like sets (3 x 2,000) incl. every v0.2 code, so G7/G4/G1/strict-G2 boundaries are exercised."""
    rng = np.random.default_rng(11)
    pool = ["caller_unknown", "caller_international", "caller_voip_unknown", "bank_claim_not_1600", "fri_medium",
            "fri_high", "call_ongoing_long", "payee_new", "amount_gt_p95", "amount_gt_p99", "payee_flagged_medium",
            "payee_flagged_high", "payee_name_mismatch", "burst_new_payees", "claim_family", "claim_bank",
            "claim_authority", "claim_none", "claim_other", "fv_timeout", "voice_likely_synthetic",
            "voice_no_strong_evidence", "watermark_detected", "cue_secrecy", "cue_otp_pin", "cue_arrest_threat",
            "safeword_passed"] + V02_CODES
    n = 2000
    seen_tiers, g7_hits, g1_hits = set(), 0, 0
    for prior in (1 / 400, 1 / 1300, 0.02):
        X = np.zeros((n, len(SIG)), dtype=bool)
        for i in range(n):
            for c in rng.choice(pool, size=rng.integers(1, 8), replace=False):
                X[i, IDX[c]] = True
        r = _check_parity(X, prior)
        seen_tiers |= set(np.unique(r.tier).tolist())
        g7_hits += int(r.g7.sum())
        g1_hits += int(r.g1_capped.sum())
    assert seen_tiers == {0, 1, 2} and g7_hits > 0 and g1_hits > 0


def test_strict_g2_and_g7_paths_exercised():
    X = np.zeros((3, len(SIG)), dtype=bool)
    for c in ["claim_bank", "caller_unknown", "bank_claim_not_1600", "payee_new", "voice_likely_synthetic"]:
        X[0, IDX[c]] = True  # strict G2
    for c in ["claim_family", "fv_denied"]:
        X[1, IDX[c]] = True  # G7 with p < theta
    for c in ["claim_bank", "caller_unknown", "bank_claim_not_1600", "payee_new", "bank_registry_unknown"]:
        X[2, IDX[c]] = True  # registry unknown: neutral
    r = _check_parity(X, 1 / 400)
    assert bool(r.g2[0]) and r.tier[0] == 1
    assert bool(r.g7[1]) and r.tier[1] == 2
    assert r.tier[2] == 1 and not r.g7[2]


def test_base_rate_prior_anchor_near_1_in_1300():
    d = base_rate_prior(load_assumptions())
    assert 1 / 2000 < d["prior_derived"] < 1 / 900


def test_sim_smoke(tmp_path):
    out = simulate(n_genuine=4000, n_scam=1500, seed=3, out_dir=tmp_path, charts=False, verbose=False)
    s = out["summary"]
    assert s["assumption_driven_projection"] is True
    f = s["friction_budget_genuine_pct"]
    total = f["silent_green"] + f["one_tap_question_then_green"] + f["saw_pause_and_verify"]
    assert total == pytest.approx(100, abs=0.05)
    for k in ("T1", "T2", "T3"):
        c = s["catch_rates_pct"][k]
        assert 0 <= c["red_hold"] <= c["amber_plus"] <= 100
    for name in ("sim_summary.json", "sim_sensitivity.json", "sim_ablation.json", "sim_threshold_sweep.json",
                 "deck_numbers.json"):
        json.loads((tmp_path / name).read_text(encoding="utf-8"))
    assert len(out["sensitivity"]["rows"]) == 15
    assert [r["level"] for r in out["ablation"]["rows"]] == ["context_only", "plus_claim", "plus_out_of_band", "plus_voice"]
    d = out["deck_numbers"]
    for key in ("genuine_silent_pct", "genuine_final_red_pct", "scam_T1_red_pct", "holds_per_scam_held_1_400",
                "holds_per_scam_held_1_1300", "inr_protected_per_inr_delayed", "theta_red",
                "zero_voice_scam_red_pct_1_400", "ablation_plus_out_of_band_scam_red_pct"):
        assert key in d
    assert all(isinstance(v, (int, float, str, bool)) or v is None for v in d.values())  # flat
    sw = out["sweep"]
    assert sw["theta_rows"] and sw["green_rows"] and "auto_registry" in sw["what_if"]


def test_sim_is_deterministic():
    a = simulate(n_genuine=3000, n_scam=1000, seed=5, out_dir=None, charts=False, verbose=False)["summary"]
    b = simulate(n_genuine=3000, n_scam=1000, seed=5, out_dir=None, charts=False, verbose=False)["summary"]
    assert a["catch_rates_pct"] == b["catch_rates_pct"]
    assert a["friction_budget_genuine_pct"] == b["friction_budget_genuine_pct"]


def test_upi_or_shop_claim_never_picks_up_bank_checks():
    """Merchants answering 'UPI app, shop or delivery' must not get bank_claim_not_1600 / registry signals."""
    from pehchaan.sim import C_UPI, Sessions, generate, run_flow  # noqa: F401
    A = load_assumptions()
    rng = np.random.default_rng(0)
    S = generate(A, {"G_merchant": 4000}, rng, A["detector"]["band_rates"])
    R = run_flow(S, BatchEngine(CFG), 1 / 400, 0.3, 3)
    upi = S["claim"] == C_UPI
    fx = R["final_X"]
    for code in ("bank_claim_not_1600", "bank_no_active_call", "bank_registry_unknown", "bank_active_call_1600"):
        assert not fx[upi, IDX[code]].any()
