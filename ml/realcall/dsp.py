"""Signal helpers: sync chirp, matched-filter detection, item alignment, a small energy VAD, quality numbers.

No librosa: everything is numpy/scipy so it runs on the laptop as is.
"""
import numpy as np
from scipy.signal import butter, chirp as _chirp, fftconvolve, sosfiltfilt

from common.audio import resample

SR = 16000
CHIRP_S = 0.6
CHIRP_F = (300.0, 3400.0)  # inside the narrowband telephone passband, so it survives every codec


def sync_chirp(sr: int = SR) -> np.ndarray:
    t = np.arange(int(CHIRP_S * sr)) / sr
    x = _chirp(t, f0=CHIRP_F[0], t1=CHIRP_S, f1=CHIRP_F[1], method="linear")
    return (0.5 * x * np.hanning(len(t))).astype(np.float32)


def bandpass(x: np.ndarray, sr: int, lo: float = 300.0, hi: float = 3400.0) -> np.ndarray:
    hi = min(hi, 0.45 * sr)
    sos = butter(4, [lo, hi], btype="band", fs=sr, output="sos")
    return sosfiltfilt(sos, x).astype(np.float32)


def _ncc(x: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Normalised cross-correlation of template t against every position of x (valid part)."""
    t = (t - t.mean()) / (np.linalg.norm(t - t.mean()) + 1e-9)
    num = fftconvolve(x, t[::-1], mode="valid")
    x2 = fftconvolve(x * x, np.ones(len(t)), mode="valid")
    x1 = fftconvolve(x, np.ones(len(t)), mode="valid")
    var = np.maximum(x2 - x1 * x1 / len(t), 1e-12)
    return num / np.sqrt(var)


def find_chirps(x: np.ndarray, sr: int = SR, min_ncc: float = 0.35, min_gap_s: float = 2.0):
    """Positions (seconds) and scores of the sync chirps in a capture, strongest-first filtered, time-ordered."""
    y = bandpass(resample(x, sr, 8000), 8000)
    c = _ncc(y, bandpass(sync_chirp(8000), 8000))
    hits, used = [], np.zeros(len(c), bool)
    gap = int(min_gap_s * 8000)
    for i in np.argsort(-c):
        if c[i] < min_ncc or len(hits) >= 8:
            break
        if used[max(0, i - gap):i + gap].any():
            continue
        used[i] = True
        hits.append((i / 8000.0, float(c[i])))
    return sorted(hits)


ENV_HOP_S = 0.005


def envelope(x: np.ndarray, sr: int = SR) -> np.ndarray:
    """Log-energy envelope at 200 Hz from the telephone band. Survives codecs, reverb and phase smear,
    which waveform correlation through a speakerphone does not (NCC ~0.1-0.2 in tests)."""
    y = bandpass(resample(x, sr, 8000), 8000)
    hop = int(ENV_HOP_S * 8000)
    m = len(y) // hop
    if m == 0:
        return np.zeros(1, np.float32)
    e = np.log((y[: m * hop].reshape(m, hop) ** 2).mean(1) + 1e-7)
    return np.maximum(e, np.percentile(e, 10)).astype(np.float32)


def align_item(capture: np.ndarray, item: np.ndarray, expected_s: float, sr: int = SR, search_s: float = 0.6):
    """Refine where `item` sits in `capture` near `expected_s` by envelope correlation. Returns (start_s, ncc_peak)."""
    a_s = max(0.0, expected_s - search_s)
    win = capture[int(a_s * sr): int((expected_s + search_s) * sr) + len(item)]
    ew, ei = envelope(win, sr), envelope(item, sr)
    if len(ew) < len(ei) + 1 or ei.std() < 1e-6:
        return expected_s, 0.0
    c = _ncc(ew, ei)
    i = int(np.argmax(c))
    return a_s + i * ENV_HOP_S, float(c[i])


def frame_db(x: np.ndarray, sr: int = SR, frame_s: float = 0.03) -> np.ndarray:
    n = int(frame_s * sr)
    m = len(x) // n
    if m == 0:
        return np.array([-120.0])
    f = x[: m * n].reshape(m, n)
    return 20 * np.log10(np.sqrt((f.astype(np.float64) ** 2).mean(1)) + 1e-9)


def vad_regions(x: np.ndarray, sr: int = SR, frame_s: float = 0.03, margin_db: float = 12.0,
                min_speech_s: float = 0.3, max_gap_s: float = 0.6):
    """Speech regions [(start_s, end_s)] from frame energy above an adaptive noise floor."""
    db = frame_db(x, sr, frame_s)
    floor = np.percentile(db, 15)
    on = db > max(floor + margin_db, -55.0)
    regs, s = [], None
    for i, v in enumerate(on):
        if v and s is None:
            s = i
        elif not v and s is not None:
            regs.append([s, i])
            s = None
    if s is not None:
        regs.append([s, len(on)])
    merged = []
    for r in regs:
        if merged and (r[0] - merged[-1][1]) * frame_s <= max_gap_s:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    return [(a * frame_s, b * frame_s) for a, b in merged if (b - a) * frame_s >= min_speech_s]


def chunk_regions(regs, min_s: float = 4.0, max_s: float = 10.0):
    """Greedy-merge speech regions into chunks of min_s..max_s seconds (gaps included)."""
    out, cur = [], None
    for a, b in regs:
        if cur is None:
            cur = [a, b]
        elif b - cur[0] <= max_s:
            cur[1] = b
        else:
            if cur[1] - cur[0] >= min_s:
                out.append(tuple(cur))
            cur = [a, b]
        while cur[1] - cur[0] > max_s:
            out.append((cur[0], cur[0] + max_s))
            cur[0] += max_s
    if cur and cur[1] - cur[0] >= min_s:
        out.append(tuple(cur))
    return out


def trim(x: np.ndarray, sr: int = SR, pad_s: float = 0.15) -> np.ndarray:
    regs = vad_regions(x, sr)
    if not regs:
        return x
    a = max(0, int((regs[0][0] - pad_s) * sr))
    b = min(len(x), int((regs[-1][1] + pad_s) * sr))
    return x[a:b]


def quality(x: np.ndarray, sr: int = SR, floor_db: float | None = None) -> dict:
    """Speech seconds and SNR. Pass floor_db (noise measured in silence, e.g. tape gaps) when the clip is
    mostly speech: a floor estimated inside a speech-only clip undercounts speech badly."""
    db = frame_db(x, sr)
    floor = np.percentile(db, 15) if floor_db is None else floor_db
    speech = db[db > floor + 10]
    return {
        "dur_s": round(len(x) / sr, 2),
        "speech_s": round(len(speech) * 0.03, 2),
        "snr_db": round(float(np.median(speech) - floor) if len(speech) else 0.0, 1),
        "clip_frac": round(float(np.mean(np.abs(x) > 0.98)), 4),
        "rms_db": round(float(np.median(speech)) if len(speech) else -120.0, 1),
    }
