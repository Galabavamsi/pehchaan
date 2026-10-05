"""Case service: turns raw payment/call context into Pehchaan signals (via the
mock adapters), runs the fusion engine at each stage, and keeps the case,
its hash-chained events and the cooling-off hold."""
from __future__ import annotations

import json
import os
import secrets
import time
from datetime import timedelta
from pathlib import Path

from pehchaan import assess, default_config, evaluate_trigger, should_ask_claim
from pehchaan.actions import actions_for
from pehchaan.evidence import (
    Signer,
    append_event,
    build_evidence_pack,
    ist_iso,
    now_ist,
    verify_signature,
)
from pehchaan.explain import copy_text, format_inr
from pehchaan.fusion import TrustedPayee
from pehchaan.trigger import TriggerInput

from .adapters import (
    country_of,
    is_1600_series,
    is_international,
    mock_bank_registry,
    mock_contacts,
    mock_fri,
    mock_i4c,
    mock_payer_history,
    names_match,
    normalise_number,
    pretty_number,
)
from .db import Store

CFG = default_config()
CLAIM_CODES = {"family", "bank", "authority", "other", "none"}
CHECK_SIGNALS = {
    "family_verify": {"confirmed": "fv_confirmed", "denied": "fv_denied", "timeout": "fv_timeout"},
    "callback": {"confirmed": "callback_confirmed", "denied": "callback_denied"},
    "safeword": {"passed": "safeword_passed", "failed": "safeword_failed"},
    "bank_registry": {"no_active_call": "bank_no_active_call", "active_call_1600": "bank_active_call_1600"},
}
ALLOWED_CUES = {"cue_secrecy", "cue_urgency", "cue_otp_pin", "cue_arrest_threat", "cue_remote_app",
                "cue_refund_verification"}


PRONOUNS = {"he": {"their": "his", "they": "he", "them": "him"},
            "she": {"their": "her", "they": "she", "them": "her"}}


class CaseError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status
        self.msg = msg


