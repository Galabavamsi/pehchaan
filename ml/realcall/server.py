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
from realcall.consent import Registry
from realcall.settings import ATTACK, TAPES, UPLINK, calls, config, ensure_dirs, log_event
from realcall import agent

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
    if c["kind"] == "attack":
        # demo theatre: never recorded, whatever record_session says
        return _xml(f'<Play>{escape(b)}/attack/{call_id}.wav</Play>\n<Wait length="1"/>\n<Hangup/>')
    if c["kind"] == "agent":
        # conversational live-demo attacker (SPEC §8 V4): a two-way media stream, never recorded (demo theatre)
        ws = b.replace("https://", "wss://") + f"/ws/agent/{call_id}"
        return _xml(f'<Stream bidirectional="true" audioTrack="inbound" contentType="audio/x-l16;rate={SR_UP}" keepCallAlive="true" '
                    f'streamTimeout="{cfg["call_time_limit_s"]}" statusCallbackUrl="{b}/stream/{call_id}">{escape(ws)}</Stream>\n<Hangup/>')
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


@app.api_route("/attack/{name}", methods=["GET", "HEAD"])
def attack_file(name: str):
    """The clone clip for one live-demo attack call, by its unguessable call ID, only while that call is live."""
    call_id = name[:-4] if name.endswith(".wav") else ""
    c = calls().get(call_id)
    if not c or c.get("kind") != "attack":
        raise HTTPException(404)
    if "hangup_t" in c or time.time() - c.get("registered_t", 0) > TAPE_URL_TTL_S:
        raise HTTPException(404)
    p = ATTACK / f"{call_id}.wav"
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


# ---------------------------------------------------------------- conversational agent (SPEC §8 V4)

def _make_agent(c: dict):
    """(providers, vad, card) for one agent call. Tests monkeypatch this to inject FakeSTT/FakeLLM/FakeTTS."""
    card = agent.ScriptCard(**(c.get("card") or {}))
    providers = agent.build_providers(card, c.get("speaker"), Registry(),
                                      stt=c.get("stt", "sarvam"), llm=c.get("llm", "openai"))
    return providers, agent.make_vad(c.get("vad", "energy"), sr=SR_UP), card


async def _stream_out(send, audio, be, stream_id, barged, stopped, sr=SR_UP, chunk_s=0.1) -> bool:
    """Send one spoken line as paced playAudio frames, flushing with clearAudio the moment she barges in. Paced so
    Vobiz never buffers more than a chunk ahead, which is what makes barge-in feel instant. Returns True if the whole
    line played, False if it was cut short."""
    step = int(chunk_s * sr)
    for i in range(0, len(audio), step):
        if stopped():
            return False
        if barged():
            await send({"event": "clearAudio", "streamId": stream_id})
            return False
        chunk = audio[i:i + step]
        await send({"event": "playAudio", "streamId": stream_id,
                    "media": {"contentType": "audio/x-l16", "sampleRate": sr, "payload": _pcm(chunk, bool(be))}})
        await asyncio.sleep(len(chunk) / sr)
    return True


