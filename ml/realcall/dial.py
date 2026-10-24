"""Place consented calls through Vobiz, one at a time, and wait for each to finish.

  python -m realcall.dial tape --device D2 --n 10              # 10 tape calls to device D2
  python -m realcall.dial uplink --speaker S01 --device D1 --lines 12 --replay 4
  python -m realcall.dial attack --device A --speaker S02 --clip work/src/attack/t1_S02.wav   # live-demo attack call
  python -m realcall.dial check                                # credentials, tunnel, sources; places no call

Only registered devices of consenting participants can be dialled (consent.Registry.dialable).
"""
import argparse
import random
import time
import uuid
from pathlib import Path

import numpy as np
import requests

from common.audio import load, resample, save
from realcall import agent
from realcall.consent import Registry, hash_number
from realcall.dsp import SR
from realcall.settings import ATTACK, UPLINK, calls, config, env, ensure_dirs, log_event
from realcall.tape import _texts, build, index_sources


def _vobiz_call(to: str, call_id: str) -> dict:
    cfg = config()
    if not cfg.get("vobiz_number") or "X" in cfg["vobiz_number"]:
        raise SystemExit("set vobiz_number in realcall/config.yaml")
    aid, tok = env("VOBIZ_AUTH_ID"), env("VOBIZ_AUTH_TOKEN")
    b = cfg["public_base_url"].rstrip("/")
    body = {"from": cfg["vobiz_number"].lstrip("+"), "to": to.lstrip("+"),
            "answer_url": f"{b}/answer/{call_id}", "answer_method": "POST",
            "hangup_url": f"{b}/hangup/{call_id}", "hangup_method": "POST",
            "ring_url": f"{b}/ring/{call_id}", "ring_method": "POST",
            "time_limit": int(cfg["call_time_limit_s"])}
    r = requests.post(f"{cfg['vobiz_api']}/Account/{aid}/Call/", json=body, timeout=20,
                      headers={"X-Auth-ID": aid, "X-Auth-Token": tok, "Content-Type": "application/json"})
    if r.status_code >= 300:
        raise RuntimeError(f"Vobiz {r.status_code}: {r.text[:300]}")
    return r.json()


def _wait_hangup(call_id: str, timeout_s: float) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        c = calls().get(call_id, {})
        if "hangup_t" in c:
            return c
        time.sleep(2)
    print(f"  ! no hangup webhook for {call_id} after {timeout_s:.0f} s (check the server and tunnel)")
    return calls().get(call_id, {})


def _register_and_dial(reg: Registry, kind: str, device: str, **extra) -> dict:
    to = reg.dialable(device)
    d = reg.device(device)
    call_id = uuid.uuid4().hex
    log_event("call_registered", call_id=call_id, kind=kind, device=device, device_hash=hash_number(to),
              carrier=d.get("carrier"), network=d.get("network"), model=d.get("model"), route="cellular", **extra)
    resp = _vobiz_call(to, call_id)
    log_event("call_api", call_id=call_id, request_uuid=resp.get("request_uuid"), message=resp.get("message"))
    return {"call_id": call_id}


def cmd_tape(a, reg):
    serial = None
    if a.auto_answer or a.pull:
        from realcall import phone
        ss = phone.serials()
        if not ss:
            raise SystemExit("--auto-answer/--pull need the phone on USB with debugging allowed")
        serial = ss[0]
        if a.pull and not phone.auto_record_on(serial):
            print("  ! the phone's 'Auto record calls' is OFF: no dialer recordings will be made")
    for i in range(a.n):
        meta = build(reg, a.pairs, speakers=a.speakers)
        th = res = None
        if a.auto_answer:
            import threading
            res = {}
            th = threading.Thread(target=lambda: res.update(phone.answer_and_speaker(serial, ring_timeout=70,
                                                                                    lock_first=a.lock_first)), daemon=True)
            th.start()
        r = _register_and_dial(reg, "tape", a.device, tape_id=meta["tape_id"])
        print(f"[{i + 1}/{a.n}] call {r['call_id'][:8]} tape {meta['tape_id']} ({meta['total_s']:.0f} s): "
              + ("auto-answering" if a.auto_answer else "answer on speakerphone"), flush=True)
        if th:
            th.join(80)
            log_event("phone_auto", call_id=r["call_id"], **res)
            print(f"  phone: {res}", flush=True)
        c = _wait_hangup(r["call_id"], meta["total_s"] + 120)
        print(f"  ended: {c.get('hangup_cause')} after {c.get('duration_s')} s", flush=True)
        if a.pull:
            time.sleep(4)   # the dialer finalises the file after hangup
            print(f"  pulled: {phone.pull(a.device, serial) or 'nothing new'}", flush=True)
        if i + 1 < a.n:
            time.sleep(config()["gap_between_calls_s"])


