"""Plain-language reasons in English and Hindi (Devanagari).

Rules (G6): never accuse. We never say "this is a scam", "fraud" or "fake
voice detected". We say what we noticed and what to check. Sentences are short
and concrete, written for a 60-year-old reading under pressure.

Templates take optional parameters, filled by the risk API from the case:
  {payee} {relative} {caller} {country} {bank} {minutes} {amount}
Missing parameters fall back to neutral words ("this person", "your bank").
"""
from __future__ import annotations

import re
from string import Formatter

# code -> (english, hindi)
REASON_TEXT: dict[str, tuple[str, str]] = {
    # ---- C: Claim
    "claim_family": (
        "You told us a family member asked for this money.",
        "आपने बताया कि परिवार के किसी सदस्य ने ये पैसे माँगे हैं।",
    ),
    "claim_bank": (
        "You told us someone from a bank asked for this payment. A real bank never asks you to move money to keep it safe.",
        "आपने बताया कि बैंक की ओर से किसी ने ये पेमेंट करने को कहा। असली बैंक कभी पैसे बचाने के लिए उन्हें कहीं और भेजने को नहीं कहता।",
    ),
    "claim_authority": (
        "You told us police or a government officer asked for this payment. Police and officers never ask for money on a call.",
        "आपने बताया कि पुलिस या किसी सरकारी अफ़सर ने ये पेमेंट माँगा है। पुलिस या अफ़सर कभी फ़ोन पर पैसे नहीं माँगते।",
    ),
    "claim_other": (
        "You told us someone else asked for this payment.",
        "आपने बताया कि किसी और ने ये पेमेंट करने को कहा।",
    ),
    "claim_none": (
        "You told us no one asked you to make this payment.",
        "आपने बताया कि किसी ने ये पेमेंट करने को नहीं कहा।",
    ),
    # ---- K: Call context
    "caller_unknown": (
        "You are on a call with {caller}. This number is not saved in your phone.",
        "आप {caller} से बात कर रहे हैं। ये नंबर आपके फ़ोन में सेव नहीं है।",
    ),
    "caller_international": (
        "The call is coming from outside India ({country}).",
        "ये कॉल भारत के बाहर ({country}) से आ रही है।",
    ),
    "caller_voip_unknown": (
        "This is an internet call (like WhatsApp) from a number you have not saved.",
        "ये इंटरनेट कॉल (जैसे WhatsApp) है, ऐसे नंबर से जो आपके फ़ोन में सेव नहीं है।",
    ),
    "bank_claim_not_1600": (
        "Real bank calls now come from numbers starting with 1600. This call is from an ordinary mobile number.",
        "असली बैंक की कॉल अब 1600 से शुरू होने वाले नंबर से आती है। ये कॉल एक आम मोबाइल नंबर से है।",
    ),
    "fri_medium": (
        "The telecom department's risk list marks this caller's number as medium risk.",
        "दूरसंचार विभाग की जोखिम सूची में इस नंबर को मध्यम जोखिम वाला बताया गया है।",
    ),
    "fri_high": (
        "The telecom department's risk list marks this caller's number as high risk.",
        "दूरसंचार विभाग की जोखिम सूची में इस नंबर को ज़्यादा जोखिम वाला बताया गया है।",
    ),
    "fri_very_high": (
        "The telecom department's risk list marks this caller's number as very high risk.",
        "दूरसंचार विभाग की जोखिम सूची में इस नंबर को बहुत ज़्यादा जोखिम वाला बताया गया है।",
    ),
    "call_ongoing_long": (
        "This call has gone on for more than {minutes} minutes. When a long call ends in a request for money, take extra care.",
        "ये कॉल {minutes} मिनट से ज़्यादा चल रही है। लंबी कॉल के बाद पैसे माँगे जाएँ, तो ज़्यादा सावधानी रखें।",
    ),
    # ---- P: Payment context
    "payee_new": (
        "You have never paid {payee} before.",
        "आपने {payee} को पहले कभी पैसे नहीं भेजे हैं।",
    ),
    "amount_gt_p95": (
        "{amount} is more than you usually send.",
        "{amount} आपकी आम रकम से ज़्यादा है।",
    ),
    "amount_gt_p99": (
        "{amount} is much more than you usually send.",
        "{amount} आपकी आम रकम से बहुत ज़्यादा है।",
    ),
    "payee_flagged_medium": (
        "Other people have raised concerns about the account receiving this money.",
        "पैसे पाने वाले इस खाते के बारे में दूसरे लोगों ने चिंता जताई है।",
    ),
    "payee_flagged_high": (
        "The account receiving this money is on a national list of accounts reported by other people.",
        "पैसे पाने वाला ये खाता उस राष्ट्रीय सूची में है, जिसकी शिकायत दूसरे लोगों ने की है।",
    ),
    "payee_name_mismatch": (
        "The account name ‘{payee}’ does not match {relative}.",
        "खाते का नाम ‘{payee}’ {relative} के नाम से मेल नहीं खाता।",
    ),
    "burst_new_payees": (
        "You have started payments to several new people in the last 30 minutes.",
        "पिछले 30 मिनट में आपने कई नए लोगों को पेमेंट शुरू किए हैं।",
    ),
    # ---- V: Voice provenance
    "voice_likely_synthetic": (
        "Our voice check found signs that this voice may be computer-made. The check can be wrong, so please confirm another way.",
        "आवाज़ की जाँच में कुछ संकेत मिले कि ये आवाज़ कंप्यूटर से बनी हो सकती है। जाँच गलत भी हो सकती है, इसलिए किसी और तरीके से पक्का करें।",
    ),
    "voice_inconclusive": (
        "The voice check could not decide. The line may be noisy or the clip too short.",
        "आवाज़ की जाँच से कुछ तय नहीं हो पाया। लाइन में शोर हो सकता है या रिकॉर्डिंग बहुत छोटी थी।",
    ),
    "voice_no_strong_evidence": (
        "The voice check found no strong signs of a computer-made voice. That alone does not prove who is speaking.",
        "आवाज़ की जाँच में कंप्यूटर से बनी आवाज़ के पक्के संकेत नहीं मिले। पर सिर्फ़ इससे ये पक्का नहीं होता कि बात कौन कर रहा है।",
    ),
    "watermark_detected": (
        "The audio carries a hidden marker that some AI voice tools add.",
        "इस आवाज़ में एक छिपा निशान मिला है, जो कुछ AI आवाज़ वाले टूल लगाते हैं।",
    ),
    # ---- S: Script cues
    "cue_secrecy": (
        "You were asked to keep this payment a secret from your family.",
        "आपसे कहा गया कि ये पेमेंट परिवार से छिपाकर रखें।",
    ),
    "cue_urgency": (
        "You were told to pay right now, with no time to check.",
        "आपसे कहा गया कि अभी तुरंत पैसे भेजें, जाँचने का समय नहीं दिया गया।",
    ),
    "cue_otp_pin": (
        "You were asked for an OTP or PIN. No genuine caller ever needs these.",
        "आपसे OTP या PIN माँगा गया। कोई भी असली कॉल करने वाला ये कभी नहीं माँगता।",
    ),
    "cue_arrest_threat": (
        "You were told someone could be arrested. There is no ‘digital arrest’ in Indian law.",
        "आपसे कहा गया कि किसी को गिरफ़्तार किया जा सकता है। भारतीय कानून में ‘डिजिटल अरेस्ट’ जैसा कुछ नहीं होता।",
    ),
    "cue_remote_app": (
        "You were asked to install an app or share your screen.",
        "आपसे कोई ऐप डाउनलोड करने या स्क्रीन शेयर करने को कहा गया।",
    ),
    "cue_refund_verification": (
        "You were told to pay to ‘verify’ your account or to get a refund.",
        "आपसे कहा गया कि खाता ‘वेरिफ़ाई’ करने या रिफ़ंड पाने के लिए पैसे भेजें।",
    ),
    # ---- O: Out-of-band verification
    "fv_denied": (
        "{relative} said on {their} own phone that {they} did not ask for this money.",
        "{relative} ने अपने फ़ोन पर बताया कि उन्होंने ये पैसे नहीं माँगे।",
    ),
    "fv_confirmed": (
        "{relative} confirmed on {their} own phone that it really is {them}.",
        "{relative} ने अपने फ़ोन पर पक्का किया कि ये सच में वही हैं।",
    ),
    "fv_timeout": (
        "{relative} has not answered on {their} phone yet.",
        "{relative} ने अभी तक अपने फ़ोन पर जवाब नहीं दिया।",
    ),
    "callback_denied": (
        "When you called {relative}'s saved number, {they} said {they} did not ask for money.",
        "आपने {relative} के सेव किए नंबर पर कॉल किया, तो उन्होंने कहा कि उन्होंने पैसे नहीं माँगे।",
    ),
    "callback_confirmed": (
        "You called {relative}'s saved number and {they} confirmed the request.",
        "आपने {relative} के सेव किए नंबर पर कॉल किया और उन्होंने बात पक्की की।",
    ),
    "safeword_failed": (
        "The caller did not know your family safe word.",
        "कॉल करने वाले को आपके परिवार का गुप्त शब्द नहीं पता था।",
    ),
    "safeword_passed": (
        "The caller knew your family safe word.",
        "कॉल करने वाले को आपके परिवार का गुप्त शब्द पता था।",
    ),
    "bank_no_active_call": (
        "{bank} is not calling you right now.",
        "{bank} अभी आपको कॉल नहीं कर रहा है।",
    ),
    "bank_active_call_1600": (
        "{bank} confirms it is calling you right now from its official 1600 number.",
        "{bank} ने पक्का किया है कि वो अभी अपने आधिकारिक 1600 नंबर से आपको कॉल कर रहा है।",
    ),
}

