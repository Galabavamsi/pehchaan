"""Alert-budget simulator (SPEC section 8, V2).

A generative model of *triggered* payment sessions (payment during / <= 10 min
after a call, AND new payee / > p95 / >= Rs 10k), genuine and scam, run through
the real Pehchaan fusion config with the same staged flow as the app:

  stage 1  Pay tap: call + payment context only (K, P). If context is clearly
           benign (should_ask_claim is False) -> Green silently.
  stage 2  one-tap "Who asked you to make this payment?" (C) + claim-derived
           context (bank_claim_not_1600, payee_name_mismatch).
  stage 3  if Pause & Verify (Amber/Red) is shown: claim-specific checks
           (Family Verify, callback, safe word, bank registry) and the
           optional voice check (+ script cues from the same capture, G3).

Everything uncertain lives in engine/sim_assumptions.yaml. Results are an
ASSUMPTION-DRIVEN PROJECTION, not a measurement.

    cd engine && python -m pehchaan.sim            # full run (~30 s)
    cd engine && python -m pehchaan.sim --quick    # smoke run
"""
from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import yaml

from .config import DEFAULT_ML_METRICS, Config, _band_dict, _walk, default_config
from .signals import (
    ALL_SIGNALS,
    DECISIVE_NEGATIVE,
    DECISIVE_POSITIVE,
    EXCLUSIVE_GROUPS,
    FAMILIES,
    SIGNAL_FAMILY,
    VOICE_BANDS,
)

ENGINE_DIR = Path(__file__).resolve().parent.parent
ASSUMPTIONS_PATH = ENGINE_DIR / "sim_assumptions.yaml"
RESULTS_DIR = ENGINE_DIR / "results"
IST = timezone(timedelta(hours=5, minutes=30))

SIG = list(ALL_SIGNALS)
IDX = {s: i for i, s in enumerate(SIG)}
FAM = list(FAMILIES)  # C K P V S O
CLAIM_KEYS = ["family", "bank", "authority", "other", "none"]
TIER_NAMES = ["green", "amber", "red"]
CUES = ["cue_secrecy", "cue_urgency", "cue_otp_pin", "cue_arrest_threat", "cue_remote_app", "cue_refund_verification"]

DISCLAIMER = (
    "Assumption-driven projection. These numbers come from a synthetic session simulator whose every "
    "distribution is listed in engine/sim_assumptions.yaml (public base rates where cited, team assumptions "
    "otherwise). They show how the Pehchaan decision logic behaves under those assumptions; they are not "
    "measured outcomes on real customers."
)


# ---------------------------------------------------------------------------
# vectorised fusion: must match pehchaan.fusion.assess exactly (tested)
# ---------------------------------------------------------------------------
@dataclass
class BatchResult:
    p: np.ndarray
    log_odds: np.ndarray
    raw_tier: np.ndarray
    tier: np.ndarray
    ask: np.ndarray
    X: np.ndarray
    fam_ln: np.ndarray
    g1_capped: np.ndarray
    g4: np.ndarray
    g5: np.ndarray


class BatchEngine:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        n_s, n_f = len(SIG), len(FAM)
        self.W = np.zeros((n_s, n_f))
        for i, s in enumerate(SIG):
            self.W[i, FAM.index(SIGNAL_FAMILY[s])] = cfg.ln_lr(s)
        self.caps = np.array([cfg.ln_cap(f) for f in FAM])
        self.v_cols = np.array([IDX[s] for s in SIG if SIGNAL_FAMILY[s] == "V"])
        self.inconclusive = IDX["voice_inconclusive"]
        self.excl = [np.array([IDX[m] for m in members]) for members in EXCLUSIVE_GROUPS.values()]
        self.neg_cols = np.array([IDX[s] for s in sorted(DECISIVE_NEGATIVE)])
        self.pos_cols = np.array([IDX[s] for s in sorted(DECISIVE_POSITIVE)])
        g = cfg.guardrails
        self.min_ln = math.log(g.g1_min_family_lr)
        self.counted = np.array([f not in g.g1_excluded_families for f in FAM])
        self.min_fams = g.g1_min_families
        self.flag_col = IDX[g.g4_flag_exception]
        self.green, self.red = cfg.tiers.green_below, cfg.tiers.red_at_or_above
        self.ask_thr = cfg.tiers.ask_claim_at_or_above

    def assess(self, X: np.ndarray, prior: float, quality_ok: np.ndarray | None = None,
               trusted: np.ndarray | None = None) -> BatchResult:
        X = X.astype(bool, copy=True)
        n = X.shape[0]
        for cols in self.excl:  # first member present wins (most severe first)
            seen = np.zeros(n, dtype=bool)
            for c in cols:
                col = X[:, c].copy()
                X[:, c] = col & ~seen
                seen |= col
        if quality_ok is not None:  # G3
            bad = ~quality_ok & X[:, self.v_cols].any(axis=1)
            if bad.any():
                X[np.ix_(bad, self.v_cols)] = False
                X[bad, self.inconclusive] = True
        fam = X.astype(np.float64) @ self.W
        fam = np.clip(fam, -self.caps, self.caps)
        lo = math.log(prior / (1 - prior)) + fam.sum(axis=1)
        p = np.where(lo >= 0, 1 / (1 + np.exp(-np.abs(lo))), np.exp(-np.abs(lo)) / (1 + np.exp(-np.abs(lo))))
        raw = np.where(p >= self.red, 2, np.where(p >= self.green, 1, 0))
        tier = raw.copy()
        n_counted = ((fam >= self.min_ln - 1e-12) & self.counted).sum(axis=1)
        neg = X[:, self.neg_cols].any(axis=1)
        pos = X[:, self.pos_cols].any(axis=1)
        g5 = (trusted if trusted is not None else np.zeros(n, dtype=bool)) & ~neg
        g4 = ~g5 & pos & ~neg
        tier[g5] = 0
        tier[g4] = np.where(X[g4, self.flag_col], 1, 0)
        g1 = ~g5 & ~g4 & (tier == 2) & ~neg & (n_counted < self.min_fams)
        tier[g1] = 1
        ask = ~g5 & ((tier != 0) | (p >= self.ask_thr))
        return BatchResult(p=p, log_odds=lo, raw_tier=raw, tier=tier, ask=ask, X=X, fam_ln=fam,
                           g1_capped=g1, g4=g4, g5=g5)


