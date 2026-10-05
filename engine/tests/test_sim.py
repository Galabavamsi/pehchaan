import json

import numpy as np
import pytest

from pehchaan import assess, default_config, should_ask_claim
from pehchaan.sim import IDX, SIG, BatchEngine, base_rate_prior, load_assumptions, simulate

CFG = default_config()
TIER = {"green": 0, "amber": 1, "red": 2}


def _random_sets(rng, n):
    """Random signal sets incl. exclusive-group collisions, voice/quality and trusted flags."""
    X = rng.random((n, len(SIG))) < rng.uniform(0.04, 0.3, size=(n, 1))
    quality_ok = rng.random(n) < 0.6
    trusted = rng.random(n) < 0.08
    return X, quality_ok, trusted


@pytest.mark.parametrize("prior", [1 / 2000, 1 / 400, 1 / 100, 0.05, 0.3])
def test_vectorised_fusion_matches_engine(prior):
    rng = np.random.default_rng(7 + int(prior * 1e6))
    n = 600
    X, q, t = _random_sets(rng, n)
    eng = BatchEngine(CFG)
    r = eng.assess(X, prior, quality_ok=q, trusted=t)
    for i in range(n):
        codes = [SIG[j] for j in np.flatnonzero(X[i])]
        vq = None if q[i] else {"speech_sec": 2.0, "snr_db": 20.0}
        tr = {"prior_payments": 5, "usual_amount_inr": 10000, "amount_inr": 10000} if t[i] else None
        a = assess(codes, prior=prior, voice_quality=vq, trusted=tr, cfg=CFG)
        assert r.p[i] == pytest.approx(a.p, rel=1e-9, abs=1e-12), (i, codes)
        assert r.raw_tier[i] == TIER[a.raw_tier], (i, codes)
        assert r.tier[i] == TIER[a.tier], (i, codes, a.guardrails_applied)
        assert bool(r.ask[i]) == should_ask_claim(a, CFG), (i, codes)
        assert set(SIG[j] for j in np.flatnonzero(r.X[i])) == set(a.signals), (i, codes)


def test_vectorised_fusion_matches_engine_on_realistic_sets():
    """Sparser, scenario-like sets (2,000) so the Amber/Red boundary is exercised."""
    rng = np.random.default_rng(11)
    pool = ["caller_unknown", "caller_international", "caller_voip_unknown", "bank_claim_not_1600", "fri_medium",
            "fri_high", "call_ongoing_long", "payee_new", "amount_gt_p95", "amount_gt_p99", "payee_flagged_medium",
            "payee_flagged_high", "payee_name_mismatch", "claim_family", "claim_bank", "claim_authority", "claim_none",
            "fv_denied", "fv_confirmed", "fv_timeout", "callback_denied", "bank_no_active_call",
            "bank_active_call_1600", "safeword_failed", "voice_likely_synthetic", "voice_no_strong_evidence",
            "cue_secrecy", "cue_arrest_threat"]
    n = 2000
    X = np.zeros((n, len(SIG)), dtype=bool)
    for i in range(n):
        for c in rng.choice(pool, size=rng.integers(1, 7), replace=False):
            X[i, IDX[c]] = True
    eng = BatchEngine(CFG)
    r = eng.assess(X, 1 / 400)
    mism = 0
    for i in range(n):
        a = assess([SIG[j] for j in np.flatnonzero(X[i])], cfg=CFG)
        mism += r.tier[i] != TIER[a.tier]
    assert mism == 0
    assert set(np.unique(r.tier)) == {0, 1, 2}


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
    for name in ("sim_summary.json", "sim_sensitivity.json", "sim_ablation.json"):
        json.loads((tmp_path / name).read_text(encoding="utf-8"))
    assert len(out["sensitivity"]["rows"]) == 15
    assert [r["level"] for r in out["ablation"]["rows"]] == ["context_only", "plus_claim", "plus_out_of_band", "plus_voice"]


def test_sim_is_deterministic():
    a = simulate(n_genuine=3000, n_scam=1000, seed=5, out_dir=None, charts=False, verbose=False)["summary"]
    b = simulate(n_genuine=3000, n_scam=1000, seed=5, out_dir=None, charts=False, verbose=False)["summary"]
    assert a["catch_rates_pct"] == b["catch_rates_pct"]
    assert a["friction_budget_genuine_pct"] == b["friction_budget_genuine_pct"]
