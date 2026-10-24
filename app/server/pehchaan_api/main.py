"""Pehchaan risk API (prototype). SPEC section 7 contracts.

Run:  cd app/server && python -m uvicorn pehchaan_api.main:app --port 8400
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

SERVER_DIR = Path(__file__).resolve().parents[1]
REPO = SERVER_DIR.parents[1]
sys.path.insert(0, str(REPO / "engine"))

from pehchaan import default_config  # noqa: E402
from pehchaan.explain import copy_text  # noqa: E402
from pehchaan.evidence import ist_iso, render_pack_pdf, verify_chain, verify_pack  # noqa: E402

from . import voice as voice_svc  # noqa: E402
from .db import Store  # noqa: E402
from .risk import CaseError, CaseService  # noqa: E402
from .scenarios import SCENARIOS, build_custom, load_scenario, seed_background, seed_people  # noqa: E402

DATA_DIR = Path(os.environ.get("PEHCHAAN_DATA", SERVER_DIR / "data"))


# --------------------------------------------------------------------------- hub
class Hub:
    """Topic fan-out for WebSockets: case:{id}, device:{id}, console, demo."""

    def __init__(self):
        self.subs: dict[str, set[WebSocket]] = defaultdict(set)

    async def join(self, topic: str, ws: WebSocket):
        await ws.accept()
        self.subs[topic].add(ws)

    def leave(self, topic: str, ws: WebSocket):
        self.subs[topic].discard(ws)

    async def send(self, topic: str, msg: dict):
        dead = []
        data = json.dumps(msg, ensure_ascii=False, default=str)
        for ws in list(self.subs.get(topic, ())):
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.subs[topic].discard(ws)


def case_summary(c: dict) -> dict:
    return {k: c.get(k) for k in (
        "case_id", "created_at_ist", "updated_at_ist", "status", "tier", "p", "amount_inr", "amount_display",
        "payee_name", "payee_vpa", "payer_name", "caller_display", "call_channel", "claim", "scenario", "stage",
        "relative_name", "hold")} | {"top_codes": [r["code"] for r in (c.get("top_reasons") or [])][:3]}


# --------------------------------------------------------------------------- models
class CallIn(BaseModel):
    state: Literal["active", "ended", "none"] = "active"
    number: str | None = None
    channel: Literal["pstn", "whatsapp", "voip"] = "pstn"
    duration_sec: float = 0
    ended_sec_ago: float | None = None
    in_contacts: bool | None = Field(None, description="On-device contact-hash match result, if the SDK sends it")


class PaymentIn(BaseModel):
    payee_vpa: str
    payee_name: str | None = None
    amount_inr: float = Field(gt=0)


class AssessIn(BaseModel):
    case_id: str | None = None
    payer_id: str | None = None
    payment: PaymentIn | None = None
    call: CallIn | None = None
    claim: Literal["family", "bank", "upi_or_shop", "authority", "other", "none"] | None = None
    claim_target: str | None = Field(None, description="relative id for family; bank id for bank (e.g. 'bdb')")
    cues: list[str] = []
    checklist_done: bool = False
    voice: dict | None = None
    scenario: str | None = None


class FamilyVerifyIn(BaseModel):
    case_id: str
    relative_id: str | None = None


class RespondIn(BaseModel):
    answer: Literal["yes", "no"]
    device_id: str
    signature_b64: str


class DeviceIn(BaseModel):
    device_id: str
    user_id: str
    public_key_b64: str


class CheckIn(BaseModel):
    result: str | None = None


class ActionIn(BaseModel):
    action: Literal["continue", "pay", "cancel", "report", "release", "bank_callback"]


class DecisionIn(BaseModel):
    decision: Literal["release_hold", "confirm_fraud", "false_positive"]
    note: str | None = None


class CustomCaseIn(BaseModel):
    """The jury's own case on the demo page (FINALE_PLAN B1)."""
    payer_id: Literal["u_sunita", "u_ramesh", "u_kamala"] = "u_sunita"
    caller: Literal["saved", "unknown", "international", "bank_1600"] = "unknown"
    channel: Literal["pstn", "whatsapp"] = "pstn"
    call_state: Literal["active", "ended", "none"] = "active"
    duration_min: float = Field(6, ge=0, le=240)
    ended_min: float = Field(5, ge=0, le=24 * 60)
    amount_inr: float = Field(50000, gt=0, le=10_000_000)
    payee: Literal["usual", "new"] = "new"
    payee_name: str = Field("Arif Traders", max_length=60)
    payee_flagged: bool = False
    caller_fri: Literal["medium", "high", "very_high"] | None = None
    bank_calling: bool = False