# ---------------------------------------------------------------------------
# assumptions
# ---------------------------------------------------------------------------
def load_assumptions(path: Path = ASSUMPTIONS_PATH) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _probs(d: dict, keys: list[str]) -> np.ndarray:
    v = np.array([float(d.get(k, 0.0)) for k in keys])
    s = v.sum()
    if s <= 0:
        raise ValueError(f"empty distribution {d}")
    return v / s


def measured_band_rates(path: Path = DEFAULT_ML_METRICS) -> tuple[dict | None, str]:
    """Look for P(band | spoof) and P(band | bona fide) in the ML metrics file."""
    if not Path(path).exists():
        return None, "placeholder (ml/results/metrics.json not found)"
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover
        return None, f"placeholder (could not parse metrics.json: {exc})"
    found = []
    for p, node in _walk(data):
        if not isinstance(node, dict):
            continue
        for key in ("band_rates", "band_probs", "rates_by_band"):
            rates = node.get(key)
            if not isinstance(rates, dict):
                continue
            spoof = next((_band_dict(v) for k, v in rates.items() if any(t in k.lower() for t in ("spoof", "synthetic", "fake", "attack"))), None)
            bona = next((_band_dict(v) for k, v in rates.items() if any(t in k.lower() for t in ("bona", "genuine", "real", "human"))), None)
            if spoof and bona and all(b in spoof and b in bona for b in VOICE_BANDS):
                found.append((p, spoof, bona))
    if not found:
        return None, "placeholder (metrics.json has no band_rates with spoof+bonafide for all 3 bands)"
    held = [f for f in found if "held" in f[0].lower() or "unseen" in f[0].lower()]
    seen = [f for f in found if f not in held]
    unseen_spoof = (held or found)[0][1]
    seen_spoof = (seen or found)[0][1]
    bona = (held or found)[0][2]
    return ({"synthetic_seen": seen_spoof, "synthetic_unseen": unseen_spoof, "bonafide": bona},
            f"measured from {path} ({(held or found)[0][0]})")


# ---------------------------------------------------------------------------
# session generation
# ---------------------------------------------------------------------------
@dataclass
class Sessions:
    scenario: np.ndarray            # index into names
    names: list[str]
    kinds: list[str]
    n: int
    cols: dict[str, np.ndarray] = field(default_factory=dict)

    def __getitem__(self, k: str) -> np.ndarray:
        return self.cols[k]


def _lognormal(rng, med, sigma, n):
    return np.exp(np.log(med) + sigma * rng.standard_normal(n))


