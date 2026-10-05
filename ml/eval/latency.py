"""Inference latency for a 10 s clip (model forward only, and the full /v1/voice/score service path).

  python eval/latency.py --ckpt runs/ours/best.pt --device cuda --out results/latency_<host>.json
"""
import argparse
import json
import os
import platform
import sys
import time

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.threads:
        torch.set_num_threads(a.threads)
    from models.detectors import SSLAASIST, timed_latency
    det = SSLAASIST(a.ckpt, device=a.device, fp16=a.device == "cuda")
    r = {"device": a.device, "host": platform.node(), "cpu": platform.processor() or platform.machine(),
         "torch_threads": torch.get_num_threads(),
         "gpu": torch.cuda.get_device_name(0) if a.device == "cuda" else None,
         "windows_per_10s_clip": 4, "model_forward_10s": timed_latency(det, 10.0, n=a.n if a.device == "cuda" else max(5, a.n // 4))}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(r, open(a.out, "w"), indent=1)
    print(json.dumps(r, indent=1))


if __name__ == "__main__":
    main()
