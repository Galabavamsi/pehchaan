"""Offline end-to-end test: synthetic 'speech' through a simulated phone + speakerphone path, then ingest and gate.

  cd ml && python -m pytest -q realcall/tests
No network, no phone, no real voices: sources are synthetic harmonic signals.
"""
import base64
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pytest

TMP = Path(tempfile.mkdtemp(prefix="realcall_test_"))
os.environ["REALCALL_WORK"] = str(TMP / "work")
os.environ["REALCALL_PARTICIPANTS"] = str(TMP / "participants.yaml")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

EV = (TMP / "ev.png").as_posix()
(TMP / "ev.png").write_bytes(b"x")
(TMP / "participants.yaml").write_text(f"""
participants:
  S01: {{consent: {{record: true, clone: true, evidence: {EV}, expires: 2099-12-31}}}}
  S02: {{consent: {{record: true, clone: true, evidence: {EV}, expires: 2099-12-31}}}}
  V01: {{consent: {{record: true, clone: false, evidence: {EV}, expires: 2099-12-31}}}}
  V09: {{consent: {{record: true, clone: false, evidence: {EV}, expires: 2000-01-01}}}}
  V0: {{consent: {{record: true, clone: true, evidence: data/raw/consent/nope.png}}}}
devices:
  D1: {{owner: S01, phone: "+919000000001", carrier: jio, network: volte}}
  D2: {{owner: S02, phone: "+919000000002", carrier: airtel, network: volte}}
  DX: {{owner: V01, phone: "+91XXXXXXXXXX"}}
""")

from common.audio import save as _save  # noqa: E402
from realcall import ingest, settings  # noqa: E402
from realcall.consent import Registry  # noqa: E402
from realcall.dsp import SR, bandpass, find_chirps, vad_regions  # noqa: E402
from realcall.tape import build, load_tape  # noqa: E402

RNG = np.random.default_rng(0)


def save(path, x, sr):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    _save(path, x, sr)


def fake_speech(dur, f0, seed):
    r = np.random.default_rng(seed)
    t = np.arange(int(dur * SR)) / SR
    f = f0 * (1 + 0.08 * np.sin(2 * np.pi * 0.7 * t + r.uniform(0, 6)))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = sum(np.sin(k * ph) / k for k in range(1, 12))
    env = np.clip(np.sin(2 * np.pi * 3.5 * t + r.uniform(0, 6)), 0, None) ** 0.7   # syllables
    return (0.2 * x * env + 0.002 * r.standard_normal(len(t))).astype(np.float32)


def phone_path(x, drift=1.0015, delay_s=3.3, noise_db=-48):
    """Narrowband + mu-law + loudspeaker->mic IR + drift + room noise: a crude stand-in for a real call."""
    from scipy.signal import resample_poly, fftconvolve
    y = bandpass(x, SR)
    y8 = resample_poly(y, 1, 2)
    mu = np.sign(y8) * np.log1p(255 * np.abs(np.clip(y8, -1, 1))) / np.log1p(255)
    mu = np.round(mu * 127) / 127
    y8 = np.sign(mu) * ((1 + 255) ** np.abs(mu) - 1) / 255
    y = resample_poly(y8, 2, 1)
    ir = np.exp(-np.arange(int(0.05 * SR)) / (0.008 * SR)) * RNG.standard_normal(int(0.05 * SR)) * 0.3
    ir[0] = 1.0
    y = fftconvolve(y, ir)[: len(y)]
    n = int(len(y) * drift)
    y = np.interp(np.linspace(0, len(y) - 1, n), np.arange(len(y)), y)
    y = np.concatenate([np.zeros(int(delay_s * SR)), 0.6 * y, np.zeros(SR * 2)])
    return (y + 10 ** (noise_db / 20) * RNG.standard_normal(len(y))).astype(np.float32)