def generate(A: dict, n_by_scn: dict[str, int], rng: np.random.Generator, band_rates: dict) -> Sessions:
    meta = A["meta"]
    cap = float(meta["upi_p2p_cap_inr"])
    p99x = float(meta["p99_over_p95"])
    names = list(n_by_scn)
    kinds = [A["scenarios"][s]["kind"] for s in names]
    parts: dict[str, list[np.ndarray]] = {}

    def put(k, v):
        parts.setdefault(k, []).append(v)

    det = A["detector"]
    wm_rate = float(det["watermark_given_synthetic"]["value"])
    unseen_share = float(det["unseen_generator_share"])
    br = {k: _probs(v, VOICE_BANDS) for k, v in band_rates.items()}

    for si, name in enumerate(names):
        S = A["scenarios"][name]
        n = int(n_by_scn[name])
        u = lambda: rng.random(n)  # noqa: E731
        put("scenario", np.full(n, si))
        # payment: rejection-sample until the SPEC 2 trigger holds
        amount = np.minimum(_lognormal(rng, S["amount"]["median"], S["amount"]["sigma"], n), cap)
        p95 = _lognormal(rng, S["user_p95"]["median"], S["user_p95"]["sigma"], n)
        new = u() < S["payee"]["new"]
        for _ in range(200):
            trig = new | (amount > p95) | (amount >= 10000)
            bad = ~trig
            if not bad.any():
                break
            k = int(bad.sum())
            amount[bad] = np.minimum(_lognormal(rng, S["amount"]["median"], S["amount"]["sigma"], k), cap)
            p95[bad] = _lognormal(rng, S["user_p95"]["median"], S["user_p95"]["sigma"], k)
            new[bad] = rng.random(k) < S["payee"]["new"]
        put("amount", amount)
        put("payee_new", new)
        put("gt_p95", amount > p95)
        put("gt_p99", amount > p95 * p99x)
        put("trusted", ~new & (u() < S["payee"]["trusted_if_known"]))
        c = S["caller"]
        unknown = u() < c["unknown"]
        put("caller_unknown", unknown)
        put("caller_international", u() < c["international"])
        put("caller_voip_unknown", (u() < c["voip"]) & unknown)
        put("from_1600", u() < c["from_1600"])
        put("fri", rng.choice(4, size=n, p=_probs(S["fri"], ["none", "medium", "high", "very_high"])))
        put("call_long", u() < S["call_long"])
        put("payee_flag", rng.choice(3, size=n, p=_probs(S["payee_flag"], ["none", "medium", "high"])))
        put("burst", u() < S["burst"])
        put("claim", rng.choice(5, size=n, p=_probs(S["claim"], CLAIM_KEYS)))
        put("name_mismatch", u() < S["name_mismatch_if_family"])
        # voice capture (only used if the user runs the voice check)
        synth = u() < S["synthetic_audio"]
        unseen = u() < unseen_share
        band = np.empty(n, dtype=np.int64)
        for cls, mask in (("bonafide", ~synth), ("synthetic_seen", synth & ~unseen), ("synthetic_unseen", synth & unseen)):
            k = int(mask.sum())
            if k:
                band[mask] = rng.choice(3, size=k, p=br[cls])
        put("synthetic", synth)
        put("band", band)
        put("watermark", synth & (u() < wm_rate))
        put("quality_ok", u() < S["quality_ok"])
        for cue in CUES:
            put(cue, u() < S["cues"][cue])
        put("u_voice", u())
        # out-of-band checks
        fv = S["fv"]
        put("fv_enrolled", u() < fv["enrolled"])
        put("u_fv", u())
        put("fv_uptake", np.full(n, fv["uptake"]))
        put("fv_out", rng.choice(3, size=n, p=_probs(fv, ["confirmed", "denied", "timeout"])))
        cb = S["callback"]
        put("u_cb", u())
        put("cb_uptake", np.full(n, cb["uptake"]))
        put("cb_out", rng.choice(3, size=n, p=_probs(cb, ["confirmed", "denied", "no_answer"])))
        sw = S["safeword"]
        put("sw_has", u() < sw["has"])
        put("u_sw", u())
        put("sw_uptake", np.full(n, sw["uptake"]))
        put("sw_pass", u() < sw["pass"])
        rg = S["registry"]
        put("reg_covered", u() < rg["coverage"])
        put("u_reg", u())
        put("reg_uptake", np.full(n, rg["uptake"]))
        put("reg_active", u() < rg["active_call"])
        put("amber_cancel", np.full(n, S["amber_cancel"]))
        beh = A["behaviour"]
        rco = S.get("red_completes_override", {})
        put("red_complete_lo", np.full(n, rco.get("below_review", beh["red_scam_completes_below_review"]["value"])))
        put("red_complete_hi", np.full(n, rco.get("review", beh["red_scam_completes_review"]["value"])))

    cols = {k: np.concatenate(v) for k, v in parts.items()}
    sc = cols.pop("scenario")
    return Sessions(scenario=sc, names=names, kinds=kinds, n=len(sc), cols=cols)


# ---------------------------------------------------------------------------
# staged flow
# ---------------------------------------------------------------------------
LEVELS = {0: "context_only", 1: "plus_claim", 2: "plus_out_of_band", 3: "plus_voice"}


