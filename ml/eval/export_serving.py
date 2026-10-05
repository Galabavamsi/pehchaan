"""Export the chosen checkpoint + calibration/bands for the Voice Provenance Service.

  python eval/export_serving.py --ckpt runs/ours/best.pt --metrics results/metrics.json --name ours \
        --version pehchaan-xlsr-aasist-ft-v1 --out_dir serve
Writes serve/weights/<version>.safetensors (fp16) and serve/model_config.json.
"""
import argparse
import hashlib
import json
import os

import torch
from safetensors.torch import save_file


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--metrics", required=True)
    ap.add_argument("--name", default="ours")
    ap.add_argument("--version", required=True)
    ap.add_argument("--out_dir", required=True)
    a = ap.parse_args()
    m = json.load(open(a.metrics))["detectors"][a.name]
    sd = torch.load(a.ckpt, map_location="cpu", weights_only=False)
    sd = {k: v.half().contiguous() if v.is_floating_point() else v.contiguous() for k, v in sd.items()}
    os.makedirs(os.path.join(a.out_dir, "weights"), exist_ok=True)
    wp = os.path.join(a.out_dir, "weights", f"{a.version}.safetensors")
    save_file(sd, wp)
    h = hashlib.sha256(open(wp, "rb").read()).hexdigest()[:12]
    cfg = {"model_version": f"{a.version}+{h}", "weights": f"weights/{a.version}.safetensors",
           "platt": m["platt"], "bands": m["bands"],
           "band_LRs_measured": {k: {b: v[b]["LR"] for b in ("likely_synthetic", "inconclusive", "no_strong_evidence")}
                                 for k, v in m["band_LRs"].items() if v},
           "quality_gate": {"min_speech_sec": 4.0, "min_snr_db": 10.0},
           "note": "Calibrated on dev (seen generators). Held-out-generator LRs are the conservative ones for fusion."}
    json.dump(cfg, open(os.path.join(a.out_dir, "model_config.json"), "w"), indent=1)
    print(json.dumps(cfg, indent=1))


if __name__ == "__main__":
    main()