@pytest.fixture(scope="module")
def sources():
    src = settings.SRC
    for spk, f0 in (("S01", 120), ("S02", 180)):
        for i in range(1, 7):
            line = f"E{i:02d}"
            save(src / "genuine" / spk / f"team_{spk}_{line}.wav", fake_speech(3 + i * 0.4, f0, hash((spk, i)) % 999), SR)
            for g in ("xtts", "seedvc"):
                save(src / "clone" / g / f"{g}__{spk}__{line}.wav", fake_speech(3 + i * 0.3, f0 * 1.05, hash((g, spk, i)) % 999), SR)
    # a speaker without clone consent must never reach a tape
    save(src / "genuine" / "V01" / "team_V01_E01.wav", fake_speech(3, 150, 7), SR)
    save(src / "clone" / "xtts" / "xtts__V01__E01.wav", fake_speech(3, 150, 8), SR)
    return src


def test_consent_guards():
    reg = Registry()
    assert reg.dialable("D1") == "+919000000001"
    with pytest.raises(PermissionError):
        reg.dialable("DX")          # placeholder number
    with pytest.raises(PermissionError):
        reg.dialable("NOPE")
    with pytest.raises(PermissionError):
        reg.require_clone("V01")
    with pytest.raises(PermissionError):
        reg.require_record("V09")   # expired
    with pytest.raises(PermissionError):
        reg.require_record("V0")    # no evidence file


def test_tape_and_ingest_alignment(sources):
    reg = Registry()
    meta = build(reg, n_pairs=6, seed=1)
    assert {it["speaker"] for it in meta["items"]} <= {"S01", "S02"}
    labs = [it["label"] for it in meta["items"]]
    assert labs.count("bonafide") == labs.count("spoof") == 6
    from common.audio import load
    ref = load(settings.TAPES / f"{meta['tape_id']}.ref.wav")
    assert len(find_chirps(ref)) == 2

    cap = phone_path(ref)
    t_ans = time.time() - 600
    session = settings.CAPTURE / f"session_D2_{int(t_ans - 10)}"
    save(str(session) + ".wav", np.concatenate([np.zeros(10 * SR, np.float32), cap]), SR)
    Path(str(session) + ".json").write_text(json.dumps({"start_epoch": t_ans - 10, "sr": SR, "device": "D2"}))
    cid = "a" * 32
    settings.log_event("call_registered", call_id=cid, kind="tape", tape_id=meta["tape_id"], device="D2", route="cellular")
    settings.log_event("answered", call_id=cid)
    led = settings.read_ledger()
    for e in led:                      # back-date to match the synthetic session
        if e.get("call_id") == cid:
            e["t"] = t_ans
    settings.LEDGER.write_text("\n".join(json.dumps(e) for e in led) + "\n")
    settings.log_event("hangup", call_id=cid, cause="NORMAL_CLEARING", duration_s=meta["total_s"])
    led = settings.read_ledger()
    led[-1]["t"] = t_ans + len(cap) / SR
    settings.LEDGER.write_text("\n".join(json.dumps(e) for e in led) + "\n")

    df = ingest.main()
    t = df[df.call_id == cid]
    assert len(t) == 12 and (t.qc == "ok").all(), t[["qc", "ncc", "snr_db", "speech_s"]]
    assert (t["align"] == "two_chirps").all()
    assert abs(t["drift"].iloc[0] - 1.0015) < 0.001
    # every cut lands on its item: capture window starts 5 s into the session; item truth = 10 + 3.3 + start*drift
    truth = {it["idx"]: 10 + 3.3 + it["start_s"] * 1.0015 - 5 for it in meta["items"]}
    err = np.array([abs(r.pos_s - truth[int(r.utt_id[-2:])]) for r in t.itertuples()])
    assert err.max() < 0.03, err
    assert t["ncc"].min() > 0.5


def test_live_ingest_gate_window():
    x = np.concatenate([np.zeros(SR * 2, np.float32), fake_speech(25, 140, 3), np.zeros(SR, np.float32)])
    p = settings.CAPTURE / "live_test.wav"
    save(p, phone_path(x, drift=1.0, delay_s=0.5), SR)
    settings.log_event("live_call", call_id="b" * 32, kind="live", device="D1", route="whatsapp", caller="V01",
                       speaker="V01", lang="hi", file=str(p), answered_t=time.time(), capture="laptop_mic")
    df = ingest.main()
    lv = df[df.call_id == "b" * 32]
    gw = lv[lv.gate_window == True]  # noqa: E712
    assert len(gw) == 1 and gw.qc.iloc[0] == "ok"
    assert (lv[lv.gate_window == False].dur_s.between(4, 10.01)).all()  # noqa: E712
    assert lv.split.nunique() == 1   # one caller -> one split