def cmd_uplink(a, reg):
    reg.require_record(a.speaker)
    texts = {k[1]: v for k, v in _texts().items() if k[0] == a.speaker and v[1] and v[1] != "nan"}
    if not texts:
        raise SystemExit(f"no script lines for {a.speaker} in work/src/team_bona.csv")
    rng = random.Random()
    lines = rng.sample(sorted(texts), min(a.lines, len(texts)))
    plan = [{"type": "read", "line_id": l, "lang": texts[l][0], "text": texts[l][1], "speaker": a.speaker} for l in lines]
    if a.replay:
        clones = [(spk, line, g, p) for (spk, line), v in index_sources(reg).items() for g, p in v["clone"]]
        for spk, line, g, p in rng.sample(clones, min(a.replay, len(clones))):
            reg.require_clone(spk)
            plan.append({"type": "replay", "line_id": line, "speaker": spk, "generator": g, "src": str(p)})
        rng.shuffle(plan)
    ensure_dirs()
    sheet = [f"Pehchaan uplink session, speaker {a.speaker}. Two beeps (low-high) = read the next line. One low beep = stay quiet.", ""]
    n = 0
    for it in plan:
        if it["type"] == "read":
            n += 1
            sheet.append(f"{n:2d}. {it['text']}")
    r = _register_and_dial(reg, "uplink", a.device, speaker=a.speaker, plan=plan, window_s=a.window)
    (UPLINK / f"{r['call_id']}_sheet.txt").write_text("\n".join(sheet), encoding="utf-8")
    print("\n".join(sheet))
    print(f"\ncall {r['call_id'][:8]}: {len(plan)} steps; replay steps play clones from the laptop speaker, hold the phone near it")
    c = _wait_hangup(r["call_id"], len(plan) * (a.window + 6) + 120)
    print(f"ended: {c.get('hangup_cause')} after {c.get('duration_s')} s")


def cmd_attack(a, reg):
    """Live-demo attack call: play one consented clone clip (e.g. the T1 "accident, send ₹50,000" script) to a
    registered device. Demo theatre only: attack calls are never ingested, scored or counted towards the gate."""
    reg.require_clone(a.speaker)
    clip = Path(a.clip)
    if not clip.exists():
        raise SystemExit(f"{clip} not found (make one with: python -m realcall.sarvam_clone --speakers {a.speaker} --say ...)")
    ensure_dirs()
    x = load(clip)
    if a.lead_in:
        x = np.concatenate([np.zeros(int(a.lead_in * SR), np.float32), x])
    to = reg.dialable(a.device)   # fail before anything is written if the device can't be dialled
    for i in range(a.n):
        call_id = uuid.uuid4().hex
        wav = ATTACK / f"{call_id}.wav"
        save(wav, resample(x, SR, 8000), 8000)   # what Vobiz plays (8 kHz mono)
        try:
            d = reg.device(a.device)
            log_event("call_registered", call_id=call_id, kind="attack", device=a.device, device_hash=hash_number(to),
                      carrier=d.get("carrier"), network=d.get("network"), model=d.get("model"), route="cellular",
                      speaker=a.speaker, clip=clip.name, clip_s=round(len(x) / SR, 1))
            resp = _vobiz_call(to, call_id)
            log_event("call_api", call_id=call_id, request_uuid=resp.get("request_uuid"), message=resp.get("message"))
            print(f"[{i + 1}/{a.n}] attack call {call_id[:8]}: {clip.name} ({len(x) / SR:.0f} s) as {a.speaker} -> {a.device}", flush=True)
            c = _wait_hangup(call_id, len(x) / SR + 120)
            print(f"  ended: {c.get('hangup_cause')} after {c.get('duration_s')} s", flush=True)
        finally:
            wav.unlink(missing_ok=True)   # also when Vobiz rejects the call, it times out or the operator interrupts
        if i + 1 < a.n:
            time.sleep(config()["gap_between_calls_s"])


