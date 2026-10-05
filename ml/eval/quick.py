"""Quick metrics: python eval/quick.py --manifest M.csv --scores S.csv [--by generator channel]"""
import argparse
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eval.metrics import summary  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--scores", required=True, nargs="+")
    ap.add_argument("--by", nargs="*", default=[])
    a = ap.parse_args()
    m = pd.read_csv(a.manifest)
    for sp in a.scores:
        s = pd.read_csv(sp)
        d = m.merge(s, on="utt_id")
        d["y"] = (d["label"] == "spoof").astype(int)
        print(f"== {os.path.basename(sp)}  n={len(d)}")
        print("  overall", json.dumps(summary(d.y, d.score)))
        for col in a.by:
            for k, g in d.groupby(col):
                if g.y.nunique() < 2:
                    # compare this group's spoofs (or bona fides) against all bona fides (or spoofs)
                    other = d[d.y != g.y.iloc[0]]
                    g = pd.concat([g, other])
                r = summary(g.y, g.score)
                print(f"  {col}={k}: eer={r.get('eer')} auc={r.get('auc')} nS={r['n_spoof']} nB={r['n_bonafide']}")


if __name__ == "__main__":
    main()
