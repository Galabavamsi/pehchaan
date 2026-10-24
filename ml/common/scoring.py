"""How a clip is scored, shared by the voice service (serve/app.py), the detector bench (serve/panel.py) and the
clone-vs-detect benchmark (eval/clone_vs_detect.py), so the three give the same score for the same audio.

Only the first MAX_S seconds of a clip are scored (PEHCHAAN_MAX_SECONDS, default 60). XLS-R+AASIST models score
~4 s windows (WIN samples, HOP hop) over that whole span, skipping windows that are mostly silence by Silero VAD,
and the clip score is the mean window logit. NII AntiDeepfake scores whole chunks of up to 16 s of the same span
(its native protocol) and the clip score is the mean chunk logit.
"""
import os

import numpy as np

from common.audio import fix_length

SR = 16000
MAX_S = float(os.environ.get("PEHCHAAN_MAX_SECONDS", "60"))
WIN, HOP = 64600, 32000       # the model's native 4.04 s input, 2 s hop
MIN_SPEECH_FRAC = 0.25        # skip windows that are mostly silence (unless every window is)
NII_CHUNK = 16 * SR           # NII: whole chunks of up to 16 s; shorter than 1 s only if nothing else is left
_vad = None


def clip(x):
    """The part of a clip that is scored."""
    return x[: int(MAX_S * SR)]


def vad():
    global _vad
    if _vad is None:
        from silero_vad import load_silero_vad
        _vad = load_silero_vad()   # note: this sets torch's thread count to 1; callers restore their own
    return _vad


def speech_mask(x):
    """Per-sample speech flags from Silero VAD."""
    import torch
    from silero_vad import get_speech_timestamps
    ts = get_speech_timestamps(torch.from_numpy(x), vad(), sampling_rate=SR, min_silence_duration_ms=200)
    mask = np.zeros(len(x), dtype=bool)
    for t in ts:
        mask[t["start"]:t["end"]] = True
    return mask


def plan_windows(n_samples, speech_mask=None):
    """Start offsets of the scoring windows over the whole clip, silent windows dropped."""
    if n_samples <= WIN:
        return [0]
    starts = list(range(0, n_samples - WIN + 1, HOP))
    if starts[-1] != n_samples - WIN:
        starts.append(n_samples - WIN)
    if speech_mask is not None:
        frac = [float(speech_mask[s:s + WIN].mean()) for s in starts]
        keep = [s for s, f in zip(starts, frac) if f >= MIN_SPEECH_FRAC]
        starts = keep or [starts[int(np.argmax(frac))]]
    return starts


def window_segments(x, starts):
    return [fix_length(x[s:s + WIN], WIN) for s in starts]


def aasist_score(logits, x, starts, batch=8):
    """XLS-R+AASIST clip score: mean spoof-minus-bona-fide logit over the planned windows. `logits` maps a list of
    WIN-sample segments to an [n, 2] array; windows go through it in batches of `batch`, as on the service."""
    segs = window_segments(x, starts)
    lg = np.concatenate([logits(segs[b:b + batch]) for b in range(0, len(segs), batch)])
    return float((lg[:, 0] - lg[:, 1]).mean())


def nii_chunks(x):
    chunks = [x[i:i + NII_CHUNK] for i in range(0, len(x), NII_CHUNK)]
    return [c for c in chunks if len(c) >= SR] or [x]
