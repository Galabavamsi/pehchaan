"""Paid-API retrain (2026-10-24, common/protocol.py notes): the promotion check and the new engines' unseen voices.
  aws s3 sync s3://pehchaan-ml-301745146083-use1/work/scores_rc realcall/work/retrain_v4/scores
  aws s3 sync s3://pehchaan-ml-301745146083-use1/work/scores_v4 realcall/work/retrain_v4/scores
  python -m eval.compare_v4                       # plus: python -m realcall.compare_models --dir ... --name retrain_v4
1. Promotion check: EER on one fixed dev set (dev_sim + dev_rc), the same rows for model A and both candidates.
2. Unseen voices of the new engines (api2 test split, five channels): share caught at each model's deployed threshold,
   i.e. its EER point on the fixed simulated test sample (as in realcall/compare_models.py).
3. Sarvam IVC clones on real phone calls (test split), caught at the deployed threshold. For A2-ivc only S02 counts as
   an unseen speaker; its S01 number is "seen speaker and seen generator" and is not a generalisation result.
"""
import argparse
import json
from pathlib import Path

import pandas as pd

from realcall.compare_models import eer_thr
from realcall.settings import REPORTS

MODELS = {"ours_v3_rc": "A (current)", "ours_a2": "A2: + paid-API stock voices", "ours_a2_ivc": "A2-ivc: + S01 Sarvam clones"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="realcall/work/retrain_v4/scores")
    a = ap.parse_args()
    d = Path(a.dir)
    sim_lab = pd.read_csv(d / "sim_test.csv", usecols=lambda c: c in ("utt_id", "label"))
    dev_lab = pd.concat([pd.read_csv(d / f, usecols=["utt_id", "label"]) for f in ("dev_sim.csv", "dev_rc.csv")])
    api2_lab = pd.read_csv(d / "api2_test.csv", usecols=["utt_id", "generator", "channel"])
    rc_lab = pd.read_csv(d / "realcall_eval.csv", usecols=lambda c: c in ("utt_id", "label", "generator", "speaker", "split"))
    out = {}
    for m, name in MODELS.items():
        if not (d / f"sim__{m}.csv").exists():
            continue
        sim = pd.read_csv(d / f"sim__{m}.csv").merge(sim_lab, on="utt_id")
        sim_eer, thr = eer_thr((sim.label == "spoof").astype(int).values, sim.score.values)
        r = {"model": name, "sim_EER": round(float(sim_eer), 4), "threshold": round(float(thr), 4)}
        dev = [pd.read_csv(d / f"{p}__{m}.csv") for p in ("devsim", "devrc") if (d / f"{p}__{m}.csv").exists()]
        if len(dev) == 2:
            dv = pd.concat(dev).merge(dev_lab, on="utt_id")
            r["dev_EER"] = round(float(eer_thr((dv.label == "spoof").astype(int).values, dv.score.values)[0]), 4)
            r["n_dev"] = int(len(dv))
        if (d / f"api2__{m}.csv").exists():
            x = pd.read_csv(d / f"api2__{m}.csv").merge(api2_lab, on="utt_id")
            r["api2_caught"] = round(float((x.score >= thr).mean()), 3)
            r["api2_n"] = int(len(x))
            r["api2_caught_by_engine"] = {g: round(float((y.score >= thr).mean()), 3) for g, y in x.groupby("generator")}
            r["api2_caught_by_channel"] = {c: round(float((y.score >= thr).mean()), 3) for c, y in x.groupby("channel")}
        if (d / f"real__{m}.csv").exists():
            t = pd.read_csv(d / f"real__{m}.csv").merge(rc_lab, on="utt_id")
            t = t[(t.split == "test") & (t.generator == "sarvam_ivc")]
            r["sarvam_ivc_real_calls"] = {spk: f"{int((y.score >= thr).sum())}/{len(y)}" for spk, y in t.groupby("speaker")}
        out[m] = r
    if not out:
        raise SystemExit(f"no scores in {d}")
    print("Promotion check (same fixed dev set for every model; lower EER is better):")
    for m, r in out.items():
        print(f"  {r['model']:32s} dev EER {r.get('dev_EER', float('nan')):.1%} (n={r.get('n_dev', 0)})"
              f"   simulated test EER {r['sim_EER']:.1%}")
    print("\nNew engines, unseen voices (api2 test split, all five channels), caught at each model's deployed threshold:")
    for m, r in out.items():
        if "api2_caught" in r:
            print(f"  {r['model']:32s} {r['api2_caught']:.0%} of {r['api2_n']}   by engine {r['api2_caught_by_engine']}")
    print("\nSarvam voice clones on real phone calls (test split), caught / clips by speaker:")
    for m, r in out.items():
        if "sarvam_ivc_real_calls" in r:
            note = ('  S02 = "seen cloner, unseen speaker (S02)"; S01 = seen speaker and seen cloner'
                    if m == "ours_a2_ivc" else "")
            print(f"  {r['model']:32s} {r['sarvam_ivc_real_calls']}{note}")
    (REPORTS / "retrain_v4_comparison.json").write_text(json.dumps(out, indent=1))
    print(f"\nwrote {REPORTS / 'retrain_v4_comparison.json'}")


if __name__ == "__main__":
    main()