def test_server_answer_and_uplink_ws(sources):
    from fastapi.testclient import TestClient
    from realcall import server
    settings_cfg = {**settings.DEFAULTS, "public_base_url": "https://example.trycloudflare.com"}
    server.config = lambda: settings_cfg
    cl = TestClient(server.app)
    meta = load_tape(sorted(settings.TAPES.glob("*.json"))[0].stem)
    settings.log_event("call_registered", call_id="c" * 32, kind="tape", tape_id=meta["tape_id"], device="D2")
    r = cl.post("/answer/" + "c" * 32, data={"CallUUID": "u1"})
    assert r.status_code == 200 and f"/tape/{'c' * 32}.wav</Play>" in r.text and "recordSession" in r.text
    assert cl.post("/answer/" + "z" * 32).status_code == 404
    # tapes: only by the live call's ID, never by tape ID, never the .ref reference
    assert cl.get(f"/tape/{'c' * 32}.wav").status_code == 200
    assert cl.get(f"/tapes/{meta['tape_id']}.wav").status_code == 404
    assert cl.get(f"/tape/{meta['tape_id']}.ref.wav").status_code == 404
    assert cl.get("/tape/..%2Fledger.jsonl").status_code == 404
    # webhooks for unregistered calls never reach the ledger
    n0 = len(settings.read_ledger())
    for route in ("hangup", "ring", "record", "stream"):
        assert cl.post(f"/{route}/" + "y" * 32, data={"CallUUID": "x"}).status_code == 404
    assert len(settings.read_ledger()) == n0
    # once the call has hung up its tape URL stops working
    cl.post("/hangup/" + "c" * 32, data={"CallUUID": "u1", "HangupCause": "NORMAL_CLEARING"})
    assert cl.get(f"/tape/{'c' * 32}.wav").status_code == 404

    plan = [{"type": "read", "line_id": "E01", "text": "one", "speaker": "S01"},
            {"type": "read", "line_id": "E02", "text": "two", "speaker": "S01"}]
    cid = "d" * 32
    settings.log_event("call_registered", call_id=cid, kind="uplink", device="D1", speaker="S01", plan=plan, window_s=3.0)
    r = cl.post("/answer/" + cid)
    assert "<Stream" in r.text and 'contentType="audio/x-l16;rate=16000"' in r.text
    speech = fake_speech(9.5, 120, 5)   # prompts at ~2 s and ~5.5 s, end tone at ~9 s, then the caller side stops
    with cl.websocket_connect(f"/ws/uplink/{cid}") as ws:
        ws.send_text(json.dumps({"event": "start", "start": {"streamId": "s1", "mediaFormat": {"encoding": "audio/x-l16", "sampleRate": 16000}}}))
        for i in range(0, len(speech), 320):           # 20 ms frames, little-endian
            pcm = (speech[i:i + 320] * 32767).astype("<i2").tobytes()
            ws.send_text(json.dumps({"event": "media", "media": {"track": "inbound", "payload": base64.b64encode(pcm).decode()}}))
        prompts = [ws.receive_json() for _ in range(3)]
        ws.send_text(json.dumps({"event": "stop"}))
    assert [p["event"] for p in prompts] == ["playAudio"] * 3
    for _ in range(50):
        if settings.calls()[cid].get("uplink_wav"):
            break
        time.sleep(0.1)
    c = settings.calls()[cid]
    assert c.get("uplink_wav") and len(c["windows"]) == 2 and c["big_endian"] is False
    df = ingest.main()
    up = df[df.call_id == cid]
    assert len(up) == 2 and set(up.label) == {"bonafide"}


