"""Voice Provenance Service client.

If VOICE_SERVICE_URL is set, the WAV is proxied there (the ML teammate's
service, contract per SPEC section 7). Otherwise a deterministic MOCK answers.
The mock is not a detector: it measures duration/SNR from the audio and derives
p_synthetic from a hash of the bytes (or from an explicit demo hint), and it
labels itself loudly as a mock in every response.
"""
from __future__ import annotations

import hashlib
import io
import math
import os
import time
import wave

import httpx
import numpy as np

from pehchaan import default_config

MOCK_MODEL_VERSION = "mock-voice-0.1 (NOT A DETECTOR - demo stand-in)"
DEMO_HINT_P = {"synthetic": 0.91, "bonafide": 0.12, "watermark": 0.96}


def _read_wav(data: bytes) -> tuple[np.ndarray, int]:
    with wave.open(io.BytesIO(data), "rb") as w:
        sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(n)
    if sw == 2:
        x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768
    elif sw == 1:
        x = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128) / 128
    elif sw == 4:
        x = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2**31
    else:
        raise ValueError(f"unsupported sample width {sw}")
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def measure_quality(x: np.ndarray, sr: int) -> dict:
    """Energy VAD on 20 ms frames: speech_sec and a crude SNR (speech vs noise-floor energy)."""
    frame = max(1, int(0.02 * sr))
    nfr = len(x) // frame
    if nfr == 0:
        return {"duration_sec": 0.0, "speech_sec": 0.0, "snr_db": 0.0}
    e = (x[: nfr * frame].reshape(nfr, frame) ** 2).mean(axis=1) + 1e-10
    floor = np.percentile(e, 10)
    speech = e > floor * 10 ** (6 / 10)  # 6 dB above floor
    speech_e = e[speech].mean() if speech.any() else floor
    noise_e = e[~speech].mean() if (~speech).any() else floor
    return {
        "duration_sec": round(len(x) / sr, 2),
        "speech_sec": round(float(speech.sum() * frame / sr), 2),
        "snr_db": round(float(10 * math.log10(speech_e / noise_e)), 1),
    }


def band_for(p: float, quality_ok: bool) -> str:
    th = default_config().voice.band_thresholds
    if not quality_ok:
        return "inconclusive"
    if p >= th["likely_synthetic_at_or_above"]:
        return "likely_synthetic"
    if p < th["no_strong_evidence_below"]:
        return "no_strong_evidence"
    return "inconclusive"


def mock_score(data: bytes, demo_hint: str | None = None) -> dict:
    t0 = time.perf_counter()
    try:
        x, sr = _read_wav(data)
        q = measure_quality(x, sr)
    except Exception as exc:  # not a WAV
        q = {"duration_sec": 0.0, "speech_sec": 0.0, "snr_db": 0.0, "error": f"unreadable audio: {exc}"}
    g = default_config().guardrails
    ok = q["speech_sec"] >= g.g3_min_speech_sec and q["snr_db"] >= g.g3_min_snr_db
    if demo_hint in DEMO_HINT_P:
        p = DEMO_HINT_P[demo_hint]
    else:
        p = int(hashlib.sha256(data).hexdigest()[:8], 16) / 0xFFFFFFFF
    wm = demo_hint == "watermark"
    return {
        "p_synthetic": round(p, 3),
        "band": band_for(p, ok),
        "quality": {"speech_sec": q["speech_sec"], "snr_db": q["snr_db"], "ok": ok, "duration_sec": q["duration_sec"]},
        "watermark": {"detected": wm, "scheme": "perth" if wm else None},
        "model_version": MOCK_MODEL_VERSION,
        "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        "mock": True,
        "mock_notice": "Deterministic mock: quality is measured from the audio, p_synthetic is NOT. "
                       "Set VOICE_SERVICE_URL to use the real Voice Provenance Service.",
        "demo_hint": demo_hint,
    }


async def score(data: bytes, filename: str = "clip.wav", demo_hint: str | None = None) -> dict:
    url = os.environ.get("VOICE_SERVICE_URL", "").strip()
    if not url:
        return mock_score(data, demo_hint)
    target = url if url.rstrip("/").endswith("score") else url.rstrip("/") + "/v1/voice/score"
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(target, files={"file": (filename, data, "audio/wav")})
            r.raise_for_status()
            out = r.json()
        out.setdefault("latency_ms", round((time.perf_counter() - t0) * 1000, 1))
        out["mock"] = False
        out["proxied_to"] = target
        if "band" not in out and "p_synthetic" in out:
            out["band"] = band_for(out["p_synthetic"], (out.get("quality") or {}).get("ok", True))
        return out
    except Exception as exc:
        res = mock_score(data, demo_hint)
        res["fallback_reason"] = f"voice service at {target} failed: {exc}"
        return res


# ---------------------------------------------------------------------------
# demo audio (generated, so no .wav files are committed)
# ---------------------------------------------------------------------------
def demo_wav(kind: str, sr: int = 16000) -> bytes:
    """Speech-like test signal: harmonic 'voice' with syllable-rate envelope and pauses.
    kinds: synthetic | bonafide | noisy | short. Content is identical in spirit;
    the label is carried by the demo hint, because the mock is not a detector."""
    rng = np.random.default_rng({"synthetic": 1, "bonafide": 2, "noisy": 3, "short": 4}.get(kind, 0))
    dur = 2.6 if kind == "short" else 10.0
    t = np.arange(int(dur * sr)) / sr
    f0 = 140 + 25 * np.sin(2 * np.pi * 0.7 * t) + 10 * np.sin(2 * np.pi * 3.1 * t)
    phase = 2 * np.pi * np.cumsum(f0) / sr
    voice = sum((0.6 / k) * np.sin(k * phase) for k in range(1, 9))
    syll = 0.5 * (1 + np.sin(2 * np.pi * 4.2 * t + rng.uniform(0, 6)))
    gate = (np.sin(2 * np.pi * 0.35 * t) > -0.6).astype(float)
    x = voice * syll * gate
    noise_level = 0.25 if kind == "noisy" else 0.004
    x = 0.3 * x / np.abs(x).max() + noise_level * rng.standard_normal(len(t))
    pcm = np.clip(x, -1, 1)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((pcm * 32767).astype("<i2").tobytes())
    return buf.getvalue()