def cmd_agent(a, reg):
    """Conversational live-demo attack call (SPEC §8 V4): the cloned 'son' listens and reacts turn by turn. Demo
    theatre only, like attack: never ingested, scored or counted. Costs money (phone + STT/LLM/TTS each turn)."""
    reg.require_clone(a.speaker)
    to = reg.dialable(a.device)       # fail before anything else if consent/device is wrong
    card = agent.ScriptCard(persona=a.persona, lang=a.lang, min_amount=a.min_amount, max_amount=a.max_amount,
                            upi_id=a.upi, max_turns=a.max_turns)
    if a.lang not in agent.LANG:
        raise SystemExit(f"--lang must be one of {sorted(agent.LANG)}")
    tts = getattr(a, "tts", "sarvam")
    engine = getattr(a, "engine", "xtts")
    gpu_host = getattr(a, "gpu_host", agent.GPU_HOST)
    if tts == "gpu":
        # the GPU clone is validated in `agent dry --tts gpu`; the live two-way call is driven by realcall.server,
        # which builds the Sarvam clone, so a real --tts gpu call needs server._make_agent to read tts/engine too.
        print(f"note: --tts gpu ({engine}) prewarms and records the GPU backend, but realcall.server still drives the "
              f"live call with Sarvam IVC. Drive the agent with the GPU clone via `agent dry --tts gpu`.", flush=True)
    use_fillers = getattr(a, "fillers", False)   # off by default: fillers add audio that the line echoes
                                                  # back, which on some handsets cuts the reply; opt in once tested
    live_providers = None       # the live two-way call is driven by Sarvam IVC (even with --tts gpu); its opener and
    if not a.no_prewarm:        # fillers are rendered here, before the ring, so the son speaks the moment she answers
        if tts == "gpu":
            agent.GpuCloneTTS(engine, a.speaker, reg, card.lang, host=gpu_host).ensure_voice()
        live_tts = agent.SarvamCloneTTS(a.speaker, reg, card.lang)
        live_tts.ensure_voice()                      # fails fast on missing consent/reference
        live_providers = agent.Providers(agent.SarvamSTT(), agent.OpenAILLM(), live_tts)
        if use_fillers:
            agent.FillerBank(a.speaker, "sarvam", card.lang).prepare(live_tts)
            print(f"prepared fillers for {a.speaker} ({card.lang})", flush=True)
    ensure_dirs()
    agent.clear_openers()       # drop any opener left over from an earlier run
    d = reg.device(a.device)
    for i in range(a.n):
        call_id = uuid.uuid4().hex
        if live_providers is not None:
            try:
                plan, _ = agent.render_opener(call_id, card, live_providers)   # LLM + TTS before dialing
                print(f"  opener ready: {plan.text!r}", flush=True)
            except Exception as e:  # fall back to the server rendering it on answer
                print(f"  opener prerender skipped ({e!r})", flush=True)
        log_event("call_registered", call_id=call_id, kind="agent", device=a.device, device_hash=hash_number(to),
                  carrier=d.get("carrier"), network=d.get("network"), model=d.get("model"), route="cellular",
                  speaker=a.speaker, card=card.as_dict(), stt=a.stt, llm=a.llm, vad=a.vad, tts=tts, engine=engine,
                  fillers=use_fillers)
        resp = _vobiz_call(to, call_id)
        log_event("call_api", call_id=call_id, request_uuid=resp.get("request_uuid"), message=resp.get("message"))
        print(f"[{i + 1}/{a.n}] agent call {call_id[:8]} as {a.speaker} -> {a.device}: cloned son, up to {a.max_turns} "
              f"turns (watch the server log for the live transcript)", flush=True)
        c = _wait_hangup(call_id, a.max_turns * 30 + 120)
        agent.take_opener(call_id)      # delete this call's opener if it never connected / was already used
        print(f"  ended: {c.get('hangup_cause')} after {c.get('duration_s')} s", flush=True)
        if i + 1 < a.n:
            time.sleep(config()["gap_between_calls_s"])


