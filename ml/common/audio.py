"""Small audio helpers shared by data prep, channel simulation, training and serving."""
from math import gcd

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

SR = 16000


def resample(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if sr_in == sr_out:
        return x.astype(np.float32)
    g = gcd(int(sr_in), int(sr_out))
    return resample_poly(x, sr_out // g, sr_in // g).astype(np.float32)


def load(path, sr: int = SR) -> np.ndarray:
    """Load any soundfile-readable file as mono float32 at `sr`."""
    x, s = sf.read(str(path), dtype="float32", always_2d=True)
    x = x.mean(axis=1)
    return resample(x, s, sr)


def load_any(path, sr: int = SR) -> np.ndarray:
    """Like load(), but falls back to ffmpeg for m4a/mp3/opus etc."""
    try:
        return load(path, sr)
    except Exception:
        import subprocess
        cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
        raw = subprocess.run(cmd, capture_output=True, check=True).stdout
        return np.frombuffer(raw, dtype=np.float32).copy()


def decode_bytes(data: bytes, sr: int = SR) -> np.ndarray:
    """Decode an uploaded file of any common format (wav, flac, ogg, mp3, m4a/aac, opus, webm) to mono float32
    at `sr`. soundfile first; ffmpeg otherwise, through a temp file because m4a/mp4 need a seekable input."""
    import io
    try:
        x, s = sf.read(io.BytesIO(data), dtype="float32", always_2d=True)
        return resample(x.mean(axis=1), s, sr)
    except Exception:
        import os
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(data)
            tmp = f.name
        try:
            return load_any(tmp, sr)
        finally:
            os.unlink(tmp)   # uploads are never kept on disk


def save(path, x: np.ndarray, sr: int = SR):
    sf.write(str(path), np.clip(x, -1, 1).astype(np.float32), sr, subtype="PCM_16")


def rms_db(x: np.ndarray) -> float:
    return float(20 * np.log10(np.sqrt(np.mean(np.square(x, dtype=np.float64))) + 1e-9))


def normalize_rms(x: np.ndarray, target_db: float = -26.0, peak: float = 0.99) -> np.ndarray:
    g = 10 ** ((target_db - rms_db(x)) / 20)
    y = x * g
    m = np.max(np.abs(y)) + 1e-9
    if m > peak:
        y = y * (peak / m)
    return y.astype(np.float32)


def trim_silence(x: np.ndarray, sr: int = SR, top_db: float = 35.0, pad_s: float = 0.15) -> np.ndarray:
    """Trim leading/trailing silence with the same rule for real and fake audio, so leading-silence
    length cannot become a shortcut feature (Mueller et al. 2021)."""
    import librosa
    if len(x) < sr // 4:
        return x
    _, (a, b) = librosa.effects.trim(x, top_db=top_db, frame_length=1024, hop_length=256)
    p = int(pad_s * sr)
    return x[max(0, a - p): min(len(x), b + p)]


def fix_length(x: np.ndarray, n: int, rng=None, random_crop: bool = False) -> np.ndarray:
    """Repeat-pad (as in SSL_Anti-spoofing) or crop to exactly n samples."""
    if len(x) >= n:
        if random_crop and rng is not None:
            s = int(rng.integers(0, len(x) - n + 1))
        else:
            s = 0
        return x[s:s + n]
    reps = int(np.ceil(n / max(1, len(x))))
    return np.tile(x, reps)[:n]


def windows(x: np.ndarray, n: int = 64600, hop: int = 32000, max_windows: int = 8):
    """Sliding windows for utterance-level scoring (mean of window logits)."""
    if len(x) <= n:
        return [fix_length(x, n)]
    starts = list(range(0, len(x) - n + 1, hop))
    if starts[-1] != len(x) - n:
        starts.append(len(x) - n)
    if len(starts) > max_windows:
        idx = np.linspace(0, len(starts) - 1, max_windows).round().astype(int)
        starts = [starts[i] for i in idx]
    return [x[s:s + n] for s in starts]