def test_attack_call_plays_clip_only_while_live(monkeypatch):
    from fastapi.testclient import TestClient
    from realcall import dial, server
    server.config = lambda: {**settings.DEFAULTS, "public_base_url": "https://example.trycloudflare.com"}
    monkeypatch.setattr(dial, "_tunnel_ok", lambda: True)          # offline test: pretend the tunnel is up
    cl = TestClient(server.app)
    clip = TMP / "t1_S02.wav"
    save(clip, fake_speech(4, 180, 11), SR)
    dialled = []

    def fake_vobiz(to, call_id):
        # Vobiz fetches the answer XML and the clip while the call is live
        r = cl.post(f"/answer/{call_id}", data={"CallUUID": "a1"})
        assert f"/attack/{call_id}.wav</Play>" in r.text and "recordSession" not in r.text
        assert cl.get(f"/attack/{call_id}.wav").status_code == 200
        assert cl.get(f"/tape/{call_id}.wav").status_code == 404
        cl.post(f"/hangup/{call_id}", data={"CallUUID": "a1", "HangupCause": "NORMAL_CLEARING"})
        dialled.append((to, call_id))
        return {"request_uuid": "r1"}

    monkeypatch.setattr(dial, "_vobiz_call", fake_vobiz)
    a = type("A", (), dict(device="D1", speaker="S02", clip=str(clip), n=1, lead_in=1.0))
    dial.cmd_attack(a, Registry())
    (to, cid), = dialled
    assert to == "+919000000001" and settings.calls()[cid]["kind"] == "attack"
    assert cl.get(f"/attack/{cid}.wav").status_code == 404        # hung up: clip gone
    assert not (settings.ATTACK / f"{cid}.wav").exists()
    with pytest.raises(PermissionError):                            # no clone consent, no attack call
        dial.cmd_attack(type("A", (), dict(device="D1", speaker="V01", clip=str(clip), n=1, lead_in=0)), Registry())

    def vobiz_rejects(to, call_id):
        raise RuntimeError("Vobiz 400: rejected")
    monkeypatch.setattr(dial, "_vobiz_call", vobiz_rejects)
    with pytest.raises(RuntimeError):                               # a failed call leaves no playback copy behind
        dial.cmd_attack(a, Registry())
    assert not list(settings.ATTACK.glob("*.wav"))
    assert cid not in set(ingest.main().call_id)                    # demo calls never enter the datasets


def _fake_agent_setup(max_turns=1):
    from realcall import agent
    return (agent.Providers(agent.FakeSTT(), agent.FakeLLM(), agent.FakeTTS()),
            agent.make_vad("energy", sr=agent.SR_UP), agent.ScriptCard(max_turns=max_turns))


def _ingested_ids():
    df = ingest.main()
    return set(df["call_id"]) if "call_id" in df.columns else set()


def test_agent_conversation_reactive_metered_and_silent():
    """The son opens, then reacts turn by turn; distinct replies prove reactivity; every turn carries latency and
    length metadata; nothing is written to disk (never recorded)."""
    from realcall import agent
    card = agent.ScriptCard(max_turns=3)
    conv = agent.AgentConversation(card, agent.Providers(agent.FakeSTT(), agent.FakeLLM(), agent.FakeTTS()))
    plan, audio, t = conv.open()
    assert plan.emotion in agent.EMOTIONS and len(audio) > 0 and t["stt_ms"] == 0 and set(t) == {
        "stt_ms", "llm_ms", "tts_ms", "total_ms", "mother_chars", "son_chars"}
    lines, done = [], False
    for _ in range(3):
        plan, audio, t = conv.respond(np.zeros(agent.SR_UP, np.float32), agent.SR_UP)
        assert plan.emotion in agent.EMOTIONS and t["mother_chars"] > 0 and len(audio) > 0
        lines.append(plan.text)
        if plan.done:
            done = True
            break
    assert len(set(lines)) >= 2 and done                       # reacts differently, and ends the call


def test_agent_stream_out_bargein():
    """Paced playback finishes when uninterrupted, and flushes with clearAudio the instant she barges in."""
    import asyncio
    from realcall import agent, server
    sent = []

    async def send(o):
        sent.append(o)

    audio = np.zeros(int(0.5 * agent.SR_UP), np.float32)
    assert asyncio.run(server._stream_out(send, audio, False, "s1", lambda: False, lambda: False)) is True
    assert sent and all(o["event"] == "playAudio" for o in sent)

    sent.clear()
    fired = {"n": 0}

    def barged():
        fired["n"] += 1
        return fired["n"] > 2                                  # barge in after two chunks have gone out
    assert asyncio.run(server._stream_out(send, audio, False, "s1", barged, lambda: False)) is False
    assert sent[-1]["event"] == "clearAudio" and any(o["event"] == "playAudio" for o in sent[:-1])


