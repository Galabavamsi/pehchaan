"""IndicF5 (ai4bharat/IndicF5; MIT; gated on HF, needs HF_TOKEN with accepted terms). 11 Indic languages."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

a = common.args(lambda ap: ap.add_argument("--repo", default="ai4bharat/IndicF5"))
jobs = common.load_jobs(a)
if jobs:
    import numpy as np
    import torch
    from transformers import AutoModel
    model = AutoModel.from_pretrained(a.repo, trust_remote_code=True).to("cuda")

    def fn(j):
        torch.manual_seed(int(j.get("seed", 0)))
        audio = model(j["text"], ref_audio_path=j["ref_wav"], ref_text=j["ref_text"])
        audio = np.asarray(audio)
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        audio = audio.astype(np.float32)
        if np.max(np.abs(audio)) > 2:
            audio = audio / 32768.0
        return audio, 24000

    common.run(jobs, fn, "indicf5")
