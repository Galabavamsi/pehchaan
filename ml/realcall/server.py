"""Webhook server for Vobiz: answers calls with VobizXML, serves tapes, conducts uplink sessions over WebSocket.

  python -m realcall.server          # listens on 127.0.0.1:<server_port>; expose it with a tunnel (README)

Call IDs are random UUIDs minted by dial.py, so an answer URL only works for a call we registered.
Every webhook is appended to the ledger; nothing else is stored server-side.
"""
import asyncio
import base64
import json
import time
from xml.sax.saxutils import escape

import numpy as np
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response

from common.audio import load, save
from realcall.settings import TAPES, UPLINK, calls, config, ensure_dirs, log_event

app = FastAPI(title="pehchaan-realcall")
SR_UP = 16000


def _base() -> str:
    b = config()["public_base_url"].rstrip("/")
    if not b.startswith("https://"):
        raise HTTPException(500, "public_base_url must be an https tunnel URL")
    return b


def _xml(body: str) -> Response:
    return Response(f'<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n{body}\n</Response>', media_type="application/xml")


async def _form(request: Request) -> dict:
    try:
        f = await request.form()
        d = dict(f)
    except Exception:
        d = {}
    if not d:
        try:
            d = await request.json()
        except Exception:
            d = dict(request.query_params)
    return {k: str(v) for k, v in d.items()}


MAX_EVENTS_PER_CALL = 60   # a real call produces ~10 webhook events; anything beyond is noise or abuse
TAPE_URL_TTL_S = 1800      # a tape can be fetched only while its call is live, at most 30 min after registration


def _call(call_id: str) -> dict:
    """The registered call, or 404. Call IDs are 128-bit random, minted by dial.py; webhooks for anything else are
    rejected before they touch the ledger, and each call's event count is capped so the ledger can't be flooded."""
    c = calls().get(call_id)
    if not c or "kind" not in c:
        raise HTTPException(404, "unknown call")
    if len(c.get("events", [])) >= MAX_EVENTS_PER_CALL:
        raise HTTPException(429, "too many events for this call")
    return c


@app.api_route("/answer/{call_id}", methods=["GET", "POST"])
async def answer(call_id: str, request: Request):
    c = _call(call_id)
    f = await _form(request)
    log_event("answered", call_id=call_id, call_uuid=f.get("CallUUID"), status=f.get("CallStatus"))
    b, cfg = _base(), config()
    rec = (f'<Record recordSession="true" redirect="false" playBeep="false" fileFormat="wav" maxLength="{cfg["call_time_limit_s"]}" '
           f'callbackUrl="{b}/record/{call_id}" callbackMethod="POST"/>') if cfg.get("record_session") else ""
    if c["kind"] == "tape":
        # 6 s before the tape: time for the phone (by hand or realcall.phone) to switch to speaker before the start chirp
        return _xml(f'{rec}\n<Wait length="6"/>\n<Play>{escape(b)}/tape/{call_id}.wav</Play>\n<Wait length="2"/>\n<Hangup/>')
    if c["kind"] == "uplink":
        ws = b.replace("https://", "wss://") + f"/ws/uplink/{call_id}"
        return _xml(f'<Stream bidirectional="true" audioTrack="inbound" contentType="audio/x-l16;rate={SR_UP}" keepCallAlive="true" '
                    f'streamTimeout="{cfg["call_time_limit_s"]}" statusCallbackUrl="{b}/stream/{call_id}">{escape(ws)}</Stream>\n<Hangup/>')
    raise HTTPException(400, f"kind {c['kind']} is not dialled through Vobiz")


@app.api_route("/hangup/{call_id}", methods=["GET", "POST"])
async def hangup(call_id: str, request: Request):
    _call(call_id)
    f = await _form(request)
    log_event("hangup", call_id=call_id, call_uuid=f.get("CallUUID"), cause=f.get("HangupCause") or f.get("HangupCauseName"),
              duration_s=f.get("Duration"), status=f.get("CallStatus"))
    return {"ok": True}


@app.api_route("/ring/{call_id}", methods=["GET", "POST"])
async def ring(call_id: str, request: Request):
    _call(call_id)
    f = await _form(request)
    log_event("ring", call_id=call_id, call_uuid=f.get("CallUUID"))
    return {"ok": True}


@app.api_route("/record/{call_id}", methods=["GET", "POST"])
async def record(call_id: str, request: Request):
    _call(call_id)
    f = await _form(request)
    log_event("recording", call_id=call_id, recording_id=f.get("RecordingID"), url=f.get("RecordFile") or f.get("RecordUrl"),
              duration_ms=f.get("RecordingDurationMs"), reason=f.get("RecordingEndReason"))
    return _xml("")


@app.api_route("/stream/{call_id}", methods=["GET", "POST"])
async def stream_status(call_id: str, request: Request):
    _call(call_id)
    f = await _form(request)
    log_event("stream_status", call_id=call_id, event=f.get("Event"), stream_id=f.get("StreamID"))
    return {"ok": True}