def _context_matrix(S: Sessions) -> np.ndarray:
    X = np.zeros((S.n, len(SIG)), dtype=bool)
    X[:, IDX["caller_unknown"]] = S["caller_unknown"]
    X[:, IDX["caller_international"]] = S["caller_international"]
    X[:, IDX["caller_voip_unknown"]] = S["caller_voip_unknown"]
    for k, code in ((1, "fri_medium"), (2, "fri_high"), (3, "fri_very_high")):
        X[:, IDX[code]] = S["fri"] == k
    X[:, IDX["call_ongoing_long"]] = S["call_long"]
    X[:, IDX["payee_new"]] = S["payee_new"]
    X[:, IDX["amount_gt_p99"]] = S["gt_p99"]
    X[:, IDX["amount_gt_p95"]] = S["gt_p95"] & ~S["gt_p99"]
    X[:, IDX["payee_flagged_medium"]] = S["payee_flag"] == 1
    X[:, IDX["payee_flagged_high"]] = S["payee_flag"] == 2
    X[:, IDX["burst_new_payees"]] = S["burst"]
    return X


def run_flow(S: Sessions, eng: BatchEngine, prior: float, voice_uptake: float, level: int = 3,
             review_at: float = 50000, amber_cancel_neg: float = 0.85, red_genuine_completes: float = 0.95) -> dict:
    n = S.n
    X1 = _context_matrix(S)
    a1 = eng.assess(X1, prior, trusted=S["trusted"])
    claim = S["claim"]
    if level == 0:
        asked = np.zeros(n, dtype=bool)
        shown = a1.tier >= 1
        final, final_X, p_final = a1.tier, a1.X, a1.p
        a2_tier = a1.tier
        checks = {}
    else:
        asked = a1.ask
        X2 = X1.copy()
        for ci, key in enumerate(CLAIM_KEYS):
            X2[:, IDX[f"claim_{key}"]] = claim == ci
        X2[:, IDX["bank_claim_not_1600"]] = (claim == 1) & ~S["from_1600"]
        X2[:, IDX["payee_name_mismatch"]] = (claim == 0) & S["name_mismatch"]
        a2 = eng.assess(X2, prior, trusted=S["trusted"])
        a2_tier = np.where(asked, a2.tier, a1.tier)
        shown = asked & (a2.tier >= 1)
        final = a2_tier.copy()
        final_X = np.where(asked[:, None], a2.X, a1.X)
        p_final = np.where(asked, a2.p, a1.p)
        checks = {}
        if level >= 2:
            X3 = X2.copy()
            fam = shown & (claim == 0)
            fv_taken = fam & S["fv_enrolled"] & (S["u_fv"] < S["fv_uptake"])
            fo = S["fv_out"]
            X3[:, IDX["fv_confirmed"]] = fv_taken & (fo == 0)
            X3[:, IDX["fv_denied"]] = fv_taken & (fo == 1)
            X3[:, IDX["fv_timeout"]] = fv_taken & (fo == 2)
            nodec = ~fv_taken | (fo == 2)
            cb_taken = fam & nodec & (S["u_cb"] < S["cb_uptake"])
            co = S["cb_out"]
            X3[:, IDX["callback_confirmed"]] = cb_taken & (co == 0)
            X3[:, IDX["callback_denied"]] = cb_taken & (co == 1)
            nodec2 = nodec & (~cb_taken | (co == 2))
            sw_taken = fam & nodec2 & S["sw_has"] & (S["u_sw"] < S["sw_uptake"])
            X3[:, IDX["safeword_passed"]] = sw_taken & S["sw_pass"]
            X3[:, IDX["safeword_failed"]] = sw_taken & ~S["sw_pass"]
            bank = shown & (claim == 1)
            reg_taken = bank & S["reg_covered"] & (S["u_reg"] < S["reg_uptake"])
            X3[:, IDX["bank_active_call_1600"]] = reg_taken & S["reg_active"]
            X3[:, IDX["bank_no_active_call"]] = reg_taken & ~S["reg_active"]
            quality = np.ones(n, dtype=bool)
            voice_done = np.zeros(n, dtype=bool)
            if level >= 3 and voice_uptake > 0:
                voice_done = shown & (S["u_voice"] < voice_uptake)
                for bi, b in enumerate(VOICE_BANDS):
                    X3[:, IDX[f"voice_{b}"]] = voice_done & (S["band"] == bi)
                X3[:, IDX["watermark_detected"]] = voice_done & S["watermark"]
                asr_ok = voice_done & S["quality_ok"]
                for cue in CUES:
                    X3[:, IDX[cue]] = asr_ok & S[cue]
                quality = np.where(voice_done, S["quality_ok"], True)
            a3 = eng.assess(X3, prior, quality_ok=quality, trusted=S["trusted"])
            final = np.where(shown, a3.tier, a2_tier)
            final_X = np.where(shown[:, None], a3.X, final_X)
            p_final = np.where(shown, a3.p, p_final)
            checks = {"fv": fv_taken, "callback": cb_taken, "safeword": sw_taken, "registry": reg_taken,
                      "voice": voice_done}

    amount = S["amount"]
    neg = final_X[:, eng.neg_cols].any(axis=1)
    amber_cancel = np.where(neg, amber_cancel_neg, S["amber_cancel"])
    red_complete = np.where(amount >= review_at, S["red_complete_hi"], S["red_complete_lo"])
    stopped = np.where(final == 2, 1 - red_complete, np.where(final == 1, amber_cancel, 0.0))
    return {
        "stage1": a1.tier, "stage2": a2_tier, "final": final, "p": p_final,
        "asked": asked, "shown": shown, "checks": checks,
        "stopped": stopped,
        "abandoned": np.where(final == 1, S["amber_cancel"], 0.0),
        "held": final == 2,
        "red_genuine_completes": red_genuine_completes,
    }


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------
def _pct(x: float) -> float:
    return round(100.0 * float(x), 3)


