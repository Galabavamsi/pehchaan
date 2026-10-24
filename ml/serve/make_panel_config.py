"""Build serve/panel_config.json: per-detector thresholds and scales for the side-by-side detector panel.

  python serve/make_panel_config.py        (run from ml/, after the score files below exist)

Every detector is put on the same footing with the rule already used in realcall/compare_models.py: its
threshold is its EER point on the same 6,000-clip simulated test sample, applied unchanged everywhere else.
The fused score is an equal-weight mean of z = (score - threshold) / std over the panel's models, so no fusion
weight is fitted on any data. Inputs (scores are spoof-minus-bona-fide logits, higher = more synthetic):
  realcall/work/d2/scores/sim__ours_v1.csv, sim__ours_v3_rc.csv (the sample itself), corpus_eval.csv (labels)
  realcall/work/panel/{nii_mms300m,ssl_la}__eval.csv (full eval set; filtered to the same sample)
"""
import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

ML = Path(__file__).resolve().parents[1]
W = ML / "realcall" / "work"
OUT = ML / "serve" / "panel_config.json"

MODELS = {
    "v1": {"name": "Pehchaan v1 (Round 1)", "scores": W / "d2/scores/sim__ours_v1.csv",
           "trained_on": "consented Indic corpus, simulated phone channels"},
    "A": {"name": "Pehchaan A (real-call retrain)", "scores": W / "d2/scores/sim__ours_v3_rc.csv",
          "trained_on": "v1 corpus + learned speakerphone channel + real-call clips"},
    "nii": {"name": "NII AntiDeepfake MMS-300M (off the shelf)", "scores": W / "panel/nii_mms300m__eval.csv",
            "trained_on": "NII's 56k h genuine + 18k h artefact speech; never saw our data", "licence": "CC BY-NC-SA 4.0"},
    "la": {"name": "XLS-R + AASIST LA (off the shelf)", "scores": W / "panel/ssl_la__eval.csv",
           "trained_on": "ASVspoof 2019 LA (English); never saw our data"},
}


def eer_thr(y, s):
    order = np.argsort(-s)
    s, y = s[order], y[order]
    tp, fp = np.cumsum(y), np.cumsum(1 - y)
    fnr, fpr = 1 - tp / y.sum(), fp / (1 - y).sum()
    i = int(np.argmin(np.abs(fnr - fpr)))
    return float((fnr[i] + fpr[i]) / 2), float(s[i])


def main():
    labels = pd.read_csv(W / "d2/scores/corpus_eval.csv", usecols=["utt_id", "label", "heldout"])
    sample = pd.read_csv(MODELS["v1"]["scores"])[["utt_id"]]
    df = sample.merge(labels, on="utt_id")
    for m, spec in MODELS.items():
        s = pd.read_csv(spec["scores"]).drop_duplicates("utt_id").rename(columns={"score": m})
        df = df.merge(s[["utt_id", m]], on="utt_id", how="left")
    y = (df.label == "spoof").astype(int).values
    cfg = {"sample": f"{len(df)} clips of the simulated test set (same sample as realcall/compare_models.py)",
           "rule": "threshold = EER point on this sample; fused = mean of (score - threshold) / std",
           "models": {}, "fused": {}}
    for m, spec in MODELS.items():
        ok = df[m].notna().values
        eer, thr = eer_thr(y[ok], df[m].values[ok])
        ho = ok & (df.heldout.astype(str) == "True").values
        eer_ho = eer_thr(y[ho], df[m].values[ho])[0] if y[ho].min() != y[ho].max() else None
        cfg["models"][m] = {k: v for k, v in spec.items() if k != "scores"} | {
            "threshold": round(thr, 4), "std": round(float(np.std(df[m].values[ok])), 4),
            "sim_eer": round(eer, 4), "sim_eer_heldout_generators": None if eer_ho is None else round(eer_ho, 4),
            "n": int(ok.sum())}
    for k in range(2, len(MODELS) + 1):
        for combo in combinations(MODELS, k):
            ok = df[list(combo)].notna().all(axis=1).values
            z = np.mean([(df[m].values[ok] - cfg["models"][m]["threshold"]) / cfg["models"][m]["std"] for m in combo], axis=0)
            eer, thr = eer_thr(y[ok], z)
            cfg["fused"]["+".join(sorted(combo))] = {"threshold": round(thr, 4), "sim_eer": round(eer, 4), "n": int(ok.sum())}
    OUT.write_text(json.dumps(cfg, indent=1))
    for m, v in cfg["models"].items():
        print(f"{m:4s} thr {v['threshold']:8.3f}  std {v['std']:6.3f}  sim EER {v['sim_eer']:.1%}  held-out {v['sim_eer_heldout_generators']}  n={v['n']}")
    for c, v in cfg["fused"].items():
        print(f"fused {c:14s} thr {v['threshold']:7.3f}  sim EER {v['sim_eer']:.1%}  n={v['n']}")


if __name__ == "__main__":
    main()
