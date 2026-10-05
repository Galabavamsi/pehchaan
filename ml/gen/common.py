"""Shared job handling for every generator runner.

A job file is JSONL; one object per output clip:
  {"id": "...", "text": "...", "lang": "hi", "ref_wav": "/path/ref.wav", "ref_text": "...",
   "src_wav": "/path/source.wav" (voice conversion only), "out": "/path/out.wav", "seed": 0}
Runners skip jobs whose output exists, log failures to <out_dir>/failed.jsonl and never crash the
whole batch on one bad line. Outputs are written at the generator's native sample rate (16-bit WAV);
resampling to 16 kHz happens later in channel simulation.
"""
import argparse
import json
import os
import sys
import time
import traceback


def args(extra=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0)
    if extra:
        extra(ap)
    return ap.parse_args()


def load_jobs(a):
    jobs = [json.loads(l) for l in open(a.jobs, encoding="utf-8") if l.strip()]
    jobs = [j for i, j in enumerate(jobs) if i % a.nshards == a.shard]
    jobs = [j for j in jobs if not (os.path.exists(j["out"]) and os.path.getsize(j["out"]) > 1000)]
    if a.limit:
        jobs = jobs[: a.limit]
    return jobs


def run(jobs, fn, tag):
    """fn(job) -> (np.ndarray float32 mono, sr). Writes job['out']."""
    import numpy as np
    import soundfile as sf
    ok = fail = 0
    t0 = time.time()
    for k, j in enumerate(jobs):
        os.makedirs(os.path.dirname(j["out"]), exist_ok=True)
        try:
            wav, sr = fn(j)
            wav = np.asarray(wav, dtype=np.float32).reshape(-1)
            if len(wav) < sr * 0.3 or not np.isfinite(wav).all():
                raise RuntimeError(f"bad output len={len(wav)}")
            peak = np.max(np.abs(wav)) + 1e-9
            if peak > 0.99:
                wav = wav / peak * 0.99
            tmp = j["out"] + ".tmp.wav"
            sf.write(tmp, wav, sr, subtype="PCM_16")
            os.replace(tmp, j["out"])
            ok += 1
        except Exception as e:  # keep going
            fail += 1
            with open(os.path.join(os.path.dirname(j["out"]), "failed.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps({"id": j.get("id"), "err": repr(e)[:500], "tb": traceback.format_exc()[-1500:]},
                                   ensure_ascii=False) + "\n")
        if (k + 1) % 20 == 0 or k + 1 == len(jobs):
            el = time.time() - t0
            print(f"[{tag}] {k + 1}/{len(jobs)} ok={ok} fail={fail} {el / (k + 1):.2f}s/clip", flush=True)
    print(f"[{tag}] DONE ok={ok} fail={fail}", flush=True)
    sys.stdout.flush()
