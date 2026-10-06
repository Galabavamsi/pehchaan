"""Explainable log-odds fusion with per-family clipping, then guardrails G1-G7 (SPEC v0.2).

    log_odds = logit(prior) + sum_f clip(sum_{s in f} ln LR_s, -ln cap_f, +ln cap_f)
    p        = sigmoid(log_odds)

Guardrails (hard rules after scoring, SPEC section 4), in the order applied:
  G3  Quality gate: speech < 4 s or SNR < 10 dB -> voice_inconclusive.
  G7  Decisive floor: fv_denied or bank_no_active_call -> Red regardless of p.
  G5  Trusted bypass: payee paid >= 3 times and amount <= 1.5x usual -> Green.
  G4  fv_confirmed / callback_confirmed / bank_active_call_1600 -> Green (Amber if
      payee_flagged_high). With a conflicting user-reported negative: at least Amber.
  G1  Red (p >= theta_red) needs >= 2 families each with LR >= 3, where trigger-implied
      evidence (payee_new, amount_gt_*) does not count and V never counts.
  G2  Strict: if removing V would drop p below theta_red, cap at Amber.
  G6  No accusation in user text (enforced in explain.py + tests).
"""
from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel

from .config import Config, default_config
from .explain import copy_text, reason_text
from .signals import (
    DECISIVE_NEGATIVE,
    DECISIVE_POSITIVE,
    USER_REPORTED_NEGATIVE,
    FAMILIES,
    FAMILY_NAMES_HI,
    SIGNAL_FAMILY,
    resolve_exclusive,
)

Tier = Literal["green", "amber", "red"]
TIER_RANK = {"green": 0, "amber": 1, "red": 2}


def logit(p: float) -> float:
    return math.log(p / (1 - p))


def sigmoid(x: float) -> float:
    if x >= 0:
        return 1 / (1 + math.exp(-x))
    e = math.exp(x)
    return e / (1 + e)


class VoiceQuality(BaseModel):
    speech_sec: float
    snr_db: float


class TrustedPayee(BaseModel):
    prior_payments: int = 0
    usual_amount_inr: float | None = None
    amount_inr: float | None = None


class Reason(BaseModel):
    code: str
    family: str
    family_name: str
    family_name_hi: str
    lr: float
    ln_lr: float              # raw ln LR of this signal
    contribution: float       # ln LR after family clipping (sums to the family total)
    direction: Literal["raises", "lowers", "neutral"]
    text: dict[str, str]      # {"en": ..., "hi": ...}
    basis: str


class FamilyScore(BaseModel):
    family: str
    name: str
    raw_ln_lr: float
    ln_lr: float              # after clipping
    lr: float
    capped: bool
    signals: list[str]


class GuardrailNote(BaseModel):
    id: str
    name: str
    effect: str
    detail: str


class Assessment(BaseModel):
    tier: Tier
    raw_tier: Tier
    p: float
    log_odds: float
    prior: float
    prior_log_odds: float
    thresholds: dict[str, float]
    families: dict[str, FamilyScore]
    reasons: list[Reason]
    guardrails_applied: list[GuardrailNote]
    signals: list[str]
    dropped: list[dict]
    qualifying_families: list[str]
    config_version: str

    def top_reasons(self, n: int = 3, tier: Tier | None = None) -> list[Reason]:
        """Reasons to show the user: the strongest risk-raising ones, or for a
        Green-after-check result the strongest reassuring ones."""
        tier = tier or self.tier
        if tier == "green":
            pool = [r for r in self.reasons if r.direction == "lowers"]
            pool.sort(key=lambda r: r.contribution)
        else:
            pool = [r for r in self.reasons if r.direction == "raises" and not r.code.startswith("claim_")]
            pool.sort(key=lambda r: -r.contribution)
        return pool[:n]


_GUARDRAIL_NAMES = {
    "G1": "No single weak signal",
    "G2": "Voice is supporting evidence",
    "G3": "Audio quality gate",
    "G4": "Decisive positive check",
    "G5": "Trusted payee bypass",
    "G6": "No accusation",
    "G7": "Decisive floor",
}


def _tier_of(p: float, cfg: Config) -> Tier:
    if p >= cfg.tiers.red_at_or_above:
        return "red"
    if p >= cfg.tiers.green_below:
        return "amber"
    return "green"


def _note(gid: str, effect: str, detail: str) -> GuardrailNote:
    return GuardrailNote(id=gid, name=_GUARDRAIL_NAMES[gid], effect=effect, detail=detail)


