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
    assert r.status_code == 200 and f"/tapes/{meta['tape_id']}.wav</Play>" in r.text and "recordSession" in r.text
    assert cl.post("/answer/" + "z" * 32).status_code == 404
    assert cl.get(f"/tapes/{meta['tape_id']}.wav").status_code == 200
    assert cl.get("/tapes/..%2Fledger.jsonl").status_code == 404

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


def test_gate_math():
    from realcall.gate import eer, wilson_upper
    assert abs(wilson_upper(0, 50) - 0.0713) < 0.001
    assert eer(np.array([0.1, 0.2, 0.3]), np.array([0.7, 0.8, 0.9])) == 0.0
    assert abs(eer(np.random.default_rng(0).random(2000), np.random.default_rng(1).random(2000)) - 0.5) < 0.05
