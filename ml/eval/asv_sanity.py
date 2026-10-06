"""In-domain sanity check: detector metrics on the ASVspoof 2019 LA eval subset (English studio audio).
  python eval/asv_sanity.py --scores ~/work/scores/ssl_la__asv19_eval.csv --out ~/work/results/asv19_ssl_la.json
"""
import argparse
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eval.metrics import summary  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--scores", required=True)
ap.add_argument("--manifest", default=os.path.expanduser("~/work/manifests/asv19_eval.csv"))
ap.add_argument("--out", required=True)
a = ap.parse_args()
d = pd.read_csv(a.manifest).merge(pd.read_csv(a.scores), on="utt_id")
r = summary((d.label == "spoof").astype(int), d.score)
r["note"] = "stratified subset of ASVspoof 2019 LA eval (1,500 bona fide, ~2,990 spoof, attacks A07-A19)"
json.dump(r, open(a.out, "w"), indent=1)
print(r)