def _scn_stats(S: Sessions, R: dict, si: int) -> dict:
    m = S.scenario == si
    f = R["final"][m]
    d = {
        "n": int(m.sum()),
        "silent_green": float(np.mean(~R["asked"][m] & ~R["shown"][m])),
        "question_then_green": float(np.mean(R["asked"][m] & ~R["shown"][m])),
        "saw_pause_and_verify": float(np.mean(R["shown"][m])),
        "final_green": float(np.mean(f == 0)),
        "final_amber": float(np.mean(f == 1)),
        "final_red": float(np.mean(f == 2)),
        "amber_plus": float(np.mean(f >= 1)),
        "resolved_green_after_check": float(np.mean(R["shown"][m] & (f == 0))),
        "stopped": float(np.mean(R["stopped"][m])),
        "mean_amount": float(np.mean(S["amount"][m])),
    }
    for k, v in R["checks"].items():
        d[f"used_{k}"] = float(np.mean(v[m]))
    return d


def summarise(S: Sessions, R: dict, A: dict, prior: float) -> dict:
    mixg = {k: v for k, v in A["mix"]["genuine"].items() if k.startswith("G_")}
    mixs = {k: v for k, v in A["mix"]["scam"].items() if k.startswith("T")}
    zg, zs = sum(mixg.values()), sum(mixs.values())
    per = {name: _scn_stats(S, R, i) for i, name in enumerate(S.names)}

    def wavg(mix, z, key):
        return sum(per[k][key] * w for k, w in mix.items()) / z

    keys = ["silent_green", "question_then_green", "saw_pause_and_verify", "final_green", "final_amber",
            "final_red", "amber_plus", "resolved_green_after_check", "stopped"]
    genuine = {k: wavg(mixg, zg, k) for k in keys}
    scam = {k: wavg(mixs, zs, k) for k in keys}

    # per 100k triggered sessions at this prior (expectations, stratified weights)
    N = float(A["meta"]["report_per_sessions"])
    amount = S["amount"]
    inr_risk = inr_prot = inr_delay = inr_aband = 0.0
    g_held = g_pv = s_amber = s_red = s_stop = 0.0
    for i, name in enumerate(S.names):
        m = S.scenario == i
        if S.kinds[i] == "genuine":
            w = N * (1 - prior) * mixg[name] / zg / m.sum()
            inr_delay += w * float(np.sum(amount[m] * R["held"][m]))
            inr_aband += w * float(np.sum(amount[m] * R["abandoned"][m]))
            g_held += w * float(np.sum(R["held"][m]))
            g_pv += w * float(np.sum(R["shown"][m]))
        else:
            w = N * prior * mixs[name] / zs / m.sum()
            inr_risk += w * float(np.sum(amount[m]))
            inr_prot += w * float(np.sum(amount[m] * R["stopped"][m]))
            s_amber += w * float(np.sum(R["final"][m] >= 1))
            s_red += w * float(np.sum(R["held"][m]))
            s_stop += w * float(np.sum(R["stopped"][m]))
    reds = g_held + s_red
    per100k = {
        "genuine_sessions": round(N * (1 - prior), 1),
        "scam_sessions": round(N * prior, 1),
        "genuine_saw_pause_and_verify": round(g_pv, 1),
        "genuine_held_red": round(g_held, 1),
        "scams_amber_plus": round(s_amber, 2),
        "scams_held_red": round(s_red, 2),
        "scams_stopped_expected": round(s_stop, 2),
        "inr_at_risk_without_pehchaan": round(inr_risk),
        "inr_protected_expected": round(inr_prot),
        "inr_genuine_delayed_by_hold": round(inr_delay),
        "inr_genuine_abandoned_at_amber": round(inr_aband),
        "protected_per_rupee_delayed": round(inr_prot / inr_delay, 2) if inr_delay else None,
        "share_of_red_holds_that_are_scams": round(s_red / reds, 4) if reds else None,
        "genuine_holds_per_scam_held": round(g_held / s_red, 2) if s_red else None,
        "genuine_pause_verify_per_scam_amber_plus": round(g_pv / s_amber, 2) if s_amber else None,
    }
    return {"genuine": genuine, "scam": scam, "per_scenario": per, "per_100k": per100k}