@app.api_route("/tape/{name}", methods=["GET", "HEAD"])
def tape_file(name: str):
    """The 8 kHz playback tape for one registered call, addressed by its unguessable call ID (never by tape ID),
    and only while that call is live. Reference (.ref.wav) files are never served."""
    call_id = name[:-4] if name.endswith(".wav") else ""
    c = calls().get(call_id)
    if not c or c.get("kind") != "tape" or not c.get("tape_id"):
        raise HTTPException(404)
    if "hangup_t" in c or time.time() - c.get("registered_t", 0) > TAPE_URL_TTL_S:
        raise HTTPException(404)
    p = TAPES / f"{c['tape_id']}.wav"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p, media_type="audio/wav")


@app.get("/healthz")
def healthz():
    return {"ok": True, "t": time.time()}


# ---------------------------------------------------------------- uplink conductor

def _tone(freqs, dur=0.25, sr=SR_UP, amp=0.3):
    t = np.arange(int(dur * sr)) / sr
    x = sum(np.sin(2 * np.pi * f * t) for f in freqs) / len(freqs)
    return (amp * x * np.hanning(len(t))).astype(np.float32)


READ_TONE = np.concatenate([_tone([880]), np.zeros(800, np.float32), _tone([1320])])  # "read the next line"
QUIET_TONE = _tone([440], dur=0.6)                                                       # "stay quiet"
END_TONE = np.concatenate([_tone([1320]), _tone([880]), _tone([660])])


def _pcm(x: np.ndarray, big_endian: bool) -> str:
    i = (np.clip(x, -1, 1) * 32767).astype(">i2" if big_endian else "<i2")
    return base64.b64encode(i.tobytes()).decode()


def _guess_big_endian(raw: bytes) -> bool:
    """L16 byte order isn't pinned down in the docs: the right order is the one that isn't white noise."""
    n = len(raw) // 2 * 2
    if n < 3200:
        return False
    def hf(dt):
        x = np.frombuffer(raw[:n], dtype=dt).astype(np.float32)
        return float(np.mean(np.diff(x) ** 2) / (np.mean(x ** 2) + 1e-9))
    return hf(">i2") < hf("<i2")


def _play_local(path: str):
    """Play a clone through the laptop speaker (held near the phone) for replay-through-handset items."""
    import sounddevice as sd
    x = load(path, 48000)
    sd.play(x, 48000)
    return len(x) / 48000


@app.websocket("/ws/uplink/{call_id}")
async def uplink_ws(ws: WebSocket, call_id: str):
    await ws.accept()
    ensure_dirs()
    c = calls().get(call_id)
    if not c or c.get("kind") != "uplink":
        await ws.close()
        return
    plan = c["plan"]                      # [{"type": "read"|"replay", "line_id", "text", "src"?, "generator"?}]
    window = float(c.get("window_s", 9.0))
    stream_id, be, buf = None, None, bytearray()
    windows, step, next_at = [], 0, int(2.0 * SR_UP)   # first prompt 2 s after audio starts
    done_at = None
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            ev = msg.get("event")
            if ev == "start":
                stream_id = msg["start"]["streamId"]
                log_event("stream_start", call_id=call_id, stream_id=stream_id, media=msg["start"].get("mediaFormat"))
            elif ev == "media" and msg.get("media", {}).get("track", "inbound") == "inbound":
                raw = base64.b64decode(msg["media"]["payload"])
                buf.extend(raw)
                if be is None and len(buf) >= 3200:
                    be = _guess_big_endian(bytes(buf))
                pos = len(buf) // 2
                if done_at is None and pos >= next_at and stream_id:
                    if step < len(plan):
                        it = plan[step]
                        tone = READ_TONE if it["type"] == "read" else QUIET_TONE
                        await ws.send_text(json.dumps({"event": "playAudio", "streamId": stream_id,
                                                       "media": {"contentType": "audio/x-l16", "sampleRate": SR_UP,
                                                                 "payload": _pcm(tone, bool(be))}}))
                        start = pos + len(tone)
                        dur = window
                        if it["type"] == "replay":
                            await asyncio.sleep(0.8)
                            dur = max(window, _play_local(it["src"]) + 1.5)
                        windows.append({**it, "step": step, "start_sample": int(start), "end_sample": int(start + dur * SR_UP)})
                        next_at = int(start + dur * SR_UP)
                        step += 1
                    else:
                        await ws.send_text(json.dumps({"event": "playAudio", "streamId": stream_id,
                                                       "media": {"contentType": "audio/x-l16", "sampleRate": SR_UP,
                                                                 "payload": _pcm(END_TONE, bool(be))}}))
                        done_at = pos + int(1.5 * SR_UP)
                if done_at is not None and pos >= done_at:
                    await ws.send_text(json.dumps({"event": "stop", "streamId": stream_id}))
                    break
            elif ev == "stop":
                break
    except WebSocketDisconnect:
        pass
    finally:
        if buf:
            x = np.frombuffer(bytes(buf[: len(buf) // 2 * 2]), dtype=">i2" if be else "<i2").astype(np.float32) / 32768
            out = UPLINK / f"{call_id}.wav"
            save(out, x, SR_UP)
            log_event("uplink_done", call_id=call_id, uplink_wav=str(out), windows=windows, big_endian=bool(be),
                      uplink_s=round(len(x) / SR_UP, 2))


def main():
    import uvicorn
    ensure_dirs()
    uvicorn.run(app, host="127.0.0.1", port=int(config()["server_port"]), log_level="info")


if __name__ == "__main__":
    main()
