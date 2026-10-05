"""Signal codes and families (SPEC section 3).

Six independent families. Every signal belongs to exactly one family; the
fusion engine sums ln-LR inside a family and clips the family total to its cap
(SPEC section 4), so correlated signals inside a family cannot run away.
"""
from __future__ import annotations

FAMILIES: dict[str, str] = {
    "C": "Claim",
    "K": "Call context",
    "P": "Payment context",
    "V": "Voice provenance",
    "S": "Script cues",
    "O": "Out-of-band verification",
}

FAMILY_NAMES_HI: dict[str, str] = {
    "C": "दावा",
    "K": "कॉल की जानकारी",
    "P": "पेमेंट की जानकारी",
    "V": "आवाज़ की जाँच",
    "S": "बातचीत के संकेत",
    "O": "दूसरे रास्ते से पुष्टि",
}

SIGNAL_FAMILY: dict[str, str] = {
    # C: Claim (one-tap answer to "Who asked you to make this payment?")
    "claim_family": "C",
    "claim_bank": "C",
    "claim_authority": "C",
    "claim_other": "C",
    "claim_none": "C",
    # K: Call context (metadata only, never audio)
    "caller_unknown": "K",
    "caller_international": "K",
    "caller_voip_unknown": "K",
    "bank_claim_not_1600": "K",
    "fri_medium": "K",
    "fri_high": "K",
    "fri_very_high": "K",
    "call_ongoing_long": "K",
    # P: Payment context
    "payee_new": "P",
    "amount_gt_p95": "P",
    "amount_gt_p99": "P",
    "payee_flagged_medium": "P",
    "payee_flagged_high": "P",
    "payee_name_mismatch": "P",
    "burst_new_payees": "P",
    # V: Voice provenance (opt-in)
    "voice_likely_synthetic": "V",
    "voice_inconclusive": "V",
    "voice_no_strong_evidence": "V",
    "watermark_detected": "V",
    # S: Script cues (opt-in; ASR on the same capture or a 3-question tap checklist)
    "cue_secrecy": "S",
    "cue_urgency": "S",
    "cue_otp_pin": "S",
    "cue_arrest_threat": "S",
    "cue_remote_app": "S",
    "cue_refund_verification": "S",
    # O: Out-of-band verification (decisive)
    "fv_denied": "O",
    "fv_confirmed": "O",
    "fv_timeout": "O",
    "callback_denied": "O",
    "callback_confirmed": "O",
    "safeword_failed": "O",
    "safeword_passed": "O",
    "bank_no_active_call": "O",
    "bank_active_call_1600": "O",
}

ALL_SIGNALS: tuple[str, ...] = tuple(SIGNAL_FAMILY)

CLAIMS: dict[str, str] = {
    "family": "claim_family",
    "bank": "claim_bank",
    "authority": "claim_authority",
    "other": "claim_other",
    "none": "claim_none",
}

# Mutually exclusive groups. If a caller sends more than one member, the first
# one in the tuple wins (ordered most-severe first) and the rest are dropped
# with a note. This keeps "fri_high + fri_very_high" from double counting.
EXCLUSIVE_GROUPS: dict[str, tuple[str, ...]] = {
    "claim": ("claim_authority", "claim_bank", "claim_family", "claim_other", "claim_none"),
    "fri": ("fri_very_high", "fri_high", "fri_medium"),
    "amount": ("amount_gt_p99", "amount_gt_p95"),
    "payee_flag": ("payee_flagged_high", "payee_flagged_medium"),
    "voice_band": ("voice_likely_synthetic", "voice_inconclusive", "voice_no_strong_evidence"),
    "family_verify": ("fv_denied", "fv_confirmed", "fv_timeout"),
    "callback": ("callback_denied", "callback_confirmed"),
    "safeword": ("safeword_failed", "safeword_passed"),
    "bank_registry": ("bank_no_active_call", "bank_active_call_1600"),
}

VOICE_BANDS: tuple[str, ...] = ("likely_synthetic", "inconclusive", "no_strong_evidence")
VOICE_BAND_SIGNAL: dict[str, str] = {b: f"voice_{b}" for b in VOICE_BANDS}

# G1(b): decisive negatives from family O
DECISIVE_NEGATIVE: frozenset[str] = frozenset(
    {"fv_denied", "callback_denied", "bank_no_active_call", "safeword_failed"}
)
# G4: decisive positives
DECISIVE_POSITIVE: frozenset[str] = frozenset({"fv_confirmed", "callback_confirmed"})


def family_of(code: str) -> str:
    try:
        return SIGNAL_FAMILY[code]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(f"unknown signal code: {code!r}") from exc


def resolve_exclusive(codes: list[str]) -> tuple[list[str], list[dict]]:
    """Dedupe and resolve exclusive groups. Returns (kept, dropped_notes)."""
    seen: list[str] = []
    for c in codes:
        if c not in SIGNAL_FAMILY:
            raise ValueError(f"unknown signal code: {c!r}")
        if c not in seen:
            seen.append(c)
    dropped: list[dict] = []
    keep = set(seen)
    for group, members in EXCLUSIVE_GROUPS.items():
        present = [m for m in members if m in keep]
        if len(present) > 1:
            winner = present[0]
            for loser in present[1:]:
                keep.discard(loser)
                dropped.append({"code": loser, "why": f"exclusive group '{group}': kept {winner}"})
    return [c for c in seen if c in keep], dropped
