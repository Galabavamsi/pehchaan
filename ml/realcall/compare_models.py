"""Compare v1 and the real-call retraining runs on real calls (test split) and on the simulated test sample.

  python -m realcall.compare_models [--dir realcall/work/retrain_v3]

Scores are spoof logit differences from eval/score.py (higher = more synthetic). Real-call metrics use the
pre-registered test split only (S02 = held-out speaker; S01 calls hashed to test). "Deployed" numbers use each
model's own threshold from the simulated test sample (its EER point there), applied unchanged to real calls,
which is how a model calibrated on our corpus would behave in the field.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from realcall.settings import MANIFESTS, REPORTS

MODELS = {"ours_v1": "v1 (Round 1, served)", "ours_v1_rc": "B: + real-call clips", "ours_v3": "C: + learned channel",
          "ours_v3_rc": "A: + learned channel + real-call clips"}


def eer_thr(y, s):
    """EER and its threshold; y=1 for spoof, s higher = more spoof."""
    order = np.argsort(-s)
    s, y = s[order], y[order]
    P, N = y.sum(), (1 - y).sum()
    tp, fp = np.cumsum(y), np.cumsum(1 - y)
    fnr, fpr = 1 - tp / P, fp / N
    i = int(np.argmin(np.abs(fnr - fpr)))
    return float((fnr[i] + fpr[i]) / 2), float(s[i])


def auc(y, s):
    from scipy.stats import mannwhitneyu
    a, b = s[y == 1], s[y == 0]
    return float(mannwhitneyu(a, b).statistic / (len(a) * len(b)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="realcall/work/retrain_v3")
    a = ap.parse_args()
    d = Path(a.dir)
    rc = pd.read_csv(MANIFESTS / "realcall.csv")
    rc = rc[(rc.qc == "ok") & rc.path.notna()][["utt_id", "label", "generator", "speaker", "split", "call_id"]]
    ce = pd.read_csv(d / "corpus_eval.csv", usecols=lambda c: c in ("utt_id", "label", "generator", "channel", "heldout"))
    rows, out = [], {}
    for m, name in MODELS.items():
        if not (d / "scores" / f"real__{m}.csv").exists():
            continue
        sim = pd.read_csv(d / "scores" / f"sim__{m}.csv").merge(ce, on="utt_id")
        ys, ss = (sim.label == "spoof").astype(int).values, sim.score.values
        sim_eer, thr = eer_thr(ys, ss)
        ho = sim[sim.heldout.astype(str) == "True"]
        sim_ho = eer_thr((ho.label == "spoof").astype(int).values, ho.score.values)[0] if ho.label.nunique() == 2 else np.nan
        real = pd.read_csv(d / "scores" / f"real__{m}.csv").merge(rc, on="utt_id")
        t = real[real.split == "test"]
        yt, st = (t.label == "spoof").astype(int).values, t.score.values
        r_eer, _ = eer_thr(yt, st)
        s02 = t[t.speaker == "S02"]
        s02_eer = eer_thr((s02.label == "spoof").astype(int).values, s02.score.values)[0]
        caught = float((t[t.label == "spoof"].score >= thr).mean())
        flagged = float((t[t.label == "bonafide"].score >= thr).mean())
        gens = {g: round(float((x.score >= thr).mean()), 2) for g, x in t[t.label == "spoof"].groupby("generator")}
        rows.append(dict(model=name, sim_EER=f"{sim_eer:.1%}", sim_heldout_gen_EER=f"{sim_ho:.1%}",
                         real_test_EER=f"{r_eer:.1%}", real_AUC=f"{auc(yt, st):.3f}", real_S02_EER=f"{s02_eer:.1%}",
                         clones_caught=f"{caught:.0%}", genuine_flagged=f"{flagged:.0%}"))
        out[m] = {**rows[-1], "per_generator_caught": gens, "n_test": int(len(t)), "n_test_calls": int(t.call_id.nunique())}
    df = pd.DataFrame(rows)
    print(f"real-call test split: {out[next(iter(out))]['n_test']} clips from {out[next(iter(out))]['n_test_calls']} calls "
          f"(S02 held-out speaker + S01 calls hashed to test)\n")
    print(df.to_string(index=False))
    print("\nclones caught per generator (deployed threshold):")
    for m in out:
        print(f"  {MODELS[m]:42s} {out[m]['per_generator_caught']}")
    (REPORTS / "retrain_v3_comparison.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