class CaseService:
    def __init__(self, store: Store, key_path: str | Path | None = None):
        self.s = store
        self.contacts = mock_contacts(store)
        self.fri = mock_fri(store)
        self.i4c = mock_i4c(store)
        self.bank = mock_bank_registry(store)
        self.history = mock_payer_history(store)
        self.signer = Signer.load_or_create(key_path) if key_path else Signer.ephemeral()
        self._clock_offset = timedelta(0)
        self._base_offset = timedelta(0)
        demo = os.environ.get("PEHCHAAN_DEMO_TIME", "").strip()  # e.g. "10:40": run the demo clock at that IST time
        if demo:
            hh, mm = (int(x) for x in demo.split(":"))
            real = now_ist()
            self._base_offset = real.replace(hour=hh, minute=mm, second=0, microsecond=0) - real

    # ------------------------------------------------------------------ util
    def now(self):
        return now_ist() + self._base_offset + self._clock_offset

    def ts(self) -> str:
        return ist_iso(self.now())

    def _event(self, case: dict, etype: str, actor: str, data: dict) -> dict:
        chain = self.s.events(case["case_id"])
        ev = append_event(chain, etype, actor, data, ts=self.ts())
        self.s.put_event(case["case_id"], ev)
        return ev

    def _new_case_id(self) -> str:
        n = self.s.next_counter("case")
        return f"PCH-{self.now():%y%m%d}-{n:04d}"

    # ------------------------------------------------------------- context
    def _context(self, payer: dict, payment: dict, call: dict | None) -> dict:
        call = call or {}
        uid = payer["id"]
        number = normalise_number(call.get("number"))
        state = call.get("state", "active" if number else "none")
        channel = call.get("channel", "pstn")
        hist = self.history.payee(uid, payment["payee_vpa"])
        amount = float(payment["amount_inr"])
        p95, p99 = payer.get("amount_p95"), payer.get("amount_p99")
        trig = evaluate_trigger(TriggerInput(
            call_active=state == "active",
            call_ended_sec_ago=call.get("ended_sec_ago") if state == "ended" else None,
            payee_new=hist is None, amount_inr=amount, amount_p95_inr=p95,
        ), CFG)
        sig: list[str] = []
        in_contacts = call.get("in_contacts")
        if in_contacts is None and number:
            in_contacts = self.contacts.match(uid, number)
        if number and not in_contacts:
            sig.append("caller_unknown")
            if channel in ("whatsapp", "voip"):
                sig.append("caller_voip_unknown")
        if number and is_international(number):
            sig.append("caller_international")
        fri = self.fri.lookup(number) if number else None
        if fri:
            sig.append(f"fri_{fri}")
        if (call.get("duration_sec") or 0) > CFG.trigger.long_call_min * 60:
            sig.append("call_ongoing_long")
        if hist is None:
            sig.append("payee_new")
        if p99 is not None and amount > p99:
            sig.append("amount_gt_p99")
        elif p95 is not None and amount > p95:
            sig.append("amount_gt_p95")
        flag = self.i4c.lookup(payment["payee_vpa"])
        if flag:
            sig.append(f"payee_flagged_{flag}")
        recent_new = payer.get("recent_new_payees_30m", 0) + (1 if hist is None else 0)
        if recent_new >= CFG.trigger.burst_min_new_payees:
            sig.append("burst_new_payees")
        cc = country_of(number) if number else None
        country_en, country_hi = (cc[1].split("|") if cc else ("", ""))
        minutes = int((call.get("duration_sec") or 0) // 60)
        params = {
            "payee": payment.get("payee_name") or payment["payee_vpa"],
            "caller": pretty_number(number) or None,
            "country": f"{cc[0]}, {country_en}" if cc else None,
            "country_hi": f"{cc[0]}, {country_hi}" if cc else None,
            "bank": payer.get("bank_name"), "bank_hi": payer.get("bank_name_hi"),
            "minutes": str(max(minutes, CFG.trigger.long_call_min)) if "call_ongoing_long" in sig else None,
            "amount": format_inr(amount),
        }
        trusted = None
        if hist is not None:
            trusted = {"prior_payments": hist["count"], "usual_amount_inr": hist["usual_amount"], "amount_inr": amount}
        return {"signals": sig, "params": params, "trigger": trig.model_dump(), "trusted": trusted,
                "number": number, "state": state, "channel": channel, "in_contacts": bool(in_contacts)}

    # --------------------------------------------------------------- scoring
    def _signals(self, case: dict) -> list[str]:
        sig = list(case["context_signals"])
        claim = case.get("claim")
        if claim:
            sig.append(f"claim_{claim}")
            if claim == "bank" and case.get("caller_number") and not is_1600_series(case["caller_number"]):
                sig.append("bank_claim_not_1600")
            if claim == "family" and case.get("relative") and not names_match(case.get("payee_name"), case["relative"]):
                sig.append("payee_name_mismatch")
        for kind, mapping in CHECK_SIGNALS.items():
            res = (case["checks"].get(kind) or {}).get("result")
            if res in mapping:
                sig.append(mapping[res])
        v = case["checks"].get("voice")
        if v:
            # Use the detector's raw band; the engine's G3 gate (not the voice service) decides
            # whether low-quality audio is downgraded to inconclusive, so it is visible in guardrails.
            from .voice import band_for
            raw = band_for(v["p_synthetic"], True) if v.get("p_synthetic") is not None else v["band"]
            sig.append(f"voice_{raw}")
            if (v.get("watermark") or {}).get("detected"):
                sig.append("watermark_detected")
        sig += [c for c in case.get("cues", []) if c in ALLOWED_CUES]
        return sig

    def _rescore(self, case: dict, reason: str) -> dict:
        t0 = time.perf_counter()
        params = dict(case["params"])
        if case.get("relative"):
            params["relative"] = case["relative"]["name"]
            params["relative_hi"] = case["relative"].get("name_hi")
            params.update(PRONOUNS.get(case["relative"].get("pronoun"), {}))
        v = case["checks"].get("voice")
        a = assess(self._signals(case), voice_quality=(v or {}).get("quality") if v else None,
                   trusted=TrustedPayee(**case["trusted"]) if case.get("trusted") else None, params=params, cfg=CFG)
        has_check = any((case["checks"].get(k) or {}).get("result") for k in CHECK_SIGNALS)
        stage = "verified" if has_check else ("claim" if case.get("claim") else "context")
        ask = stage == "context" and should_ask_claim(a, CFG)
        prev_tier = case.get("tier")
        case.update({
            "stage": stage, "tier": a.tier, "raw_tier": a.raw_tier, "p": a.p, "log_odds": a.log_odds,
            "prior": a.prior, "prior_log_odds": a.prior_log_odds, "thresholds": a.thresholds,
            "signals": a.signals, "dropped": a.dropped, "qualifying_families": a.qualifying_families,
            "families": {k: f.model_dump() for k, f in a.families.items()},
            "reasons": [r.model_dump() for r in a.reasons],
            "top_reasons": [r.model_dump() for r in a.top_reasons(3)],
            "guardrails": [g.model_dump() for g in a.guardrails_applied],
            "ask_claim": ask, "config_version": a.config_version, "updated_at_ist": self.ts(),
        })
        done = {k for k in ("family_verify", "callback", "safeword", "bank_registry", "voice_check")
                if (case["checks"].get(k.replace("_check", "")) or {}).get("result") or
                (k == "voice_check" and case["checks"].get("voice"))}
        if (case["checks"].get("family_verify") or {}).get("status") == "pending":
            done.add("family_verify")
        aparams = {"relative": params.get("relative"), "relative_hi": params.get("relative_hi"),
                   "bank": params.get("bank"), "bank_hi": params.get("bank_hi"), "their": params.get("their")}
        case["actions"] = [x.model_dump() for x in actions_for(a.tier, case.get("claim"), amount_inr=case["amount_inr"],
                                                                 params=aparams, done=done, cfg=CFG)]
        case["copy"] = {"title": copy_text(f"tier_{a.tier}_title"), "body": copy_text(f"tier_{a.tier}_body")}
        # status + hold
        if a.tier == "red":
            if not case.get("hold"):
                until = self.now() + timedelta(minutes=CFG.actions.hold_minutes)
                case["hold"] = {"started_at": self.ts(), "until": ist_iso(until), "minutes": CFG.actions.hold_minutes,
                                "auto_send_on_expiry": False, "released": False}
                self._event(case, "hold_started", "risk_api", {"minutes": CFG.actions.hold_minutes, "auto_send": False})
            case["status"] = "held"
        elif case.get("hold") and not case["hold"].get("released"):
            case["status"] = "held"   # a positive check never silently releases a hold
        elif (case["checks"].get("family_verify") or {}).get("status") == "pending":
            case["status"] = "awaiting_verification"
        elif case.get("status") not in ("sent", "cancelled", "reported", "confirmed_fraud", "false_positive"):
            case["status"] = "cleared" if a.tier == "green" else "paused"
        if case.get("hold"):
            needs_review = case["amount_inr"] >= CFG.actions.analyst_review_at_or_above_inr
            positive = a.tier == "green"
            case["hold"]["release_requires"] = "analyst_review" if needs_review else ("none" if positive else "positive_check")
            case["hold"]["can_release_now"] = (not needs_review) and positive
        case.setdefault("history", []).append(
            {"ts": self.ts(), "stage": stage, "tier": a.tier, "p": round(a.p, 4), "why": reason})
        self._event(case, "assessment", "risk_api", {
            "stage": stage, "tier": a.tier, "raw_tier": a.raw_tier, "p": round(a.p, 5), "signals": a.signals,
            "guardrails": [g.id for g in a.guardrails_applied], "why": reason,
            "tier_changed": prev_tier is not None and prev_tier != a.tier})
        case["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        self.s.put_case(case)
        return case

    # ------------------------------------------------------------- endpoints
    def assess(self, req: dict) -> dict:
        t0 = time.perf_counter()
        cid = req.get("case_id")
        if cid:
            case = self.get(cid)
            changed = []
            if req.get("claim"):
                if req["claim"] not in CLAIM_CODES:
                    raise CaseError(422, f"claim must be one of {sorted(CLAIM_CODES)}")
                case["claim"] = req["claim"]
                changed.append("claim")
                if req["claim"] == "family":
                    rel = self._relative(case["payer_id"], req.get("claim_target"))
                    case["relative"] = rel
                    case["relative_name"] = rel["name"] if rel else None
                self._event(case, "claim", "payer_app", {"claim": req["claim"], "claim_target": req.get("claim_target")})
            if req.get("cues"):
                case["cues"] = sorted(set(case.get("cues", [])) | (set(req["cues"]) & ALLOWED_CUES))
                changed.append("cues")
                self._event(case, "checklist", "payer_app", {"cues": case["cues"]})
            if req.get("voice"):
                self._attach_voice(case, req["voice"])
                changed.append("voice")
            case = self._rescore(case, "+".join(changed) or "reassess")
            return self._response(case, t0)

        payer = self.s.get_user(req["payer_id"])
        if not payer:
            raise CaseError(404, f"unknown payer {req['payer_id']}")
        payment, call = req["payment"], req.get("call") or {}
        ctx = self._context(payer, payment, call)
        if not ctx["trigger"]["fired"]:
            self.s.next_counter("not_triggered")
            return {"case_id": None, "triggered": False, "trigger": ctx["trigger"], "tier": "green", "p": None,
                    "reasons": [], "top_reasons": [], "actions": [x.model_dump() for x in actions_for("green", None)],
                    "guardrails": [], "ask_claim": False, "status": "not_assessed",
                    "copy": {"title": copy_text("tier_green_title"), "body": copy_text("tier_green_body")},
                    "latency_ms": round((time.perf_counter() - t0) * 1000, 2)}
        amount = float(payment["amount_inr"])
        case = {
            "case_id": "pending", "created_at_ist": self.ts(), "scenario": req.get("scenario"),
            "payer_id": payer["id"], "payer_name": payer["name"], "payer_phone": payer.get("phone"),
            "payer_vpa_masked": payer.get("vpa_masked"), "payer_bank": payer.get("bank_name"),
            "payer_age_band": payer.get("age_band"),
            "payee_vpa": payment["payee_vpa"], "payee_name": payment.get("payee_name"), "amount_inr": amount,
            "amount_display": format_inr(amount),
            "caller_number": ctx["number"] or None, "caller_display": pretty_number(ctx["number"]) or None,
            "caller_in_contacts": ctx["in_contacts"], "call_channel": ctx["channel"], "call_state": ctx["state"],
            "call_duration_sec": call.get("duration_sec"),
            "claim": None, "relative": None, "relative_name": None, "checks": {}, "cues": [],
            "context_signals": ctx["signals"], "params": ctx["params"], "trusted": ctx["trusted"],
            "trigger": ctx["trigger"], "status": "open", "history": [],
        }
        # score before persisting: silent Green keeps only an anonymous counter (SPEC 5)
        probe = assess(ctx["signals"], trusted=TrustedPayee(**ctx["trusted"]) if ctx["trusted"] else None,
                       params=ctx["params"], cfg=CFG)
        if probe.tier == "green" and not should_ask_claim(probe, CFG):
            self.s.next_counter("green_silent")
            return {"case_id": None, "triggered": True, "trigger": ctx["trigger"], "stage": "context", "tier": "green",
                    "p": probe.p, "log_odds": probe.log_odds, "reasons": [r.model_dump() for r in probe.reasons],
                    "top_reasons": [], "guardrails": [g.model_dump() for g in probe.guardrails_applied],
                    "actions": [x.model_dump() for x in actions_for("green", None)], "ask_claim": False,
                    "status": "cleared_silently",
                    "copy": {"title": copy_text("tier_green_title"), "body": copy_text("tier_green_body")},
                    "latency_ms": round((time.perf_counter() - t0) * 1000, 2)}
        case["case_id"] = self._new_case_id()
        self._event(case, "payment_attempt", "payer_app", {
            "payee_vpa": case["payee_vpa"], "amount_inr": amount, "caller": ctx["number"], "channel": ctx["channel"],
            "trigger": ctx["trigger"]["why"]})
        case = self._rescore(case, "pay_tap")
        return self._response(case, t0)

    def _response(self, case: dict, t0: float) -> dict:
        keys = ["case_id", "stage", "tier", "raw_tier", "p", "log_odds", "prior", "prior_log_odds", "thresholds",
                "reasons", "top_reasons", "actions", "guardrails", "families", "signals", "qualifying_families",
                "ask_claim", "status", "hold", "copy", "claim", "relative", "checks", "trigger", "amount_display",
                "payee_name", "payee_vpa", "caller_display", "config_version"]
        out = {k: case.get(k) for k in keys}
        out["triggered"] = True
        out["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        return out

    def get(self, cid: str) -> dict:
        case = self.s.get_case(cid)
        if not case:
            raise CaseError(404, f"case {cid} not found")
        return case

    def _relative(self, payer_id: str, rel_id: str | None) -> dict | None:
        payer = self.s.get_user(payer_id) or {}
        circle = payer.get("circle", [])
        if rel_id:
            for r in circle:
                if r["id"] == rel_id:
                    return r
        return circle[0] if circle else None

    # ----------------------------------------------------------- checks
    def bank_registry_check(self, cid: str) -> dict:
        case = self.get(cid)
        call = self.bank.active_call(case["payer_id"])
        result = "active_call_1600" if (call and call["is_1600"]) else "no_active_call"
        case["checks"]["bank_registry"] = {"result": result, "ts": self.ts(), "registry_call": call,
                                           "source": "mock_bank_registry"}
        self._event(case, "check_result", "mock_bank_registry", {"kind": "bank_registry", "result": result})
        return self._rescore(case, "bank_registry")

    def user_check(self, cid: str, kind: str, result: str) -> dict:
        if kind not in ("callback", "safeword") or result not in CHECK_SIGNALS[kind]:
            raise CaseError(422, f"bad check {kind}={result}")
        case = self.get(cid)
        case["checks"][kind] = {"result": result, "ts": self.ts(), "source": "user_report"}
        self._event(case, "check_result", "payer_app", {"kind": kind, "result": result})
        return self._rescore(case, kind)

    def _attach_voice(self, case: dict, v: dict) -> None:
        keep = {k: v.get(k) for k in ("p_synthetic", "band", "quality", "watermark", "model_version", "latency_ms", "mock")}
        case["checks"]["voice"] = keep
        self._event(case, "voice_scored", "voice_service", {
            "p_synthetic": v.get("p_synthetic"), "band": v.get("band"), "model_version": v.get("model_version"),
            "quality_ok": (v.get("quality") or {}).get("ok"), "audio_retained": False})

    def attach_voice(self, cid: str, v: dict) -> dict:
        case = self.get(cid)
        self._attach_voice(case, v)
        return self._rescore(case, "voice")

    # ------------------------------------------------------- family verify
    def create_challenge(self, cid: str, relative_id: str | None) -> tuple[dict, dict]:
        case = self.get(cid)
        rel = self._relative(case["payer_id"], relative_id or (case.get("relative") or {}).get("id"))
        if not rel:
            raise CaseError(404, "no relative in the payer's Pehchaan circle")
        if not rel.get("device_id"):
            raise CaseError(409, f"{rel['name']} has not joined the Pehchaan circle on a phone")
        ch_id = "fv_" + secrets.token_hex(6)
        nonce = secrets.token_hex(16)
        created = self.now()
        expires = created + timedelta(seconds=CFG.actions.family_verify_timeout_sec)
        payer = self.s.get_user(case["payer_id"]) or {}
        amount_band, amount_band_hi = _amount_band(case["amount_inr"])
        verb_hi = "वाली" if payer.get("gender") == "f" else "वाले"
        message = {
            "en": f"{rel.get('calls_payer', payer.get('name'))} is about to send {amount_band} to '{case['payee_name']}' "
                  f"because someone said they are you. Is this you?",
            "hi": f"{rel.get('calls_payer_hi', payer.get('name'))} '{case['payee_name']}' को {amount_band_hi} भेजने {verb_hi} हैं, "
                  f"क्योंकि किसी ने कहा कि वो आप हैं। क्या ये आप हैं?",
        }
        case["relative"] = case.get("relative") or rel
        case["relative_name"] = rel["name"]
        case["checks"]["family_verify"] = {"status": "pending", "challenge_id": ch_id, "sent_at": ist_iso(created),
                                           "expires_at": ist_iso(expires), "relative_id": rel["id"]}
        self._event(case, "fv_challenge_sent", "family_verify", {
            "challenge_id": ch_id, "relative_id": rel["id"], "device_id": rel["device_id"],
            "shown": {"amount_band": amount_band, "payee_name": case["payee_name"]}})
        case = self._rescore(case, "fv_sent")
        push = {"challenge_id": ch_id, "case_id": cid, "nonce": nonce, "expires_at": ist_iso(expires),
                "timeout_sec": CFG.actions.family_verify_timeout_sec, "relative": rel,
                "payer_name": payer.get("name"), "calls_payer": rel.get("calls_payer"),
                "calls_payer_hi": rel.get("calls_payer_hi"),
                "amount_band": amount_band, "payee_name": case["payee_name"], "message": message,
                "amount_band_hi": amount_band_hi, "sign_format": "pehchaan-fv|{challenge_id}|{nonce}|{answer}"}
        self.s.x("INSERT INTO challenges(id, case_id, relative_id, device_id, nonce, created_at, expires_at, status, message)"
                 " VALUES(?,?,?,?,?,?,?,?,?)",
                 (ch_id, cid, rel["id"], rel["device_id"], nonce, ist_iso(created), ist_iso(expires), "pending",
                  json.dumps(push, ensure_ascii=False)))
        return case, push

    def respond_challenge(self, ch_id: str, answer: str, device_id: str, signature_b64: str) -> dict:
        row = self.s.one("SELECT * FROM challenges WHERE id=?", (ch_id,))
        if not row:
            raise CaseError(404, "challenge not found")
        if row["status"] != "pending":
            raise CaseError(409, f"challenge already {row['status']}")
        if answer not in ("yes", "no"):
            raise CaseError(422, "answer must be yes|no")
        if device_id != row["device_id"]:
            raise CaseError(403, "response must come from the relative's bound device")
        dev = self.s.one("SELECT public_key_b64 FROM devices WHERE device_id=?", (device_id,))
        if not dev:
            raise CaseError(403, "device not bound")
        msg = f"pehchaan-fv|{ch_id}|{row['nonce']}|{answer}".encode()
        if not verify_signature(dev["public_key_b64"], msg, signature_b64):
            raise CaseError(403, "bad device signature")
        result = "confirmed" if answer == "yes" else "denied"
        self.s.x("UPDATE challenges SET status=?, answer=?, signature=? WHERE id=?", (result, answer, signature_b64, ch_id))
        case = self.get(row["case_id"])
        case["checks"]["family_verify"].update({"status": result, "result": result, "answered_at": self.ts(),
                                                "sig_ok": True, "device_id": device_id})
        self._event(case, "fv_response", "relative_device", {
            "challenge_id": ch_id, "answer": answer, "device_id": device_id, "signature_verified": True,
            "sig_sha256_prefix": __import__("hashlib").sha256(signature_b64.encode()).hexdigest()[:16]})
        return self._rescore(case, f"fv_{result}")

    def timeout_challenge(self, ch_id: str) -> dict | None:
        row = self.s.one("SELECT * FROM challenges WHERE id=?", (ch_id,))
        if not row or row["status"] != "pending":
            return None
        self.s.x("UPDATE challenges SET status='timeout' WHERE id=?", (ch_id,))
        case = self.get(row["case_id"])
        case["checks"]["family_verify"].update({"status": "timeout", "result": "timeout", "answered_at": self.ts()})
        self._event(case, "fv_timeout", "family_verify", {"challenge_id": ch_id})
        return self._rescore(case, "fv_timeout")

    def pending_challenges(self, device_id: str) -> list[dict]:
        rows = self.s.all("SELECT * FROM challenges WHERE device_id=? AND status='pending' ORDER BY created_at DESC",
                          (device_id,))
        return [json.loads(r["message"]) for r in rows]

    def register_device(self, device_id: str, user_id: str, public_key_b64: str) -> dict:
        self.s.x("INSERT OR REPLACE INTO devices(device_id, user_id, public_key_b64, bound_at) VALUES(?,?,?,?)",
                 (device_id, user_id, public_key_b64, self.ts()))
        return {"device_id": device_id, "user_id": user_id, "bound_at": self.ts(),
                "key_id": "ed25519:" + __import__("hashlib").sha256(public_key_b64.encode()).hexdigest()[:12]}

    # ------------------------------------------------------------ user + analyst
    def user_action(self, cid: str, action: str) -> dict:
        case = self.get(cid)
        st = case.get("status")
        if action == "continue":
            if case["tier"] == "red" or st == "held":
                raise CaseError(409, "payment is on a cooling-off hold; use release paths")
            case["status"] = "sent"
            case["utr"] = f"DEMO{secrets.randbelow(10**10):010d}"
        elif action == "pay":
            if case["tier"] != "green" or st == "held":
                raise CaseError(409, "payment needs a check first")
            case["status"] = "sent"
            case["utr"] = f"DEMO{secrets.randbelow(10**10):010d}"
        elif action == "cancel":
            case["status"] = "cancelled"
        elif action == "report":
            case["status"] = "reported" if st != "sent" else st
            case["reported"] = True
        elif action == "release":
            hold = case.get("hold") or {}
            if not hold:
                raise CaseError(409, "no hold to release")
            if not hold.get("can_release_now"):
                case["release_requested"] = True
                self._event(case, "release_requested", "payer_app", {"requires": hold.get("release_requires")})
                self.s.put_case(case)
                return case
            hold["released"] = True
            case["status"] = "released"
        elif action == "bank_callback":
            case["callback_requested"] = True
        else:
            raise CaseError(422, f"unknown action {action}")
        self._event(case, "user_action", "payer_app", {"action": action, "status": case["status"]})
        case["updated_at_ist"] = self.ts()
        self.s.put_case(case)
        return case

    def analyst_decision(self, cid: str, decision: str, analyst: str, role: str, note: str | None) -> dict:
        if role not in ("fraud_analyst", "supervisor"):
            raise CaseError(403, f"role {role} cannot take decisions")
        case = self.get(cid)
        if decision == "release_hold":
            if not case.get("hold"):
                raise CaseError(409, "no hold on this case")
            case["hold"]["released"] = True
            case["hold"]["released_by"] = analyst
            case["status"] = "released"
        elif decision == "confirm_fraud":
            case["status"] = "confirmed_fraud"
            case["mule_flag_sent"] = True
        elif decision == "false_positive":
            case["status"] = "false_positive"
            if case.get("hold"):
                case["hold"]["released"] = True
            self.s.x("INSERT INTO feedback(ts, case_id, label, analyst, note) VALUES(?,?,?,?,?)",
                     (self.ts(), cid, "genuine", analyst, note))
        else:
            raise CaseError(422, "decision must be release_hold | confirm_fraud | false_positive")
        if decision == "confirm_fraud":
            self.s.x("INSERT INTO feedback(ts, case_id, label, analyst, note) VALUES(?,?,?,?,?)",
                     (self.ts(), cid, "scam", analyst, note))
        case["analyst"] = {"decision": decision, "by": analyst, "role": role, "at": self.ts(), "note": note}
        self._event(case, "analyst_decision", f"analyst:{analyst}", {"decision": decision, "role": role, "note": note})
        case["updated_at_ist"] = self.ts()
        self.s.put_case(case)
        return case

    def evidence_pack(self, cid: str, include_transcript: bool = False) -> dict:
        case = self.get(cid)
        if case.get("checks", {}).get("family_verify", {}).get("result") == "denied":
            case["check_summary"] = (f"{case.get('relative_name')} said on their own phone, through the bank app's "
                                     "Family Verify, that they did not ask for this money.")
        elif case.get("checks", {}).get("bank_registry", {}).get("result") == "no_active_call":
            case["check_summary"] = f"{case.get('payer_bank') or 'My bank'} confirmed it was not calling me."
        self._event(case, "evidence_pack_generated", "risk_api", {"by": "user", "transcript": include_transcript})
        case["voice"] = case.get("checks", {}).get("voice")
        pack = build_evidence_pack(case, self.s.events(cid), self.signer, include_transcript=include_transcript,
                                   now_iso=self.ts())
        case["evidence"] = {"generated_at": pack["generated_at_ist"], "head": pack["hash_chain"]["head"],
                            "sig_key_id": pack["signature"]["key_id"]}
        self.s.put_case(case)
        return pack


def _amount_band(amount: float) -> tuple[str, str]:
    """Privacy: the relative sees an amount band, not the exact figure (round amounts stay exact)."""
    if amount < 1000:
        return "under ₹1,000", "₹1,000 से कम"
    step = 1000 if amount < 10000 else (5000 if amount < 100000 else 50000)
    rounded = round(amount / step) * step
    r = format_inr(rounded)
    if abs(rounded - amount) < 1:
        return r, r
    return "about " + r, "लगभग " + r
