"""Does the Perth watermark (embedded in every Chatterbox output) survive phone channels?

  python eval/watermark_eval.py --out results/watermark.json
Detection rate on Chatterbox clips per channel, and false-positive rate on bona fide + other generators.
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.audio import load_any  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=os.path.expanduser("~/work/manifests/corpus_eval.csv"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--n_other", type=int, default=150)
    a = ap.parse_args()
    import perth
    wm = perth.PerthImplicitWatermarker()
    m = pd.read_csv(a.manifest)
    m = m[m.split.isin(["dev", "test"]) & ~m.channel.str.startswith("real_")]
    cb = m[m.generator == "chatterbox"]
    other = m[m.generator != "chatterbox"].groupby("channel").sample(n=a.n_other, random_state=0)
    res = {"note": "Perth implicit watermark (resemble-perth); detection = get_watermark() >= 0.5", "chatterbox": {}, "non_chatterbox": {}}
    for name, df in (("chatterbox", cb), ("non_chatterbox", other)):
        for ch, g in df.groupby("channel"):
            conf = []
            for p in g.path:
                try:
                    conf.append(float(wm.get_watermark(load_any(p), sample_rate=16000)))
                except Exception:
                    conf.append(np.nan)
            conf = np.array(conf)
            res[name][ch] = {"n": int(len(conf)), "detected_rate": round(float(np.nanmean(conf >= 0.5)), 4),
                             "mean_conf": round(float(np.nanmean(conf)), 4)}
            print(name, ch, res[name][ch], flush=True)
    json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