DEFAULTS_EN = {
    "payee": "this person", "relative": "Your family member", "caller": "this caller",
    "country": "an international number", "bank": "Your bank", "minutes": "15", "amount": "This amount",
    "their": "their", "they": "they", "them": "them",
}
DEFAULTS_HI = {
    "payee": "इस व्यक्ति", "relative": "आपके परिवार के सदस्य", "caller": "इस नंबर",
    "country": "अंतरराष्ट्रीय नंबर", "bank": "आपका बैंक", "minutes": "15", "amount": "ये रकम",
}

# Fixed UI copy the API returns with a decision (so the app, deck and tests share one source).
COPY: dict[str, tuple[str, str]] = {
    "tier_green_title": ("You're good to go", "आप पेमेंट कर सकते हैं"),
    "tier_green_body": ("Nothing here needs a second look.", "यहाँ दोबारा जाँचने जैसा कुछ नहीं है।"),
    "tier_amber_title": ("Ruko, pehle pehchaan karo", "रुको, पहले पहचान करो"),
    "tier_amber_body": ("Before you pay, take one minute to check who is asking.", "पैसे भेजने से पहले, एक मिनट लेकर देख लें कि पैसे कौन माँग रहा है।"),
    "tier_red_title": ("We have paused this payment for 30 minutes", "हमने ये पेमेंट 30 मिनट के लिए रोक दिया है"),
    "tier_red_body": ("Your money has not been sent. Nothing leaves your account while it is on hold.", "आपके पैसे नहीं भेजे गए हैं। रोक के दौरान आपके खाते से कुछ नहीं जाएगा।"),
    "who_asked": ("Who asked you to make this payment?", "ये पेमेंट करने को आपसे किसने कहा?"),
    "coached_warning": (
        "If someone on the call is telling you what to tap, that is a warning sign. It is okay to hang up.",
        "अगर कॉल पर कोई आपको बता रहा है कि क्या दबाना है, तो ये खतरे का संकेत है। फ़ोन काट देना बिल्कुल ठीक है।",
    ),
    "authority_fact": (
        "There is no ‘digital arrest’ in Indian law. Police never ask for money on a call.",
        "भारतीय कानून में ‘डिजिटल अरेस्ट’ नाम की कोई चीज़ नहीं है। पुलिस कभी फ़ोन पर पैसे नहीं माँगती।",
    ),
    "bank_fact": (
        "Real bank calls come from numbers starting with 1600. Your bank will never ask you to move money to a ‘safe account’.",
        "असली बैंक की कॉल 1600 से शुरू होने वाले नंबर से आती है। आपका बैंक कभी ‘सुरक्षित खाते’ में पैसे भेजने को नहीं कहेगा।",
    ),
    "hold_not_auto": (
        "When the 30 minutes end, we will not send the money on our own. You decide.",
        "30 मिनट पूरे होने पर भी हम अपने-आप पैसे नहीं भेजेंगे। फ़ैसला आपका होगा।",
    ),
    "human_path": ("Talk to a person at your bank", "अपने बैंक के किसी व्यक्ति से बात करें"),
}