@app.websocket("/ws/agent/{call_id}")
async def agent_ws(ws: WebSocket, call_id: str):
    await ws.accept()
    ensure_dirs()
    c = calls().get(call_id)
    if not c or c.get("kind") != "agent":
        await ws.close()
        return
    try:
        providers, vad, card = _make_agent(c)
        conv = agent.AgentConversation(card, providers)
    except Exception as exc:                                  # bad card, missing consent/voice, missing key
        log_event("agent_error", call_id=call_id, error=repr(exc)[:200])
        await ws.close()
        return

    fillers = None                                            # "still here" sounds while a reply is synthesised
    if c.get("fillers", False):   # opt-in (dial --fillers); the line echo can otherwise cut the reply
        try:
            kind = "gpu" if c.get("tts") == "gpu" else "sarvam"
            bank = agent.FillerBank(c.get("speaker") or "", kind, card.lang).load()
            fillers = bank if bank.audios else None
        except Exception:
            fillers = None

    loop = asyncio.get_event_loop()
    utt_q: asyncio.Queue = asyncio.Queue()
    started, barge = asyncio.Event(), asyncio.Event()
    st = {"stream_id": None, "be": None, "speaking": False, "stop": False, "turns": 0}

    async def send(obj):
        await ws.send_text(json.dumps(obj))

    async def recv():
        buf = bytearray()
        try:
            while not st["stop"]:
                msg = json.loads(await ws.receive_text())
                ev = msg.get("event")
                if ev == "start":
                    st["stream_id"] = msg["start"]["streamId"]
                    started.set()
                    log_event("stream_start", call_id=call_id, stream_id=st["stream_id"])
                elif ev == "media" and msg.get("media", {}).get("track", "inbound") == "inbound":
                    raw = base64.b64decode(msg["media"]["payload"])
                    buf.extend(raw)
                    if st["be"] is None and len(buf) >= 3200:
                        st["be"] = _guess_big_endian(bytes(buf))
                    n = len(raw) // 2 * 2
                    frame = np.frombuffer(raw[:n], dtype=">i2" if st["be"] else "<i2").astype(np.float32) / 32768
                    for kind, utt in vad.push(frame):
                        if kind == "start" and st["speaking"]:
                            barge.set()                       # she started talking over the son -> cut him off
                        elif kind == "end":
                            utt_q.put_nowait(utt)
                elif ev == "stop":
                    break
        except (WebSocketDisconnect, RuntimeError, KeyError):
            pass
        finally:
            st["stop"] = True
            started.set()
            utt_q.put_nowait(None)

    def _drain(fut):                                          # retrieve an abandoned synth future's result/exception
        fut.add_done_callback(lambda f: f.cancelled() or f.exception())

    async def speak(audio, cut=True):
        """Stream one line. cut=False plays it through even if barge is set, so the reply's first sentence is never
        swallowed by the line echoing back (which otherwise trips barge and cuts chunk 0)."""
        st["speaking"] = True
        barge.clear()
        ok = await _stream_out(send, audio, st["be"], st["stream_id"], (lambda: False) if not cut else barge.is_set,
                               lambda: st["stop"])
        st["speaking"] = False
        return ok

    async def speak_reply(plan):
        """Speak a reply sentence by sentence, synthesising the next while the current one plays; barge-in or hangup
        drops the rest. Returns (text actually spoken, time the first frame went out)."""
        sents = agent.split_sentences(plan.text) or [plan.text]
        spoken, t_first = [], None
        audio = await loop.run_in_executor(None, conv.voice, sents[0], plan.emotion)
        for i, s in enumerate(sents):
            if st["stop"]:
                break
            nxt = (loop.run_in_executor(None, conv.voice, sents[i + 1], plan.emotion)
                   if i + 1 < len(sents) else None)
            if t_first is None:
                t_first = time.perf_counter()
            ok = await speak(audio, cut=i > 0)        # first sentence always plays; echo can't swallow the reply
            if not ok:                                # genuine barge-in on a later sentence: drop the rest
                if nxt is not None:
                    _drain(nxt)
                break
            spoken.append(s)
            if nxt is not None:
                audio = await nxt
        return " ".join(spoken), t_first

    async def do_turn(utt):
        """One of her turns. Transcribe first and only reply if she actually said something: line noise and the echo
        tail of the agent's own voice transcribe to nothing, and replying to those is what made the call babble. A
        skipped turn returns None (no LLM, no TTS, not counted)."""
        t0 = time.perf_counter()
        text = await loop.run_in_executor(None, conv.transcribe, utt, agent.SR_UP)
        stt_ms = agent._ms(t0, time.perf_counter())
        if len(text.strip()) < 2:                 # nothing was said -> don't answer, don't burn a turn
            log_event("agent_skip", call_id=call_id, stt_ms=stt_ms, utt_s=round(len(utt) / agent.SR_UP, 2),
                      chars=len(text.strip()))    # metadata only, so a test call shows what was skipped
            return None
        t1 = time.perf_counter()
        fut = loop.run_in_executor(None, conv.plan, text)
        filler, t_first = False, None
        done, _ = await asyncio.wait({fut}, timeout=agent.FILLER_AFTER_S)
        if not done and fillers is not None and not st["stop"]:
            fa = fillers.next()
            if fa is not None:
                filler, t_first = True, time.perf_counter()
                await speak(fa)
        plan = await fut
        llm_ms = agent._ms(t1, time.perf_counter())
        reply_ms = agent._ms(t0, time.perf_counter())
        spoken, t_reply = await speak_reply(plan)
        conv.record(text, spoken)
        if t_first is None:
            t_first = t_reply
        return plan, dict(stt_ms=stt_ms, llm_ms=llm_ms, reply_ms=reply_ms, filler=filler,
                          first_sound_ms=agent._ms(t0, t_first) if t_first else reply_ms,
                          mother_chars=len(text), son_chars=len(spoken))

    async def warm_providers():
        """Open the STT/LLM/TTS connections (and load their models) while the opener plays, so the first real turn
        isn't a cold start. The opener itself is pre-rendered, so nothing in this process is warm until now."""
        for p in (providers.stt, providers.llm, providers.tts):
            w = getattr(p, "warm", None)
            if w and not st["stop"]:
                try:
                    await loop.run_in_executor(None, w)
                except Exception:
                    pass

    async def brain():
        await started.wait()
        asyncio.create_task(warm_providers())            # fire-and-forget; it swallows its own errors
        if st["stop"]:
            return
        t0 = time.perf_counter()
        op = await loop.run_in_executor(None, agent.take_opener, call_id)     # rendered before the ring, if present
        if op is not None:
            plan, audio = op
            conv.use_opener(plan)
            llm_ms = 0
        else:
            plan, audio, ot = await loop.run_in_executor(None, conv.open)
            llm_ms = ot["llm_ms"]
        t_first = time.perf_counter()
        await speak(audio, cut=False)                                                    # opener is one pre-synthesised blob
        log_event("agent_turn", call_id=call_id, step=0, emotion=plan.emotion, done=plan.done, prerendered=op is not None,
                  stt_ms=0, llm_ms=llm_ms, reply_ms=agent._ms(t0, t_first), first_sound_ms=agent._ms(t0, t_first), filler=False,
                  mother_chars=0, son_chars=len(plan.text))
        print(f"[agent {call_id[:8]}] son ({plan.emotion}): {plan.text}", flush=True)
        while not st["stop"] and st["turns"] < card.max_turns:
            utt = await utt_q.get()
            if utt is None:
                break
            if len(utt) / agent.SR_UP < 0.3:                                  # too short to be a real turn
                continue
            result = await do_turn(utt)
            if result is None:                                                # noise / echo, nothing said: wait
                continue
            st["turns"] += 1
            plan, t = result
            log_event("agent_turn", call_id=call_id, step=st["turns"], emotion=plan.emotion, done=plan.done, **t)
            print(f"[agent {call_id[:8]}] mother: {conv.last_mother!r} -> son ({plan.emotion}): {plan.text}", flush=True)
            if plan.done:
                break
        st["stop"] = True
        try:
            await send({"event": "stop", "streamId": st["stream_id"]})
        except Exception:
            pass

    recv_task = asyncio.create_task(recv())
    try:
        await brain()
    finally:
        st["stop"] = True
        recv_task.cancel()
        try:
            await recv_task
        except (asyncio.CancelledError, Exception):
            pass
        log_event("agent_done", call_id=call_id, turns=st["turns"])


def main():
    import uvicorn
    ensure_dirs()
    uvicorn.run(app, host="127.0.0.1", port=int(config()["server_port"]), log_level="info")


if __name__ == "__main__":
    main()
