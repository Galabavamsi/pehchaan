"""Merge run_eval output with latency, watermark, corpus and training facts into results/metrics.json.
  python eval/assemble_metrics.py --eval_json E.json --latency L1.json L2.json --watermark W.json \
      --corpus_src corpus_src.csv --corpus_eval corpus_eval.csv --runs ~/runs/ours_v1 ... --out metrics.json
"""
import argparse
import json
import os

import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval_json", required=True)
    ap.add_argument("--latency", nargs="*", default=[])
    ap.add_argument("--watermark", default="")
    ap.add_argument("--corpus_src", required=True)
    ap.add_argument("--corpus_eval", required=True)
    ap.add_argument("--runs", nargs="*", default=[])
    ap.add_argument("--asv19", nargs="*", default=[], help="name=metrics json of the in-domain sanity check")
    ap.add_argument("--notes", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    m = json.load(open(a.eval_json))
    src = pd.read_csv(a.corpus_src, low_memory=False)
    ev = pd.read_csv(a.corpus_eval, low_memory=False)
    m["generated_at"] = pd.Timestamp.now(tz="Asia/Kolkata").isoformat(timespec="minutes")
    m["corpus"] = {
        "source_utterances_by_split_label": {f"{k[0]}|{k[1]}": int(v) for k, v in src.groupby(["split", "label"]).size().items()},
        "spoof_by_generator_split": {g: {s: int(n) for s, n in d.items()} for g, d in
                                     src[src.label == "spoof"].groupby(["generator", "split"]).size().unstack(fill_value=0).to_dict("index").items()},
        "eval_rows_by_split_channel_label": {f"{k[0]}|{k[1]}|{k[2]}": int(v) for k, v in ev.groupby(["split", "channel", "label"]).size().items()},
        "team": {"speakers": sorted(src[src.source == "team"].speaker.astype(str).unique().tolist()),
                 "bona_fide_segments": int((src.source == "team").sum()), "clone_clips": int((src.source == "team_clone").sum())},
    }
    m["latency"] = [json.load(open(p)) for p in a.latency if os.path.exists(p)]
    if a.watermark and os.path.exists(a.watermark):
        m["watermark_perth"] = json.load(open(a.watermark))
    m["training_runs"] = {}
    for r in a.runs:
        lp = os.path.join(r, "log.json")
        if os.path.exists(lp):
            log = json.load(open(lp))
            args = json.load(open(os.path.join(r, "args.json"))) if os.path.exists(os.path.join(r, "args.json")) else {}
            best = json.load(open(os.path.join(r, "best.json"))) if os.path.exists(os.path.join(r, "best.json")) else {}
            m["training_runs"][os.path.basename(r.rstrip("/"))] = {"args": {k: args.get(k) for k in ("init", "epochs", "steps_per_epoch", "bs", "lr_ssl", "lr_head", "no_channel_aug", "rawboost_p", "aug_set", "exclude_sources", "seed")},
                                                                  "best": best, "dev_eer_by_epoch": [round(e["dev_eer_mean"], 4) for e in log]}
    for spec in a.asv19:
        n, p = spec.split("=", 1)
        if os.path.exists(p):
            m.setdefault("in_domain_sanity_asvspoof2019_LA_eval_subset", {})[n] = json.load(open(p))
    if a.notes:
        m["notes"] = a.notes
    json.dump(m, open(a.out, "w"), indent=1, default=float)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