# Words that must never appear in user-facing text (G6). Tested in tests/.
FORBIDDEN_USER_TEXT = [
    r"\bscam(s|mer|mers)?\b", r"\bfake\b", r"\bfraud(ster|sters)?\b", r"\bcriminal\b", r"\bliar\b",
    "धोखा", "ठग", "फ़र्ज़ी", "फर्जी", "नकली", "अपराधी",
]


class _SafeDict(dict):
    def __missing__(self, key):  # pragma: no cover - only for unknown keys
        return "{" + key + "}"


def _fill(template: str, params: dict, defaults: dict, suffix: str = "") -> str:
    fields = {f for _, f, _, _ in Formatter().parse(template) if f}
    values = _SafeDict()
    for f in fields:
        v = params.get(f + suffix) if suffix else None
        if v in (None, ""):
            v = params.get(f)
        values[f] = str(v) if v not in (None, "") else defaults.get(f, "")
    out = template.format_map(values)
    # Capitalise a lowercase default at sentence start (e.g. "this person").
    return out[:1].upper() + out[1:] if out else out


def reason_text(code: str, params: dict | None = None) -> dict[str, str]:
    """Params may carry Hindi-specific values with a `_hi` suffix (e.g. relative_hi)."""
    en, hi = REASON_TEXT[code]
    params = params or {}
    return {"en": _fill(en, params, DEFAULTS_EN), "hi": _fill(hi, params, DEFAULTS_HI, "_hi")}


def copy_text(key: str) -> dict[str, str]:
    en, hi = COPY[key]
    return {"en": en, "hi": hi}


def violates_g6(text: str) -> list[str]:
    return [pat for pat in FORBIDDEN_USER_TEXT if re.search(pat, text, flags=re.IGNORECASE)]


def format_inr(amount: float | int | None) -> str:
    """Indian digit grouping: 150000 -> ₹1,50,000."""
    if amount is None:
        return ""
    n = int(round(amount))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return ("-" if n < 0 else "") + "₹" + s