def test_agent_server_answer_ws_and_never_recorded(monkeypatch):
    from fastapi.testclient import TestClient
    from realcall import agent, server
    server.config = lambda: {**settings.DEFAULTS, "public_base_url": "https://example.trycloudflare.com"}
    monkeypatch.setattr(server, "_make_agent", lambda c: _fake_agent_setup(max_turns=1))
    cl = TestClient(server.app)
    cid = "e" * 32
    settings.log_event("call_registered", call_id=cid, kind="agent", device="D1", speaker="S02",
                       card=agent.ScriptCard().as_dict())
    # answer XML: a two-way stream to the agent websocket, and never a Record (demo theatre)
    r = cl.post(f"/answer/{cid}")
    assert "<Stream" in r.text and f"/ws/agent/{cid}" in r.text and "recordSession" not in r.text

    speech = fake_speech(1.1, 150, 5)
    with cl.websocket_connect(f"/ws/agent/{cid}") as ws:
        ws.send_text(json.dumps({"event": "start", "start": {"streamId": "s1"}}))
        inbound = np.concatenate([np.zeros(int(0.6 * SR), np.float32), speech, np.zeros(int(0.9 * SR), np.float32)])
        for i in range(0, len(inbound) // 320 * 320, 320):     # 20 ms L16 frames, little-endian
            pcm = (inbound[i:i + 320] * 32767).astype("<i2").tobytes()
            ws.send_text(json.dumps({"event": "media", "media": {"track": "inbound", "payload": base64.b64encode(pcm).decode()}}))
        events = []
        for _ in range(400):
            m = ws.receive_json()
            events.append(m["event"])
            if m["event"] == "stop":
                break
    assert events.count("playAudio") >= 2 and "stop" in events       # the son's opening line, then a reply

    turns = [e for e in settings.read_ledger() if e.get("ev") == "agent_turn" and e.get("call_id") == cid]
    steps = sorted(e["step"] for e in turns)
    assert steps[:2] == [0, 1] and all(e["emotion"] in agent.EMOTIONS for e in turns)
    assert all("text" not in e and "transcript" not in e for e in turns)   # metadata only, no content persisted
    assert not (settings.UPLINK / f"{cid}.wav").exists() and not (settings.SEGMENTS / cid).exists()
    assert cid not in _ingested_ids()                                      # agent calls never enter the datasets


def test_agent_dial_registers_card_and_enforces_consent(monkeypatch):
    from realcall import dial, server
    server.config = lambda: {**settings.DEFAULTS, "public_base_url": "https://example.trycloudflare.com"}
    monkeypatch.setattr(dial, "_tunnel_ok", lambda: True)          # offline test: pretend the tunnel is up
    dialled = []
    monkeypatch.setattr(dial, "_vobiz_call", lambda to, cid: (dialled.append((to, cid)), {"request_uuid": "r1"})[1])
    monkeypatch.setattr(dial, "_wait_hangup", lambda cid, t: {"hangup_cause": "NORMAL_CLEARING", "duration_s": 3})
    base = dict(device="D1", speaker="S02", lang="hi", persona="Rahul", upi="rahul.friend@okfinbank",
                min_amount=2000, max_amount=50000, max_turns=4, n=1, stt="sarvam", llm="openai", vad="energy",
                no_prewarm=True)
    dial.cmd_agent(type("A", (), base), Registry())
    (to, cid), = dialled
    c = settings.calls()[cid]
    assert to == "+919000000001" and c["kind"] == "agent"
    assert c["card"]["upi_id"] == "rahul.friend@okfinbank" and c["speaker"] == "S02" and c["vad"] == "energy"
    assert cid not in _ingested_ids()
    with pytest.raises(PermissionError):                                  # no clone consent -> nothing dialled
        dial.cmd_agent(type("A", (), {**base, "speaker": "V01"}), Registry())
    assert len(dialled) == 1


def test_protocol_live_callers_stay_in_one_split():
    from realcall import protocol
    old = set(protocol.TEST_DEVICES)
    protocol.TEST_DEVICES.clear()
    protocol.TEST_DEVICES.add("DT")
    try:
        for caller in ("V01", "V02", "V03", "V04", "V05", "V06"):
            on_train_device = protocol.split_for("live", "x", "D1", caller, "bonafide", caller)
            on_test_device = protocol.split_for("live", "y", "DT", caller, "bonafide", caller)
            # a caller is test everywhere, or never reaches test through the test-only device
            assert on_test_device == ("test" if on_train_device == "test" else "excluded")
    finally:
        protocol.TEST_DEVICES.clear()
        protocol.TEST_DEVICES.update(old)


def test_gate_math():
    from realcall.gate import eer, wilson_upper
    assert abs(wilson_upper(0, 50) - 0.0713) < 0.001
    assert eer(np.array([0.1, 0.2, 0.3]), np.array([0.7, 0.8, 0.9])) == 0.0
    assert abs(eer(np.random.default_rng(0).random(2000), np.random.default_rng(1).random(2000)) - 0.5) < 0.05


def test_phone_answers_only_our_caller(monkeypatch):
    from realcall import phone
    monkeypatch.setattr(phone, "expected_caller", lambda: "8064260325")
    screens = {"reg": "", "ui": "<hierarchy></hierarchy>"}
    monkeypatch.setattr(phone, "adb", lambda *a, **k: screens["reg"] if "telephony.registry" in a else (screens["ui"] if "cat" in a else ""))
    screens["reg"] = "mCallState=1\n mCallIncomingNumber=+919999999999\n"
    assert phone.ringing_caller_matches()[0] is False          # a stranger: never answered
    screens["reg"] = "mCallState=1\n mCallIncomingNumber=\n"
    assert phone.ringing_caller_matches()[0] is False          # withheld and not on screen: never answered
    screens["ui"] = '<hierarchy><node text="+91 80 6426 0325" /></hierarchy>'
    assert phone.ringing_caller_matches() == (True, "screen")  # our Vobiz number on the ringing screen
    screens["reg"] = "mCallState=1\n mCallIncomingNumber=08064260325\n"
    assert phone.ringing_caller_matches() == (True, "telephony")


def test_relocate_paths():
    from realcall.relocate import relocate_path
    assert relocate_path(r"D:\old\laptop\ml\realcall\work\capture\live_ab.wav") == str(settings.WORK / "capture/live_ab.wav")
    assert relocate_path("/home/v/pehchaan/ml/realcall/work/segments/x/00.wav") == str(settings.WORK / "segments/x/00.wav")
    assert relocate_path("segments/x/00.wav") == "segments/x/00.wav"       # relative paths are left alone
    assert relocate_path(None) is None


def test_live_clone_consent_and_purge(tmp_path):
    """Closing demo: consent needs the signed form; purge deletes every recording and clip and withdraws consent."""
    from realcall import live_clone
    form = tmp_path / "J01.jpg"
    form.write_bytes(b"signed form")
    args = lambda **kw: type("A", (), kw)  # noqa: E731
    with pytest.raises(SystemExit):
        live_clone.cmd_consent(args(id="J01", form=str(tmp_path / "missing.jpg"), name=None))
    with pytest.raises(SystemExit):   # a team participant's id can't be taken over
        live_clone.cmd_consent(args(id="S01", form=str(form), name=None))
    with pytest.raises(PermissionError):
        Registry().require_clone("J01")
    live_clone.cmd_consent(args(id="J01", form=str(form), name="Judge"))
    Registry().require_clone("J01")
    d = live_clone.LIVE / "J01"
    d.mkdir(parents=True, exist_ok=True)
    for f in ("ref.wav", "clone_1.wav"):
        (d / f).write_bytes(b"RIFF")
    live_clone.ATTACK_SRC.mkdir(parents=True, exist_ok=True)
    (live_clone.ATTACK_SRC / "J01_1.wav").write_bytes(b"RIFF")
    live_clone.cmd_purge(args(id="J01"))
    assert not d.exists() and not list(live_clone.ATTACK_SRC.glob("J01_*"))
    with pytest.raises(PermissionError):
        Registry().require_clone("J01")
    assert (live_clone.FORMS / "J01.jpg").exists()   # the record that consent was given stays


def test_split_sentences():
    from realcall import agent
    assert agent.split_sentences("Maa main hoon. Paise bhej do!") == ["Maa main hoon.", "Paise bhej do!"]
    assert agent.split_sentences("Haan. Ab?") == ["Haan. Ab?"]              # the short 2nd piece merges back
    assert agent.split_sentences("ठीक है। पैसे भेज दो।") == ["ठीक है।", "पैसे भेज दो।"]
    assert agent.split_sentences("") == [] and agent.split_sentences("ek hi line") == ["ek hi line"]


def test_filler_bank_cache_and_rotation():
    from realcall import agent

    class CountTTS(agent.FakeTTS):
        n = 0

        def synth(self, text, emotion, lang):
            CountTTS.n += 1
            return super().synth(text, emotion, lang)

    CountTTS.n = 0
    n_hi = len(agent.FILLERS["hi"])
    b = agent.FillerBank("S02", "sarvam", "hi").prepare(CountTTS())
    assert CountTTS.n == n_hi and len(b.audios) == n_hi                     # rendered once
    CountTTS.n = 0
    b2 = agent.FillerBank("S02", "sarvam", "hi").prepare(CountTTS())        # all cached now
    assert CountTTS.n == 0 and len(b2.audios) == n_hi
    got = [id(b2.next()) for _ in range(n_hi + 1)]
    assert got[0] == got[n_hi]                                              # rotation wraps around
    assert agent.FillerBank("NOPE", "sarvam", "hi").load().next() is None   # no cache -> no filler


def test_opener_render_take_delete():
    from realcall import agent
    card = agent.ScriptCard()
    providers = agent.Providers(agent.FakeSTT(), agent.FakeLLM(), agent.FakeTTS())
    cid = "a1" * 16
    plan, audio = agent.render_opener(cid, card, providers)
    assert agent._opener_file(cid).exists() and len(audio) > 0
    got = agent.take_opener(cid)
    assert got is not None and got[0].text == plan.text and not agent._opener_file(cid).exists()
    assert agent.take_opener(cid) is None                                   # already taken, and gone


def test_agent_live_feel_opener_and_filler(monkeypatch):
    """A slow reply is covered by a filler, and the son's opener is the one rendered before the ring (step 0
    prerendered), consumed and deleted. Still metadata only."""
    from fastapi.testclient import TestClient
    from realcall import agent, server
    server.config = lambda: {**settings.DEFAULTS, "public_base_url": "https://example.trycloudflare.com"}
    card = agent.ScriptCard(max_turns=1)
    agent.FillerBank("S02", "sarvam", card.lang).prepare(agent.FakeTTS())   # filler cache for this call

    class SlowLLM(agent.FakeLLM):
        def reply(self, history, mother_text, card):
            if mother_text is not None:
                time.sleep(agent.FILLER_AFTER_S + 0.4)                      # force a filler while we "think"
            return super().reply(history, mother_text, card)

    providers = agent.Providers(agent.FakeSTT(), SlowLLM(), agent.FakeTTS())
    monkeypatch.setattr(server, "_make_agent", lambda c: (providers, agent.make_vad("energy", sr=agent.SR_UP), card))
    cl = TestClient(server.app)
    cid = "f" * 32
    settings.log_event("call_registered", call_id=cid, kind="agent", device="D2", speaker="S02",
                       card=card.as_dict(), fillers=True)
    agent.render_opener(cid, card, providers)                               # opener made before the call
    assert agent._opener_file(cid).exists()

    speech = fake_speech(1.1, 150, 7)
    with cl.websocket_connect(f"/ws/agent/{cid}") as ws:
        ws.send_text(json.dumps({"event": "start", "start": {"streamId": "s1"}}))
        inbound = np.concatenate([np.zeros(int(0.6 * SR), np.float32), speech, np.zeros(int(0.9 * SR), np.float32)])
        for i in range(0, len(inbound) // 320 * 320, 320):
            pcm = (inbound[i:i + 320] * 32767).astype("<i2").tobytes()
            ws.send_text(json.dumps({"event": "media", "media": {"track": "inbound", "payload": base64.b64encode(pcm).decode()}}))
        for _ in range(600):
            if ws.receive_json()["event"] == "stop":
                break
    assert not agent._opener_file(cid).exists()                             # consumed and deleted
    turns = {e["step"]: e for e in settings.read_ledger() if e.get("ev") == "agent_turn" and e.get("call_id") == cid}
    assert turns[0]["prerendered"] is True and turns[0]["filler"] is False
    assert turns[1]["filler"] is True                                       # the filler covered the slow reply
    assert all("text" not in e and "transcript" not in e for e in turns.values())


def test_speakable_numbers_and_handles():
    from realcall import agent
    assert agent.speakable("Maa, ₹50,000 bhej do") == "Maa, 50000 rupaye bhej do"
    assert agent.speakable("Rs. 2000 abhi") == "2000 rupaye abhi"
    assert agent.speakable("rahul.friend@okfinbank par") == "rahul dot friend at okfinbank par"
    assert agent.speakable("pachaas hazaar rupaye") == "pachaas hazaar rupaye"           # words pass through


def test_agent_skips_empty_transcript(monkeypatch):
    """Noise and echo transcribe to nothing; the agent must not reply to them. With an STT that always returns
    whitespace, only the opener is spoken and no reply turn is logged."""
    from fastapi.testclient import TestClient
    from realcall import agent, server
    server.config = lambda: {**settings.DEFAULTS, "public_base_url": "https://example.trycloudflare.com"}
    card = agent.ScriptCard(max_turns=4)

    class EmptySTT:
        def transcribe(self, pcm, sr):
            return "   "                                          # whitespace only, like a noise/echo transcript

    providers = agent.Providers(EmptySTT(), agent.FakeLLM(), agent.FakeTTS())
    monkeypatch.setattr(server, "_make_agent", lambda c: (providers, agent.make_vad("energy", sr=agent.SR_UP), card))
    cl = TestClient(server.app)
    cid = "d" * 32
    settings.log_event("call_registered", call_id=cid, kind="agent", device="D2", speaker="S02", card=card.as_dict())
    speech = fake_speech(1.1, 150, 11)
    with cl.websocket_connect(f"/ws/agent/{cid}") as ws:
        ws.send_text(json.dumps({"event": "start", "start": {"streamId": "s1"}}))
        inbound = np.concatenate([np.zeros(int(0.6 * SR), np.float32), speech, np.zeros(int(0.9 * SR), np.float32)])
        for i in range(0, len(inbound) // 320 * 320, 320):
            pcm = (inbound[i:i + 320] * 32767).astype("<i2").tobytes()
            ws.send_text(json.dumps({"event": "media", "media": {"track": "inbound", "payload": base64.b64encode(pcm).decode()}}))
        ws.send_text(json.dumps({"event": "stop"}))               # end the call (the agent would otherwise just wait)
        for _ in range(400):
            if ws.receive_json()["event"] == "stop":
                break
    turns = [e for e in settings.read_ledger() if e.get("ev") == "agent_turn" and e.get("call_id") == cid]
    assert [e["step"] for e in turns] == [0]                      # only the opener; the empty turns were skipped


def test_dial_refuses_when_tunnel_down(monkeypatch):
    """If the webhook can't be reached the call would drop on connect, so nothing is dialled (no paid call)."""
    from realcall import dial
    dialled = []
    monkeypatch.setattr(dial, "_tunnel_ok", lambda: False)
    monkeypatch.setattr(dial, "_vobiz_call", lambda to, cid: dialled.append(cid) or {"request_uuid": "r1"})
    base = dict(device="D1", speaker="S02", lang="hi", persona="Rahul", upi="rahul.friend@okfinbank",
                min_amount=2000, max_amount=50000, max_turns=4, n=1, stt="sarvam", llm="openai", vad="energy",
                no_prewarm=True)
    with pytest.raises(SystemExit, match="tunnel"):
        dial.cmd_agent(type("A", (), base), Registry())
    assert dialled == []