# --------------------------------------------------------------------------- app
def create_app(db_path: str | None = None, key_path: str | None = None) -> FastAPI:
    db_path = db_path or os.environ.get("PEHCHAAN_DB") or str(DATA_DIR / "pehchaan.db")
    key_path = key_path or str(DATA_DIR / "keys" / "evidence_ed25519.pem")
    store = Store(db_path)
    svc = CaseService(store, key_path)
    hub = Hub()
    timers: dict[str, asyncio.Task] = {}

    app = FastAPI(title="Pehchaan risk API (prototype)", version="0.1.0",
                  description="Verify the person, not the voice. All context adapters are mocks (mock_*).")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
                       expose_headers=["X-Server-Now"])
    app.state.svc, app.state.hub = svc, hub

    @app.middleware("http")
    async def _server_now(request: Request, call_next):
        resp = await call_next(request)
        resp.headers["X-Server-Now"] = svc.ts()  # clients count down against server time (demo clock safe)
        return resp

    if not store.list_cases() and not store.get_user("u_sunita"):
        seed_people(svc)
        seed_background(svc)

    @app.exception_handler(CaseError)
    async def _case_err(_: Request, exc: CaseError):
        return JSONResponse(status_code=exc.status, content={"detail": exc.msg})

    async def publish(case: dict, kind: str = "assessment"):
        msg = {"type": kind, "case_id": case["case_id"], "ts": svc.ts(), "data": svc._response(case, time.perf_counter())}
        await hub.send(f"case:{case['case_id']}", msg)
        await hub.send("console", {"type": "case_update", "case_id": case["case_id"], "data": case_summary(case)})

    def rbac(role: str | None, analyst: str | None, case_id: str | None, action: str, reason: str | None):
        role = role or "fraud_analyst"
        if role not in ("fraud_analyst", "supervisor", "auditor"):
            raise HTTPException(403, f"role {role!r} has no console access")
        store.log_access(ist_iso(), analyst or "unknown", role, case_id, action, reason)
        return role

    # ------------------------------------------------------------- health
    @app.get("/v1/health")
    def health():
        return {"ok": True, "time_ist": ist_iso(), "voice_service": os.environ.get("VOICE_SERVICE_URL") or "mock",
                "signer_key_id": svc.signer.key_id, "config_version": default_config().version,
                "adapters": ["mock_fri", "mock_i4c", "mock_bank_registry", "mock_contacts", "mock_payer_history"]}

    # ------------------------------------------------------------- risk
    @app.post("/v1/risk/assess")
    async def risk_assess(body: AssessIn):
        if not body.case_id and (not body.payer_id or not body.payment):
            raise HTTPException(422, "payer_id and payment are required for a new assessment")
        res = svc.assess(body.model_dump())
        if res.get("case_id"):
            case = svc.get(res["case_id"])
            await publish(case)
            if body.claim and svc.auto_family_verify_due(res["case_id"]):
                # SPEC v0.2 A19: "Family member" + an enrolled relative -> the push goes out without a tap
                try:
                    fv = await _send_fv(res["case_id"], (case.get("relative") or {}).get("id"), auto=True)
                except CaseError as exc:
                    if exc.status != 429:
                        raise
                    res["auto_family_verify"] = {"skipped": exc.msg}  # SPEC v0.3 rate limit: the payer calls instead
                else:
                    res = fv.pop("assessment")
                    res["auto_family_verify"] = fv
        return res

    # ------------------------------------------------------------- voice
    @app.post("/v1/voice/score")
    async def voice_score(file: UploadFile = File(...), case_id: str | None = Form(None),
                          demo_hint: str | None = Form(None)):
        data = await file.read()
        if len(data) > voice_svc.MAX_UPLOAD_BYTES:  # never cut compressed audio mid-stream: refuse instead
            raise HTTPException(413, "audio file larger than 25 MB")
        res = await voice_svc.score(data, file.filename or "clip.wav", demo_hint)
        res["audio_retained"] = False
        mode = default_config().voice.mode
        res["voice_mode"] = mode
        res["used_in_decision"] = mode == "calibrated"   # watermark_detected is always used (positive-only)
        wm = bool((res.get("watermark") or {}).get("detected"))
        if wm:
            res["user_message"] = copy_text("voice_watermark_result")
        elif mode == "shadow":
            res["user_message"] = copy_text("voice_shadow_result")
        else:
            res["user_message"] = None  # calibrated: the client shows the band explanation
        if case_id:
            case = svc.attach_voice(case_id, res)
            await publish(case)
            res["assessment"] = svc._response(case, time.perf_counter())
        return res

    @app.post("/v1/voice/panel")
    async def voice_panel(file: UploadFile = File(...)):
        """Detector bench: every detector on the same clip, side by side, plus the fused verdict. Evidence only:
        nothing here changes a payment decision (G2), and the audio is processed in memory and dropped."""
        data = await file.read()
        if len(data) > voice_svc.MAX_UPLOAD_BYTES:
            raise HTTPException(413, "audio file larger than 25 MB")
        try:
            res = await voice_svc.panel(data, file.filename or "clip")
        except voice_svc.PanelUnavailable as exc:
            raise HTTPException(503, f"detector panel unavailable: {exc}")
        res["audio_retained"] = False
        res["used_in_decision"] = False
        return res

    @app.get("/v1/demo/audio/{kind}.wav")
    def demo_audio(kind: Literal["synthetic", "bonafide", "noisy", "short"]):
        return Response(voice_svc.demo_wav(kind), media_type="audio/wav")

    # ------------------------------------------------------------- family verify
    async def _timeout_later(ch_id: str, delay: float):
        try:
            await asyncio.sleep(delay)
            case = svc.timeout_challenge(ch_id)
            if case:
                await publish(case)
                dev = case["checks"]["family_verify"]
                await hub.send(f"device:{case['relative']['device_id']}",
                               {"type": "fv_expired", "challenge_id": ch_id, "case_id": case["case_id"]})
                del dev
        except asyncio.CancelledError:
            pass

    async def _send_fv(case_id: str, relative_id: str | None, auto: bool = False) -> dict:
        case, push = svc.create_challenge(case_id, relative_id, auto=auto)
        await hub.send(f"device:{push['relative']['device_id']}", {"type": "fv_request", "data": push})
        await publish(case)
        timers[push["challenge_id"]] = asyncio.create_task(_timeout_later(push["challenge_id"], push["timeout_sec"]))
        return {"challenge_id": push["challenge_id"], "expires_at": push["expires_at"], "timeout_sec": push["timeout_sec"],
                "relative": {k: push["relative"][k] for k in ("id", "name", "relation")}, "auto": auto,
                "shown_to_relative": push["message"], "assessment": svc._response(case, time.perf_counter())}

    @app.post("/v1/verify/family")
    async def verify_family(body: FamilyVerifyIn):
        return await _send_fv(body.case_id, body.relative_id)

    @app.post("/v1/verify/family/{challenge_id}/cancel")
    async def verify_cancel(challenge_id: str):
        """The payer taps "Cancel request" on the auto-sent Family Verify (SPEC v0.2 A19)."""
        case = svc.cancel_challenge(challenge_id)
        t = timers.pop(challenge_id, None)
        if t:
            t.cancel()
        await publish(case)
        await hub.send(f"device:{(case.get('relative') or {}).get('device_id')}",
                       {"type": "fv_expired", "challenge_id": challenge_id, "case_id": case["case_id"], "cancelled": True})
        return svc._response(case, time.perf_counter())

    @app.post("/v1/verify/family/{challenge_id}/respond")
    async def verify_respond(challenge_id: str, body: RespondIn):
        case = svc.respond_challenge(challenge_id, body.answer, body.device_id, body.signature_b64)
        t = timers.pop(challenge_id, None)
        if t:
            t.cancel()
        await publish(case)
        await hub.send(f"device:{body.device_id}", {"type": "fv_done", "challenge_id": challenge_id,
                                                    "answer": body.answer})
        return {"ok": True, "result": case["checks"]["family_verify"]["result"], "tier": case["tier"]}

    @app.get("/v1/devices/{device_id}/challenges")
    def device_challenges(device_id: str):
        return svc.pending_challenges(device_id)

    @app.post("/v1/devices/register")
    def device_register(body: DeviceIn):
        return svc.register_device(body.device_id, body.user_id, body.public_key_b64)

    # ------------------------------------------------------------- checks + user actions
    @app.post("/v1/cases/{case_id}/checks/{kind}")
    async def case_check(case_id: str, kind: Literal["bank_registry", "callback", "safeword"], body: CheckIn | None = None):
        if kind == "bank_registry":
            case = svc.bank_registry_check(case_id)
        else:
            case = svc.user_check(case_id, kind, (body or CheckIn()).result or "")
        await publish(case)
        return svc._response(case, time.perf_counter())

    @app.post("/v1/cases/{case_id}/user-action")
    async def case_user_action(case_id: str, body: ActionIn):
        case = svc.user_action(case_id, body.action)
        await publish(case, "case_status")
        return svc._response(case, time.perf_counter()) | {"utr": case.get("utr"),
                                                            "release_requested": case.get("release_requested")}

    # ------------------------------------------------------------- analyst console
    @app.get("/v1/cases")
    def cases_list(x_role: str | None = Header(None), x_analyst: str | None = Header(None)):
        rbac(x_role, x_analyst, None, "list_cases", None)
        return [case_summary(c) for c in store.list_cases()]

    @app.get("/v1/cases/{case_id}")
    def case_get(case_id: str, x_role: str | None = Header(None), x_analyst: str | None = Header(None),
                 x_access_reason: str | None = Header(None)):
        role = rbac(x_role, x_analyst, case_id, "view_case", x_access_reason or "queue review")
        case = svc.get(case_id)
        out = dict(case)
        out["events"] = store.events(case_id)
        ok, msg = verify_chain(out["events"])
        out["chain"] = {"verified": ok, "detail": msg, "head": out["events"][-1]["hash"] if out["events"] else None}
        out["access_log"] = store.access_log(case_id, 8)
        out["viewer"] = {"role": role, "analyst": x_analyst or "unknown"}
        if role == "auditor":
            out.pop("payer_phone", None)
        return out

    @app.post("/v1/cases/{case_id}/decision")
    async def case_decision(case_id: str, body: DecisionIn, x_role: str | None = Header(None),
                            x_analyst: str | None = Header(None)):
        role = rbac(x_role, x_analyst, case_id, f"decision:{body.decision}", body.note)
        case = svc.analyst_decision(case_id, body.decision, x_analyst or "unknown", role, body.note)
        await publish(case, "case_status")
        return case_summary(case) | {"analyst": case.get("analyst")}

    @app.get("/v1/access-log")
    def access_log(x_role: str | None = Header(None), x_analyst: str | None = Header(None)):
        rbac(x_role, x_analyst, None, "view_access_log", None)
        return store.access_log(None, 100)

    # ------------------------------------------------------------- evidence
    @app.post("/v1/cases/{case_id}/evidence-pack")
    async def evidence_pack(case_id: str, include_transcript: bool = False):
        pack = svc.evidence_pack(case_id, include_transcript)
        (DATA_DIR / "packs").mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "packs" / f"{case_id}.json").write_text(json.dumps(pack, ensure_ascii=False, indent=1), "utf-8")
        await publish(svc.get(case_id), "case_status")
        ok, msg = verify_pack(pack)
        return pack | {"verification": {"ok": ok, "detail": msg},
                       "pdf_url": f"/v1/cases/{case_id}/evidence-pack.pdf"}

    @app.get("/v1/cases/{case_id}/evidence-pack.pdf")
    def evidence_pdf(case_id: str):
        jp = DATA_DIR / "packs" / f"{case_id}.json"
        if not jp.exists():
            raise HTTPException(404, "generate the pack first (POST .../evidence-pack)")
        pack = json.loads(jp.read_text("utf-8"))
        pdf = DATA_DIR / "packs" / f"{case_id}.pdf"
        fonts = (REPO / "app" / "web" / "public" / "fonts" / "fonts.css")
        out = render_pack_pdf(pack, pdf, fonts.resolve().as_uri() if fonts.exists() else None)
        if not out:
            raise HTTPException(501, "PDF rendering needs Playwright")
        return FileResponse(out, media_type="application/pdf", filename=f"{case_id}.pdf")

    # ------------------------------------------------------------- demo
    @app.post("/v1/demo/scenario/{name}")
    async def demo_scenario(name: str, background: bool = True):
        cur = getattr(app.state, "current", None) or {}
        if name.upper() == "CUSTOM" and cur.get("custom"):  # Restart on the jury's own case
            return await demo_custom(CustomCaseIn(**cur["custom"]), background)
        if name.upper() not in SCENARIOS:
            raise HTTPException(404, f"scenario must be one of {sorted(SCENARIOS)}")
        for t in timers.values():
            t.cancel()
        timers.clear()
        return await _announce(load_scenario(svc, name, with_background=background))

    @app.post("/v1/demo/custom")
    async def demo_custom(body: CustomCaseIn, background: bool = True):
        for t in timers.values():
            t.cancel()
        timers.clear()
        return await _announce(build_custom(svc, body.model_dump(), with_background=background))

    async def _announce(sc: dict) -> dict:
        app.state.current = sc
        await hub.send("demo", {"type": "scenario", "data": sc})
        await hub.send("console", {"type": "reset", "scenario": sc["scenario"]})
        if sc.get("relative"):
            await hub.send(f"device:{sc['relative']['device_id']}", {"type": "reset"})
        return sc

    @app.get("/v1/demo/current")
    def demo_current():
        cur = getattr(app.state, "current", None)
        if not cur:
            raise HTTPException(404, "no scenario loaded yet")
        return cur

    @app.get("/v1/demo/scenarios")
    def demo_list():
        return {k: {"title": v["title"], "pattern": v["pattern"]} for k, v in SCENARIOS.items()}

    @app.post("/v1/demo/fv/{challenge_id}/timeout")
    async def demo_force_timeout(challenge_id: str):
        t = timers.pop(challenge_id, None)
        if t:
            t.cancel()
        case = svc.timeout_challenge(challenge_id)
        if not case:
            raise HTTPException(409, "challenge not pending")
        await publish(case)
        return {"ok": True, "tier": case["tier"]}

    # ------------------------------------------------------------- websockets
    async def _ws(topic: str, ws: WebSocket, hello: dict | None = None):
        await hub.join(topic, ws)
        try:
            if hello:
                await ws.send_text(json.dumps(hello, ensure_ascii=False, default=str))
            while True:
                await ws.receive_text()  # keepalive / ignore
        except WebSocketDisconnect:
            pass
        finally:
            hub.leave(topic, ws)

    @app.websocket("/ws/case/{case_id}")
    async def ws_case(ws: WebSocket, case_id: str):
        c = store.get_case(case_id)
        hello = {"type": "assessment", "case_id": case_id, "data": svc._response(c, time.perf_counter())} if c else None
        await _ws(f"case:{case_id}", ws, hello)

    @app.websocket("/ws/device/{device_id}")
    async def ws_device(ws: WebSocket, device_id: str):
        await _ws(f"device:{device_id}", ws, {"type": "hello", "pending": svc.pending_challenges(device_id)})

    @app.websocket("/ws/console")
    async def ws_console(ws: WebSocket):
        await _ws("console", ws, {"type": "hello"})

    @app.websocket("/ws/demo")
    async def ws_demo(ws: WebSocket):
        await _ws("demo", ws, {"type": "hello"})

    return app


app = create_app() if os.environ.get("PEHCHAAN_NO_AUTOAPP") != "1" else None
