"""Coqui XTTS-v2 (CPML licence: NON-COMMERCIAL). hi/en zero-shot cloning from a 6+ s reference
(job["ref_wav"]) or one of the built-in studio speakers (job["speaker"])."""
import os
import sys

os.environ.setdefault("COQUI_TOS_AGREED", "1")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

a = common.args()
jobs = common.load_jobs(a)
if jobs:
    import numpy as np
    import torch
    from TTS.api import TTS
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cuda")
    sr = tts.synthesizer.output_sample_rate

    def fn(j):
        torch.manual_seed(int(j.get("seed", 0)))
        lang = {"en": "en", "hi": "hi"}[j["lang"]]
        if j.get("speaker"):
            wav = tts.tts(text=j["text"], speaker=j["speaker"], language=lang)
        else:
            wav = tts.tts(text=j["text"], speaker_wav=j["ref_wav"], language=lang)
        return np.asarray(wav, dtype=np.float32), sr

    common.run(jobs, fn, "xtts")
