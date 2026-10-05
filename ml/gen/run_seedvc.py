"""Seed-VC voice conversion (GPL-3.0). Source speech (src_wav) is converted to the voice of ref_wav.
This is the real-time clone attack: a scammer speaks and the VC makes it sound like the relative."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common  # noqa: E402

REPO = os.path.expanduser("~/repos/seed-vc")

a = common.args(lambda ap: ap.add_argument("--steps", type=int, default=25))
jobs = common.load_jobs(a)
if jobs:
    os.chdir(REPO)
    sys.path.insert(0, REPO)
    import numpy as np
    import torch
    from seed_vc_wrapper import SeedVCWrapper
    vc = SeedVCWrapper()

    def fn(j):
        torch.manual_seed(int(j.get("seed", 0)))
        # convert_voice is a generator function; the last yielded item carries the full waveform
        full = None
        for _mp3, full_audio in vc.convert_voice(source=j["src_wav"], target=j["ref_wav"], diffusion_steps=a.steps,
                                                 length_adjust=1.0, inference_cfg_rate=0.7, f0_condition=False,
                                                 auto_f0_adjust=False, pitch_shift=0, stream_output=True):
            if full_audio is not None:
                full = full_audio
        if isinstance(full, tuple):
            full = full[1]
        return np.asarray(full, dtype=np.float32).reshape(-1), 22050

    common.run(jobs, fn, "seedvc")
