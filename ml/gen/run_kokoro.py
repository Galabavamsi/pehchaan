"""Kokoro-82M (hexgrad/Kokoro-82M; Apache-2.0). Stock voices only (no cloning): Hindi hf_alpha, hf_beta,
hm_omega, hm_psi; English af_*/am_*/bf_*/bm_*. Job needs "voice"."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

a = common.args()
jobs = common.load_jobs(a)
if jobs:
    import numpy as np
    from kokoro import KPipeline
    pipes = {}

    def fn(j):
        v = j["voice"]
        lc = "h" if v.startswith("h") else ("b" if v.startswith("b") else "a")
        if lc not in pipes:
            pipes[lc] = KPipeline(lang_code=lc, repo_id="hexgrad/Kokoro-82M")
        chunks = [np.asarray(r.audio, dtype=np.float32) for r in pipes[lc](j["text"], voice=v, speed=float(j.get("speed", 1.0)))
                  if r.audio is not None]
        return np.concatenate(chunks), 24000

    common.run(jobs, fn, "kokoro")