def base_rate_prior(A: dict) -> dict:
    b = A["base_rates"]
    v = lambda k: float(b[k]["value"])  # noqa: E731
    cases = v("ncrp_complaints_per_year") / 12 * v("call_driven_share")
    scam_trig = cases * v("txns_per_scam_case") * v("scam_txn_meets_trigger")
    gen_trig = v("upi_txns_per_month") * v("genuine_trigger_rate")
    prior = scam_trig / (scam_trig + gen_trig)
    cross = v("upi_txns_per_month") * v("upi_fraud_per_mn_txns") / 1e6
    return {
        "call_driven_scam_cases_per_month": round(cases),
        "scam_triggered_txns_per_month": round(scam_trig),
        "genuine_triggered_txns_per_month": round(gen_trig),
        "prior_derived": prior,
        "prior_derived_as_fraction": f"1/{round(1 / prior)}",
        "cross_check_all_upi_frauds_per_month": round(cross),
        "note": ("pi0 = scam_triggered / (scam_triggered + genuine_triggered). The SPEC default 1/400 is ~3x more "
                 "scam-dense than this anchor, i.e. cautious: it over-states genuine friction."),
    }


def _frac(p: float) -> str:
    return f"1/{round(1 / p)}"


# ---------------------------------------------------------------------------
# main entry
# ---------------------------------------------------------------------------
def simulate(n_genuine: int | None = None, n_scam: int | None = None, seed: int | None = None,
             prior: float | None = None, voice_uptake: float | None = None, cfg: Config | None = None,
             assumptions: dict | None = None, out_dir: Path | None = RESULTS_DIR, charts: bool = True,
             verbose: bool = True) -> dict:
    t0 = time.time()
    cfg = cfg or default_config()
    A = assumptions or load_assumptions()
    meta = A["meta"]
    seed = int(meta["seed"] if seed is None else seed)
    n_genuine = int(meta["n_genuine"] if n_genuine is None else n_genuine)
    n_scam = int(meta["n_scam_per_pattern"] if n_scam is None else n_scam)
    prior = float(cfg.prior.value if prior is None else prior)
    beh = A["behaviour"]
    uptake = float(beh["voice_uptake"]["value"] if voice_uptake is None else voice_uptake)
    uptake_sweep = [float(x) for x in beh["voice_uptake"]["sweep"]]
    prior_sweep = [float(x) for x in A["prior"]["sweep"]]
    review_at = cfg.actions.analyst_review_at_or_above_inr
    kw = dict(review_at=review_at, amber_cancel_neg=beh["amber_cancel_if_decisive_negative"]["value"],
              red_genuine_completes=beh["red_genuine_completes"]["value"])

    measured, band_src = measured_band_rates()
    band_rates = measured or A["detector"]["band_rates"]

    mixg = {k: v for k, v in A["mix"]["genuine"].items() if k.startswith("G_")}
    zg = sum(mixg.values())
    # genuine scenarios share n_genuine by mix (min 2,000 each so rare ones are not noisy)
    n_by = {k: max(2000, int(round(n_genuine * w / zg))) for k, w in mixg.items()}
    for k in A["mix"]["scam"]:
        if k.startswith("T"):
            n_by[k] = n_scam
    rng = np.random.default_rng(seed)
    S = generate(A, n_by, rng, band_rates)
    eng = BatchEngine(cfg)

    # headline run
    R = run_flow(S, eng, prior, uptake, 3, **kw)
    head = summarise(S, R, A, prior)
    anchor = base_rate_prior(A)

    # national-scale illustration at the base-rate-derived prior
    pd_ = anchor["prior_derived"]
    Rn = run_flow(S, eng, pd_, uptake, 3, **kw)
    hn = summarise(S, Rn, A, pd_)
    monthly_sessions = anchor["genuine_triggered_txns_per_month"] + anchor["scam_triggered_txns_per_month"]
    k = monthly_sessions / float(meta["report_per_sessions"])
    national = {
        "label": "ILLUSTRATIVE ONLY: if every UPI app ran Pehchaan, at the base-rate-derived prior "
                 f"{anchor['prior_derived_as_fraction']} and the assumed 1% trigger rate",
        "triggered_sessions_per_month": round(monthly_sessions),
        "genuine_pause_and_verify_per_month": round(hn["per_100k"]["genuine_saw_pause_and_verify"] * k),
        "genuine_holds_per_month": round(hn["per_100k"]["genuine_held_red"] * k),
        "scam_payments_stopped_per_month": round(hn["per_100k"]["scams_stopped_expected"] * k),
        "inr_protected_crore_per_month": round(hn["per_100k"]["inr_protected_expected"] * k / 1e7, 1),
        "inr_genuine_delayed_crore_per_month": round(hn["per_100k"]["inr_genuine_delayed_by_hold"] * k / 1e7, 1),
        "genuine_holds_per_scam_held": hn["per_100k"]["genuine_holds_per_scam_held"],
    }

    def gp(d, key):
        return _pct(d[key])

    scen_labels = {k: A["scenarios"][k]["label"] for k in S.names}
    summary = {
        "assumption_driven_projection": True,
        "disclaimer": DISCLAIMER,
        "generated_at_ist": datetime.now(IST).isoformat(timespec="seconds"),
        "engine_config_version": cfg.version,
        "assumptions_file": "engine/sim_assumptions.yaml",
        "assumptions_version": meta["version"],
        "seed": seed,
        "n_sessions": {k: int(v) for k, v in n_by.items()},
        "prior": {"value": prior, "as_fraction": _frac(prior), "basis": "SPEC default (engine config)",
                  "base_rate_anchor": anchor},
        "voice": {"check_uptake": uptake, "band_rates_source": band_src,
                  "engine_voice_lr_basis": cfg.signals["voice_likely_synthetic"].basis,
                  "band_rates_used": band_rates},
        "flow": ("stage 1 context (K,P) -> one-tap claim question unless clearly benign (p < "
                 f"{cfg.tiers.ask_claim_at_or_above}) -> Pause & Verify if Amber/Red -> claim-specific checks + "
                 "optional voice check -> final tier"),
        "friction_budget_genuine_pct": {
            "silent_green": gp(head["genuine"], "silent_green"),
            "one_tap_question_then_green": gp(head["genuine"], "question_then_green"),
            "saw_pause_and_verify": gp(head["genuine"], "saw_pause_and_verify"),
            "resolved_to_green_by_a_check": gp(head["genuine"], "resolved_green_after_check"),
            "final_green": gp(head["genuine"], "final_green"),
            "final_amber": gp(head["genuine"], "final_amber"),
            "final_red_hold": gp(head["genuine"], "final_red"),
            "by_scenario": {
                k: {"label": scen_labels[k], "mix_weight": mixg[k],
                    **{kk: _pct(v) for kk, v in head["per_scenario"][k].items()
                       if kk not in ("n", "mean_amount", "stopped")}}
                for k in mixg
            },
        },
        "catch_rates_pct": {
            **{k: {"label": scen_labels[k], "mix_weight": A["mix"]["scam"][k],
                   "amber_plus": _pct(head["per_scenario"][k]["amber_plus"]),
                   "red_hold": _pct(head["per_scenario"][k]["final_red"]),
                   "stopped_expected": _pct(head["per_scenario"][k]["stopped"]),
                   "saw_pause_and_verify": _pct(head["per_scenario"][k]["saw_pause_and_verify"]),
                   **{kk: _pct(v) for kk, v in head["per_scenario"][k].items() if kk.startswith("used_")}}
               for k in S.names if A["scenarios"][k]["kind"] == "scam"},
            "all_scams_weighted": {"amber_plus": gp(head["scam"], "amber_plus"),
                                   "red_hold": gp(head["scam"], "final_red"),
                                   "stopped_expected": gp(head["scam"], "stopped")},
        },
        "per_100k_triggered_sessions": head["per_100k"],
        "national_scale_illustrative": national,
        "elapsed_sec": None,
    }

    # sensitivity: prior x voice uptake (engine uses the true prior each time)
    sens_rows = []
    for up in uptake_sweep:
        for pr in prior_sweep:
            Rs = run_flow(S, eng, pr, up, 3, **kw)
            h = summarise(S, Rs, A, pr)
            sens_rows.append({
                "prior": pr, "prior_fraction": _frac(pr), "voice_uptake": up,
                "genuine_saw_pause_and_verify_pct": gp(h["genuine"], "saw_pause_and_verify"),
                "genuine_final_amber_pct": gp(h["genuine"], "final_amber"),
                "genuine_red_pct": gp(h["genuine"], "final_red"),
                "scam_amber_plus_pct": gp(h["scam"], "amber_plus"),
                "scam_red_pct": gp(h["scam"], "final_red"),
                "scam_stopped_pct": gp(h["scam"], "stopped"),
                "per_pattern_red_pct": {k: _pct(h["per_scenario"][k]["final_red"]) for k in S.names if k.startswith("T")},
                "per_pattern_amber_plus_pct": {k: _pct(h["per_scenario"][k]["amber_plus"]) for k in S.names if k.startswith("T")},
                "share_of_red_holds_that_are_scams": h["per_100k"]["share_of_red_holds_that_are_scams"],
                "inr_protected_per_100k": h["per_100k"]["inr_protected_expected"],
                "inr_delayed_per_100k": h["per_100k"]["inr_genuine_delayed_by_hold"],
            })
    sensitivity = {"assumption_driven_projection": True, "disclaimer": DISCLAIMER, "seed": seed,
                   "note": "Same simulated sessions (common random numbers) re-scored at each prior and voice-check uptake.",
                   "rows": sens_rows}

    # ablation: what each layer adds (default prior and uptake)
    abl_rows = []
    for lvl, name in LEVELS.items():
        Ra = run_flow(S, eng, prior, uptake if lvl == 3 else 0.0, lvl, **kw)
        h = summarise(S, Ra, A, prior)
        abl_rows.append({
            "level": name,
            "label": {"context_only": "Context only (call + payment)", "plus_claim": "+ one-tap claim",
                      "plus_out_of_band": "+ out-of-band checks", "plus_voice": f"+ voice check ({uptake:.0%} uptake)"}[name],
            "genuine_saw_pause_and_verify_pct": gp(h["genuine"], "saw_pause_and_verify"),
            "genuine_final_amber_pct": gp(h["genuine"], "final_amber"),
            "genuine_red_pct": gp(h["genuine"], "final_red"),
            "scam_amber_plus_pct": gp(h["scam"], "amber_plus"),
            "scam_red_pct": gp(h["scam"], "final_red"),
            "scam_stopped_pct": gp(h["scam"], "stopped"),
            "per_pattern": {k: {"amber_plus_pct": _pct(h["per_scenario"][k]["amber_plus"]),
                                "red_pct": _pct(h["per_scenario"][k]["final_red"])}
                            for k in S.names if k.startswith("T")},
            "inr_protected_per_100k": h["per_100k"]["inr_protected_expected"],
        })
    ablation = {"assumption_driven_projection": True, "disclaimer": DISCLAIMER, "seed": seed,
                "prior": prior, "voice_uptake": uptake, "rows": abl_rows}

    summary["elapsed_sec"] = round(time.time() - t0, 2)
    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "sim_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        (out_dir / "sim_sensitivity.json").write_text(json.dumps(sensitivity, indent=2), encoding="utf-8")
        (out_dir / "sim_ablation.json").write_text(json.dumps(ablation, indent=2), encoding="utf-8")
        if charts:
            from .sim_charts import render_all
            render_all(summary, sensitivity, ablation, out_dir)
    if verbose:
        _print_headline(summary, ablation, sensitivity)
    return {"summary": summary, "sensitivity": sensitivity, "ablation": ablation}