def trusted_bypass_applies(trusted: TrustedPayee | None, cfg: Config) -> bool:
    if trusted is None or trusted.prior_payments < cfg.guardrails.g5_min_prior_payments:
        return False
    if trusted.usual_amount_inr is None or trusted.amount_inr is None:
        return False
    return trusted.amount_inr <= cfg.guardrails.g5_max_amount_ratio * trusted.usual_amount_inr


def assess(
    signals: list[str],
    *,
    prior: float | None = None,
    voice_quality: VoiceQuality | dict | None = None,
    trusted: TrustedPayee | dict | None = None,
    params: dict | None = None,
    cfg: Config | None = None,
) -> Assessment:
    """Score one decision point.

    signals        signal codes present (see signals.py)
    prior          override pi0 (default from config)
    voice_quality  {speech_sec, snr_db} of the voice capture, for G3
    trusted        payee history for G5
    params         template values for reason text (payee, relative, caller, ...)
    """
    cfg = cfg or default_config()
    prior = cfg.prior.value if prior is None else prior
    params = params or {}
    if isinstance(voice_quality, dict):
        voice_quality = VoiceQuality(**voice_quality)
    if isinstance(trusted, dict):
        trusted = TrustedPayee(**trusted)

    notes: list[GuardrailNote] = []
    kept, dropped = resolve_exclusive(list(signals))

    # ---- G3: quality gate on voice --------------------------------------
    voice_codes = [c for c in kept if SIGNAL_FAMILY[c] == "V"]
    if voice_codes and voice_quality is not None:
        g = cfg.guardrails
        if voice_quality.speech_sec < g.g3_min_speech_sec or voice_quality.snr_db < g.g3_min_snr_db:
            changed = [c for c in voice_codes if c != "voice_inconclusive"]
            if changed:
                kept = [c for c in kept if SIGNAL_FAMILY[c] != "V"] + ["voice_inconclusive"]
                dropped += [{"code": c, "why": "G3 quality gate"} for c in changed]
                notes.append(_note(
                    "G3", "voice -> inconclusive",
                    f"speech {voice_quality.speech_sec:.1f} s (min {g.g3_min_speech_sec}), "
                    f"SNR {voice_quality.snr_db:.1f} dB (min {g.g3_min_snr_db}); low quality is never read as 'real'",
                ))

    # ---- per-family sums and clipping -----------------------------------
    by_family: dict[str, list[str]] = {f: [] for f in FAMILIES}
    for c in kept:
        by_family[SIGNAL_FAMILY[c]].append(c)

    fam_scores: dict[str, FamilyScore] = {}
    reasons: list[Reason] = []
    total = 0.0
    for f, codes in by_family.items():
        raw = sum(cfg.ln_lr(c) for c in codes)
        cap = cfg.ln_cap(f)
        clipped = max(-cap, min(cap, raw))
        scale = (clipped / raw) if raw != 0 else 1.0
        fam_scores[f] = FamilyScore(
            family=f, name=FAMILIES[f], raw_ln_lr=raw, ln_lr=clipped, lr=math.exp(clipped),
            capped=abs(raw) > cap + 1e-12, signals=codes,
        )
        total += clipped
        for c in codes:
            ln = cfg.ln_lr(c)
            contrib = ln * scale
            reasons.append(Reason(
                code=c, family=f, family_name=FAMILIES[f], family_name_hi=FAMILY_NAMES_HI[f],
                lr=cfg.signals[c].lr, ln_lr=ln, contribution=contrib,
                direction="raises" if contrib > 1e-9 else ("lowers" if contrib < -1e-9 else "neutral"),
                # shadow-mode detector bands: the payer was told the score is saved, not a verdict (G6)
                text=copy_text("voice_shadow_result") if cfg.signals[c].basis == "shadow" else reason_text(c, params),
                basis=cfg.signals[c].basis,
            ))
    reasons.sort(key=lambda r: -abs(r.contribution))

    prior_lo = logit(prior)
    log_odds = prior_lo + total
    p = sigmoid(log_odds)
    raw_tier = _tier_of(p, cfg)
    tier: Tier = raw_tier

    g = cfg.guardrails
    min_ln = math.log(g.g1_min_family_lr)
    # G1(a) corroboration: per-family ln-LR excluding trigger-implied evidence (SPEC v0.2), clipped to the cap.
    trig = set(g.g1_trigger_implied)
    g1_ln: dict[str, float] = {}
    for f, codes in by_family.items():
        cap = cfg.ln_cap(f)
        g1_ln[f] = max(-cap, min(cap, sum(cfg.ln_lr(c) for c in codes if c not in trig)))
    qualifying = [f for f in FAMILIES if g1_ln[f] >= min_ln - 1e-12]
    qualifying_counted = [f for f in qualifying if f not in g.g1_excluded_families]
    kept_set = set(kept)
    decisive_neg = sorted(kept_set & DECISIVE_NEGATIVE)
    user_neg = sorted(kept_set & USER_REPORTED_NEGATIVE)
    decisive_pos = sorted(kept_set & DECISIVE_POSITIVE)
    theta = cfg.tiers.red_at_or_above

    # ---- G7: decisive floor -------------------------------------------------
    if decisive_neg:
        if decisive_pos:
            notes.append(_note("G4", "not applied",
                               f"{', '.join(decisive_pos)} conflicts with decisive {', '.join(decisive_neg)}"))
        notes.append(_note(
            "G7", f"{raw_tier} -> red" if raw_tier != "red" else "red (floor)",
            f"{', '.join(decisive_neg)} comes from outside the customer's own taps; held regardless of p",
        ))
        tier = "red"
    # ---- G5: trusted payee bypass -------------------------------------------
    elif trusted_bypass_applies(trusted, cfg):
        tier = "green"
        notes.append(_note(
            "G5", f"{raw_tier} -> green",
            f"payee paid {trusted.prior_payments} times before; amount within "
            f"{g.g5_max_amount_ratio}x of usual",
        ))
    # ---- G4: decisive positive ----------------------------------------------
    elif decisive_pos and not user_neg:
        flagged = g.g4_flag_exception in kept
        new_tier: Tier = "amber" if flagged else "green"
        if new_tier != tier:
            notes.append(_note(
                "G4", f"{tier} -> {new_tier}",
                f"{', '.join(decisive_pos)} from the real person's or bank's own channel"
                + (f"; but {g.g4_flag_exception} keeps it at Amber" if flagged else ""),
            ))
        elif flagged:
            notes.append(_note("G4", "kept amber", f"{g.g4_flag_exception} blocks a Green override"))
        tier = new_tier
    else:
        if decisive_pos and user_neg:
            if tier == "green":
                tier = "amber"
            notes.append(_note(
                "G4", "not applied",
                f"conflicting checks ({', '.join(decisive_pos)} vs user-reported {', '.join(user_neg)}); at least Amber",
            ))
        # ---- G1 / G2: corroboration for Red ---------------------------------
        if tier == "red" and len(qualifying_counted) < g.g1_min_families:
            tier = "amber"
            notes.append(_note(
                "G1", "red -> amber",
                f"only {len(qualifying_counted)} independent famil{'y' if len(qualifying_counted) == 1 else 'ies'} "
                f"with LR >= {g.g1_min_family_lr:g} ({', '.join(qualifying_counted) or 'none'}; trigger-implied "
                f"new-payee/amount evidence not counted) and no decisive out-of-band negative",
            ))
            v_qualifies = any(f in g.g1_excluded_families for f in qualifying)
            if v_qualifies and len(qualifying) >= g.g1_min_families:
                notes.append(_note(
                    "G2", "voice not counted",
                    "the voice check would have been the second family; voice alone cannot move a payment to a hold",
                ))
        elif tier == "red" and g.g2_strict and abs(fam_scores["V"].ln_lr) > 1e-12:
            p_no_v = sigmoid(log_odds - fam_scores["V"].ln_lr)
            if p_no_v < theta:
                tier = "amber"
                notes.append(_note(
                    "G2", "red -> amber (strict)",
                    f"without the voice check p would be {p_no_v:.2f} < {theta:g}; voice cannot be the reason for a hold",
                ))

    return Assessment(
        tier=tier, raw_tier=raw_tier, p=p, log_odds=log_odds, prior=prior, prior_log_odds=prior_lo,
        thresholds={
            "green_below": cfg.tiers.green_below,
            "red_at_or_above": cfg.tiers.red_at_or_above,
            "green_below_log_odds": logit(cfg.tiers.green_below),
            "red_at_or_above_log_odds": logit(cfg.tiers.red_at_or_above),
        },
        families=fam_scores, reasons=reasons, guardrails_applied=notes, signals=kept, dropped=dropped,
        qualifying_families=qualifying_counted, config_version=cfg.version,
    )


def should_ask_claim(a: Assessment, cfg: Config | None = None) -> bool:
    """Ask 'who asked you to pay?' unless context alone is clearly benign."""
    cfg = cfg or default_config()
    if any(n.id == "G5" for n in a.guardrails_applied):
        return False
    return a.tier != "green" or a.p >= cfg.tiers.ask_claim_at_or_above
