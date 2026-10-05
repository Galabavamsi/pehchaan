"""Resemble Chatterbox Multilingual (MIT; every output carries a Perth watermark). hi/en and 21 more."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

a = common.args()
jobs = common.load_jobs(a)
if jobs:
    import torch
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    model = ChatterboxMultilingualTTS.from_pretrained(device="cuda")

    def fn(j):
        torch.manual_seed(int(j.get("seed", 0)))
        wav = model.generate(j["text"], language_id=j["lang"], audio_prompt_path=j["ref_wav"])
        return wav.squeeze(0).cpu().numpy(), model.sr

    common.run(jobs, fn, "chatterbox")