def _print_headline(summary: dict, ablation: dict, sensitivity: dict) -> None:
    f = summary["friction_budget_genuine_pct"]
    print(f"[pehchaan.sim] prior {summary['prior']['as_fraction']}  voice uptake {summary['voice']['check_uptake']:.0%}  "
          f"({summary['voice']['band_rates_source'].split(' (')[0]} band rates)")
    print(f"  genuine: silent {f['silent_green']:.1f}%  question-only {f['one_tap_question_then_green']:.1f}%  "
          f"pause&verify {f['saw_pause_and_verify']:.2f}%  final amber {f['final_amber']:.2f}%  red {f['final_red_hold']:.3f}%")
    for k, v in summary["catch_rates_pct"].items():
        print(f"  {k:20s} amber+ {v['amber_plus']:5.1f}%  red {v['red_hold']:5.1f}%  stopped {v['stopped_expected']:5.1f}%")
    p = summary["per_100k_triggered_sessions"]
    print(f"  per 100k: protected Rs {p['inr_protected_expected']:,}  delayed Rs {p['inr_genuine_delayed_by_hold']:,}  "
          f"red holds that are scams {p['share_of_red_holds_that_are_scams']}")
    for r in ablation["rows"]:
        print(f"  ablation {r['level']:18s} scam amber+ {r['scam_amber_plus_pct']:5.1f}%  red {r['scam_red_pct']:5.1f}%  "
              f"genuine P&V {r['genuine_saw_pause_and_verify_pct']:5.2f}%  red {r['genuine_red_pct']:.3f}%")
    zero = [r for r in sensitivity["rows"] if r["voice_uptake"] == 0.0]
    for r in zero:
        print(f"  0% voice @ {r['prior_fraction']:>7s}: scam red {r['scam_red_pct']:5.1f}%  amber+ {r['scam_amber_plus_pct']:5.1f}%  "
              f"genuine P&V {r['genuine_saw_pause_and_verify_pct']:5.2f}%  red {r['genuine_red_pct']:.3f}%")
    print(f"  done in {summary['elapsed_sec']} s")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Pehchaan alert-budget simulator (assumption-driven projection)")
    ap.add_argument("--n-genuine", type=int)
    ap.add_argument("--n-scam", type=int, help="sessions per scam pattern")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--prior", type=float, help="P(scam | trigger); default from engine config (1/400)")
    ap.add_argument("--voice-uptake", type=float)
    ap.add_argument("--out", type=Path, default=RESULTS_DIR)
    ap.add_argument("--no-charts", action="store_true")
    ap.add_argument("--quick", action="store_true", help="small N smoke run")
    a = ap.parse_args(argv)
    if a.quick:
        a.n_genuine = a.n_genuine or 20000
        a.n_scam = a.n_scam or 5000
    simulate(n_genuine=a.n_genuine, n_scam=a.n_scam, seed=a.seed, prior=a.prior, voice_uptake=a.voice_uptake,
             out_dir=a.out, charts=not a.no_charts)


if __name__ == "__main__":
    main()
