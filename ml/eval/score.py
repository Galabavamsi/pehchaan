"""Score a manifest with one detector.

  python eval/score.py --manifest M.csv --detector ssl_la --out scores/ssl_la__M.csv [--root DIR]

Manifest: CSV with at least `utt_id,path` (path relative to --root or absolute). Output CSV:
utt_id,score   (score = spoof logit-difference; higher = more likely synthetic).
Detectors: ssl_la | ssl_df | nii_mms300m | hf:<repo> | ckpt:<path-to-our-checkpoint>
"""
import argparse
import os
import sys
import threading
import queue

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.audio import load_any  # noqa: E402

W = os.path.expanduser("~/weights")


def build(name, device=None):
    from models import detectors as D
    if name == "ssl_la":
        return D.SSLAASIST(f"{W}/ssl_aasist/Pre_trained_SSL_anti-spoofing_models/LA_model.pth", device, name="ssl_aasist_LA")
    if name == "ssl_df":
        return D.SSLAASIST(f"{W}/ssl_aasist/Pre_trained_SSL_anti-spoofing_models/Best_LA_model_for_DF.pth", device, name="ssl_aasist_DF")
    if name.startswith("ckpt:"):
        return D.SSLAASIST(name[5:], device, name=os.path.basename(name[5:]))
    if name.startswith("hf:"):
        return D.HFAudioClassifier(name[3:], device=device)
    if name == "nii_mms300m":
        from models.nii_antideepfake import NIIAntiDeepfake
        return NIIAntiDeepfake("nii-yamagishilab/mms-300m-anti-deepfake", device)
    raise ValueError(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--detector", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--root", default="")
    ap.add_argument("--bs", type=int, default=16)
    ap.add_argument("--device", default=None)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    df = pd.read_csv(a.manifest)
    if a.limit:
        df = df.sample(n=min(a.limit, len(df)), random_state=0)
    done = set()
    if os.path.exists(a.out):
        done = set(pd.read_csv(a.out)["utt_id"].astype(str))
    df = df[~df["utt_id"].astype(str).isin(done)]
    if len(df) == 0:
        print("nothing to do")
        return
    det = build(a.detector, a.device)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    rows = list(df[["utt_id", "path"]].itertuples(index=False))

    q = queue.Queue(maxsize=8)

    def loader():
        for i in range(0, len(rows), a.bs):
            chunk = rows[i:i + a.bs]
            wavs = []
            for r in chunk:
                p = r.path if os.path.isabs(r.path) or not a.root else os.path.join(a.root, r.path)
                wavs.append(load_any(p))
            q.put((chunk, wavs))
        q.put(None)

    threading.Thread(target=loader, daemon=True).start()
    header = not os.path.exists(a.out)
    n = 0
    with open(a.out, "a") as f:
        if header:
            f.write("utt_id,score\n")
        while True:
            item = q.get()
            if item is None:
                break
            chunk, wavs = item
            s = det.score_batch(wavs, max_bs=a.bs)
            for r, v in zip(chunk, s):
                f.write(f"{r.utt_id},{float(v):.5f}\n")
            n += len(chunk)
            if n % (a.bs * 50) == 0:
                f.flush()
                print(f"{n}/{len(rows)}", flush=True)
    print("done", n)


if __name__ == "__main__":
    main()
