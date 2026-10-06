"""End-to-end latency of the /v1/voice/score service path (decode + quality gate + watermark + model) on a 10 s clip.

  PEHCHAAN_DEVICE=cpu python serve/bench.py --wav some_10s.wav --label laptop-cpu --out ml/results/latency_service_cpu.json
Uses the in-process Service object (no HTTP), so the number excludes network/upload time.
"""
import argparse
import io
import json
import os
import platform
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav", required=True)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--label", default=platform.node())
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from serve.app import Service
    import torch
    svc = Service()
    b = open(a.wav, "rb").read()
    svc.run(b)
    ts = []
    for _ in range(a.n):
        t = time.perf_counter()
        r = svc.run(b)
        ts.append((time.perf_counter() - t) * 1000)
    out = {"label": a.label, "host": platform.node(), "cpu": platform.processor() or platform.machine(),
           "device": str(svc.device), "gpu": torch.cuda.get_device_name(0) if str(svc.device).startswith("cuda") else None,
           "cpu_int8": os.environ.get("PEHCHAAN_CPU_INT8", "1") == "1" and not str(svc.device).startswith("cuda"),
           "torch_threads": torch.get_num_threads(), "model_version": r["model_version"],
           "service_10s": {"median_ms": float(np.median(ts)), "p95_ms": float(np.percentile(ts, 95)), "n": a.n, "clip_s": 10.0},
           "last_response": r}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, "w", newline="\n"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
