"""Compare v1 and the real-call retraining runs on real calls (test split) and on the simulated test sample.

  aws s3 sync s3://pehchaan-ml-301745146083-use1/work/scores_rc realcall/work/retrain_v3/scores
  python -m realcall.compare_models [--dir realcall/work/retrain_v3/scores]
  python -m realcall.compare_models --dir realcall/work/d2/scores --device D2   # one handset's test calls only

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
    ap.add_argument("--dir", default="realcall/work/retrain_v3/scores",
                    help="folder synced from s3://.../work/scores_rc (scores + labelled manifests, flat)")
    ap.add_argument("--device", help="only real-call test clips captured on this handset (e.g. D2, held out)")
    a = ap.parse_args()
    d = Path(a.dir)
    if not (d / "realcall_eval.csv").exists() and (d / "scores").is_dir():
        d = d / "scores"                      # also accept the parent folder
    lab_cols = ("utt_id", "label", "generator", "speaker", "split", "call_id")
    rce = d / "realcall_eval.csv"
    if rce.exists() and set(lab_cols) <= set(pd.read_csv(rce, nrows=1).columns):
        rc = pd.read_csv(rce, usecols=lambda c: c in lab_cols + ("device",))
    else:                                     # older uploads carried no labels: fall back to the local manifest
        rc = pd.read_csv(MANIFESTS / "realcall.csv")
        rc = rc[(rc.qc == "ok") & rc.path.notna()][[c for c in lab_cols + ("device",) if c in rc]]
    if a.device and "device" not in rc:
        raise SystemExit("--device needs a device column in the real-call labels")
    sim_cols = ("utt_id", "label", "generator", "channel", "heldout")
    st = d / "sim_test.csv"
    if st.exists() and "label" in pd.read_csv(st, nrows=1).columns:
        ce = pd.read_csv(st, usecols=lambda c: c in sim_cols)
    elif (d / "corpus_eval.csv").exists() or (d.parent / "corpus_eval.csv").exists():
        f = d / "corpus_eval.csv" if (d / "corpus_eval.csv").exists() else d.parent / "corpus_eval.csv"
        ce = pd.read_csv(f, usecols=lambda c: c in sim_cols)
    else:
        raise SystemExit(f"no simulated-test labels in {d}: need sim_test.csv with a label column, or corpus_eval.csv")
    rows, out = [], {}
    for m, name in MODELS.items():
        if not (d / f"real__{m}.csv").exists() or not (d / f"sim__{m}.csv").exists():
            continue
        sim = pd.read_csv(d / f"sim__{m}.csv").merge(ce, on="utt_id")
        ys, ss = (sim.label == "spoof").astype(int).values, sim.score.values
        sim_eer, thr = eer_thr(ys, ss)
        ho = sim[sim.heldout.astype(str) == "True"]
        sim_ho = eer_thr((ho.label == "spoof").astype(int).values, ho.score.values)[0] if ho.label.nunique() == 2 else np.nan
        real = pd.read_csv(d / f"real__{m}.csv").merge(rc, on="utt_id")
        t = real[real.split == "test"]
        if a.device:
            t = t[t.device == a.device]
        if t.label.nunique() < 2:
            continue
        yt, st = (t.label == "spoof").astype(int).values, t.score.values
        r_eer, _ = eer_thr(yt, st)
        s02 = t[t.speaker == "S02"]
        s02_eer = eer_thr((s02.label == "spoof").astype(int).values, s02.score.values)[0] if s02.label.nunique() == 2 else np.nan
        caught = float((t[t.label == "spoof"].score >= thr).mean())
        flagged = float((t[t.label == "bonafide"].score >= thr).mean())
        gens = {g: round(float((x.score >= thr).mean()), 2) for g, x in t[t.label == "spoof"].groupby("generator")}
        rows.append(dict(model=name, sim_EER=f"{sim_eer:.1%}", sim_heldout_gen_EER=f"{sim_ho:.1%}",
                         real_test_EER=f"{r_eer:.1%}", real_AUC=f"{auc(yt, st):.3f}", real_S02_EER=f"{s02_eer:.1%}",
                         clones_caught=f"{caught:.0%}", genuine_flagged=f"{flagged:.0%}", n_clips=int(len(t))))
        out[m] = {**rows[-1], "per_generator_caught": gens, "n_test": int(len(t)), "n_test_calls": int(t.call_id.nunique())}
    if not out:
        raise SystemExit("no model has scores with both genuine and clone clips in this slice")
    df = pd.DataFrame(rows)
    scope = f"handset {a.device} only" if a.device else "S02 held-out speaker + S01 calls hashed to test"
    print(f"real-call test split: {out[next(iter(out))]['n_test']} clips from {out[next(iter(out))]['n_test_calls']} calls "
          f"({scope})\n")
    print(df.to_string(index=False))
    print("\nclones caught per generator (deployed threshold):")
    for m in out:
        print(f"  {MODELS[m]:42s} {out[m]['per_generator_caught']}")
    (REPORTS / f"retrain_v3_comparison{'_' + a.device if a.device else ''}.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
