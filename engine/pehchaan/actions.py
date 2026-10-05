"""Tier and claim -> actions (SPEC section 5).

Green  proceed; aggregated anonymous counters only.
Amber  "Ruko, pehle pehchaan karo": top reasons + one-tap checks that depend on
       the claim, Continue anyway (after 5 s) and Cancel.
Red    30-minute cooling-off hold. Payment NOT sent. Release early after a
       positive out-of-band check, or after analyst review (required for
       amounts >= Rs 50,000). Expiry never auto-sends. A human path always.
Report any tier, user-initiated; signed evidence pack + 1930/NCRP/Chakshu pre-fill.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from .config import Config, default_config
from .explain import _fill, copy_text

Kind = Literal["proceed", "check", "info", "continue", "cancel", "hold", "release", "report", "human"]


class Action(BaseModel):
    id: str
    kind: Kind
    label: dict[str, str]
    detail: dict[str, str] | None = None
    primary: bool = False
    enabled_after_sec: int = 0
    produces: list[str] = []      # signal codes this check can produce
    requires: str | None = None   # e.g. "analyst_review"


_P_EN = {"relative": "your family member", "bank": "your bank"}
_P_HI = {"relative": "परिवार के सदस्य", "bank": "अपने बैंक"}


def _l(en: str, hi: str, params: dict) -> dict[str, str]:
    return {"en": _fill(en, params, _P_EN), "hi": _fill(hi, params, _P_HI)}


def actions_for(
    tier: str,
    claim: str | None,
    *,
    amount_inr: float = 0,
    params: dict | None = None,
    done: set[str] | None = None,
    cfg: Config | None = None,
) -> list[Action]:
    cfg = cfg or default_config()
    params = dict(params or {})
    done = done or set()
    wait = cfg.actions.amber_min_read_sec
    out: list[Action] = []

    if tier == "green":
        return [Action(id="proceed", kind="proceed", primary=True, label={"en": "Pay now", "hi": "अभी पेमेंट करें"})]

    def checks() -> list[Action]:
        c: list[Action] = []
        if claim == "family":
            c += [
                Action(id="family_verify", kind="check", primary=True, produces=["fv_confirmed", "fv_denied", "fv_timeout"],
                       label=_l("Ask {relative} on their phone", "{relative} से उनके फ़ोन पर पूछें", params),
                       detail=_l("We send {relative} a private question. Only their own phone can answer.",
                                 "हम {relative} को एक निजी सवाल भेजेंगे। जवाब सिर्फ़ उनका अपना फ़ोन दे सकता है।", params)),
                Action(id="callback", kind="check", produces=["callback_confirmed", "callback_denied"],
                       label=_l("Call {relative}'s saved number", "{relative} के सेव किए नंबर पर कॉल करें", params)),
                Action(id="safeword", kind="check", produces=["safeword_passed", "safeword_failed"],
                       label={"en": "Ask our family safe word", "hi": "परिवार का गुप्त शब्द पूछें"}),
            ]
        elif claim == "bank":
            c += [
                Action(id="bank_registry", kind="check", primary=True, produces=["bank_active_call_1600", "bank_no_active_call"],
                       label=_l("Check with {bank}", "{bank} से जाँच करें", params),
                       detail=_l("We ask {bank} if it is calling you right now.",
                                 "हम {bank} से पूछेंगे कि क्या वो अभी आपको कॉल कर रहा है।", params)),
                Action(id="call_bank_official", kind="check",
                       label={"en": "Hang up and call the bank's official number", "hi": "फ़ोन काटें और बैंक के आधिकारिक नंबर पर कॉल करें"}),
                Action(id="bank_fact", kind="info", label=copy_text("bank_fact")),
            ]
        elif claim == "authority":
            c += [
                Action(id="authority_fact", kind="info", primary=True, label=copy_text("authority_fact"),
                       detail={"en": "If you feel scared, hang up and call 1930, the national cyber helpline.",
                               "hi": "अगर डर लग रहा है, तो फ़ोन काटें और राष्ट्रीय साइबर हेल्पलाइन 1930 पर कॉल करें।"}),
                Action(id="call_1930", kind="human", label={"en": "Call 1930 helpline", "hi": "1930 हेल्पलाइन पर कॉल करें"}),
            ]
        else:
            c += [
                Action(id="coached_warning", kind="info", label=copy_text("coached_warning")),
                Action(id="callback_known", kind="check", primary=True,
                       label={"en": "Hang up and call them back on a number you trust",
                              "hi": "फ़ोन काटें और भरोसे वाले नंबर पर वापस कॉल करें"}),
            ]
        if claim in ("family", "bank", "other", "none", None):
            c.append(Action(id="voice_check", kind="check", produces=["voice_likely_synthetic", "voice_inconclusive", "voice_no_strong_evidence"],
                            label={"en": "Check the caller's voice (optional)", "hi": "कॉल करने वाले की आवाज़ जाँचें (अगर चाहें)"},
                            detail={"en": "Put the call on speaker for 10 seconds. Audio is checked and deleted.",
                                    "hi": "कॉल को 10 सेकंड के लिए स्पीकर पर रखें। आवाज़ जाँचकर मिटा दी जाती है।"}))
        return [a for a in c if a.id not in done]

    if tier == "amber":
        out += checks()
        out += [
            Action(id="continue_anyway", kind="continue", enabled_after_sec=wait,
                   label={"en": "Continue anyway", "hi": "फिर भी आगे बढ़ें"}),
            Action(id="cancel_payment", kind="cancel", label={"en": "Cancel payment", "hi": "पेमेंट रद्द करें"}),
        ]
    elif tier == "red":
        needs_review = amount_inr >= cfg.actions.analyst_review_at_or_above_inr
        out.append(Action(id="hold", kind="hold", primary=True,
                          label=copy_text("tier_red_title"), detail=copy_text("hold_not_auto")))
        out += [a for a in checks() if a.kind == "check" and a.id != "voice_check"]
        out += [
            Action(id="release_early", kind="release",
                   requires="analyst_review" if needs_review else "positive_check",
                   label={"en": "Release early", "hi": "रोक जल्दी हटाएँ"},
                   detail=({"en": "For amounts of ₹50,000 or more, a bank officer reviews before release.",
                            "hi": "₹50,000 या उससे ज़्यादा की रकम पर, रोक हटाने से पहले बैंक अधिकारी जाँच करते हैं।"}
                           if needs_review else
                           {"en": "Possible after a successful check with the real person.",
                            "hi": "असली व्यक्ति से पुष्टि होने के बाद संभव है।"})),
            Action(id="cancel_and_report", kind="report",
                   label={"en": "Cancel and report", "hi": "रद्द करें और शिकायत करें"}),
            Action(id="bank_callback", kind="human", label=copy_text("human_path"),
                   detail={"en": "A person from the bank's safety desk calls you back.",
                           "hi": "बैंक की सुरक्षा टीम से कोई व्यक्ति आपको वापस कॉल करेगा।"}),
        ]
    if tier != "red":
        out.append(Action(id="report", kind="report", label={"en": "Report this", "hi": "इसकी शिकायत करें"}))
    return out
