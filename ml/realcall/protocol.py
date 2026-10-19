"""Real-call evaluation protocol. Fixed on 2026-10-16, before any real-call data was collected or trained on.

Change this file only with a dated note below, and never after looking at test results.
"""
import hashlib

from common.protocol import HELDOUT_SPEAKERS

# A generator never used in any training run, so the finale can report a brand-new clone engine on real lines.
REALCALL_HELDOUT_GENERATORS = {"sarvam_ivc"}

# Fill in before the first session: one whole handset/carrier kept out of training, and the live callers
# whose calls form the gate set. Edit only before data from them exists.
# 2026-10-19: D2 (Varun's Redmi, Jio) made test-only before any D2 call existed, to test a held-out handset.
TEST_DEVICES: set = {"D2"}
TEST_CALLERS: set = set()

SPLIT_FRACTIONS = (0.60, 0.15, 0.25)  # train, dev, test

# The gate (README "The gate").
GATE_MIN_LIVE_CALLS = 50
GATE_MAX_FLAG_RATE = 0.05
GATE_WINDOW_S = 10.0       # the product scores one 8-12 s capture per call
CHUNK_MIN_S, CHUNK_MAX_S = 4.0, 10.0


def _bucket(key: str) -> str:
    h = int(hashlib.sha1(key.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    a, b, _ = SPLIT_FRACTIONS
    return "train" if h < a else ("dev" if h < a + b else "test")


def split_for(kind: str, call_id: str, device: str, speaker: str = "", generator: str = "", caller: str = "") -> str:
    # 2026-10-20 (before any live call was collected): live calls are split by CALLER first, so one caller is never
    # in both training and the gate. A non-test caller's live call on a test-only device is "excluded" (used by
    # neither side) instead of being pulled into test by the device rule.
    if kind == "live":
        cs = "test" if (caller in TEST_CALLERS or speaker in HELDOUT_SPEAKERS) else _bucket("caller:" + caller)
        if device in TEST_DEVICES and cs != "test":
            return "excluded"
        return cs
    if device in TEST_DEVICES:
        return "test"
    if speaker in HELDOUT_SPEAKERS or generator in REALCALL_HELDOUT_GENERATORS:
        return "test"
    return _bucket("call:" + call_id)


def heldout(speaker: str, generator: str) -> bool:
    return speaker in HELDOUT_SPEAKERS or generator in REALCALL_HELDOUT_GENERATORS