def cmd_check(a, reg):
    cfg = config()
    print("vobiz_number:", "set" if cfg.get("vobiz_number") and "X" not in cfg["vobiz_number"] else "MISSING")
    for k in ("VOBIZ_AUTH_ID", "VOBIZ_AUTH_TOKEN", "SARVAM_API_KEY"):
        print(f"{k}:", "set" if env(k, required=False) else "MISSING")
    b = cfg.get("public_base_url", "")
    try:
        ok = requests.get(b.rstrip("/") + "/healthz", timeout=8).ok
    except Exception:
        ok = False
    print("tunnel -> server:", "ok" if ok else f"NOT reachable ({b or 'unset'})")
    for did in reg.devices:
        try:
            reg.dialable(did)
            print(f"device {did}: dialable")
        except PermissionError as e:
            print(f"device {did}: {e}")
    idx = index_sources(reg)
    print("tape sources:", sum(1 for v in idx.values() if v["genuine"] and v["clone"]), "lines with genuine + clone")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tape")
    t.add_argument("--device", required=True)
    t.add_argument("--n", type=int, default=1)
    t.add_argument("--pairs", type=int, default=5)
    t.add_argument("--speakers", nargs="*")
    t.add_argument("--auto-answer", action="store_true", help="answer each call and turn on speaker over adb")
    t.add_argument("--lock-first", action="store_true",
                   help="with --auto-answer: lock the screen before each ring (Redmi/MIUI needs the full-screen call UI)")
    t.add_argument("--pull", action="store_true", help="copy the phone's dialer recording after each call over adb")
    u = sub.add_parser("uplink")
    u.add_argument("--speaker", required=True)
    u.add_argument("--device", required=True)
    u.add_argument("--lines", type=int, default=12)
    u.add_argument("--replay", type=int, default=0)
    u.add_argument("--window", type=float, default=9.0)
    k = sub.add_parser("attack", help="live demo: play one consented clone clip to a device")
    k.add_argument("--device", required=True)
    k.add_argument("--speaker", required=True, help="whose cloned voice the clip is (needs clone consent)")
    k.add_argument("--clip", required=True)
    k.add_argument("--n", type=int, default=1)
    k.add_argument("--lead-in", type=float, default=1.5, help="seconds of silence after answer before the voice")
    g = sub.add_parser("agent", help="live demo: a two-way cloned 'son' that reacts to what the mother says")
    g.add_argument("--device", required=True)
    g.add_argument("--speaker", required=True, help="whose cloned voice the son uses (needs clone consent)")
    g.add_argument("--lang", default="hi")
    g.add_argument("--persona", default="Rahul", help="fictional name the son claims")
    g.add_argument("--upi", default="rahul.friend@okfinbank", help="fictional UPI ID he asks money be sent to")
    g.add_argument("--min-amount", type=int, default=2000)
    g.add_argument("--max-amount", type=int, default=50000)
    g.add_argument("--max-turns", type=int, default=8)
    g.add_argument("--n", type=int, default=1)
    g.add_argument("--stt", default="sarvam", choices=["sarvam", "deepgram"])
    g.add_argument("--llm", default="openai", choices=["openai"])
    g.add_argument("--tts", default="sarvam", choices=["sarvam", "gpu"],
                   help="sarvam = Sarvam IVC (default, live-call path); gpu = offline neural clone on the GPU box")
    g.add_argument("--engine", default="xtts", choices=list(agent.GPU_ENGINES), help="offline engine with --tts gpu")
    g.add_argument("--gpu-host", default=agent.GPU_HOST, help="serve_clone_tts.py over the SSH tunnel (--tts gpu)")
    g.add_argument("--vad", default="energy", choices=["energy", "silero"])
    g.add_argument("--no-prewarm", action="store_true", help="don't resolve the clone voice before dialing")
    g.add_argument("--fillers", action="store_true",
                   help="play short filler sounds while the reply is synthesised (off by default: the line echo can cut the reply)")
    sub.add_parser("check")
    a = ap.parse_args()
    reg = Registry()
    {"tape": cmd_tape, "uplink": cmd_uplink, "attack": cmd_attack, "agent": cmd_agent,
     "check": cmd_check}[a.cmd](a, reg)


if __name__ == "__main__":
    main()
