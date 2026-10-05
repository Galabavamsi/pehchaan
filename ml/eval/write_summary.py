"""Render results/metrics.json into a Markdown summary for the deck team.
  python eval/write_summary.py --metrics results/metrics.json --out results/SUMMARY.md [--extra results/extra.json]
"""
import argparse
import json

NAMES = {"ours": "Pehchaan fine-tuned XLS-R+AASIST", "ssl_la": "XLS-R+AASIST LA (off-the-shelf)",
         "ssl_df": "XLS-R+AASIST DF (off-the-shelf)", "nii": "NII MMS-300M AntiDeepfake (off-the-shelf, NC)"}
CH = ["clean", "pstn", "amr", "opus", "replay"]


def pct(v):
    return "n/a" if v is None else f"{100 * v:.1f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--extra", default="")
    a = ap.parse_args()
    m = json.load(open(a.metrics))
    D = m["detectors"]
    L = ["# Pehchaan voice-clone detector: results", "",
         "All numbers are on held-out TEST data; calibration and band thresholds were fitted on DEV only.",
         "FAR = clones accepted as real; FRR = real people flagged. EER in %. Channels are simulated unless marked real.", ""]
    L += ["## Headline (all test clips, 5 channels pooled, one global threshold)", "",
          "| Detector | EER | AUC | FRR @ FAR 5 % | FRR @ FAR 1 % | EER seen gens | EER held-out gens | ECE (test) |", "|---|---|---|---|---|---|---|---|"]
    for k, d in D.items():
        t = d["test"]
        L.append(f"| {NAMES.get(k, k)} | {pct(t['overall']['eer'])} | {t['overall']['auc']:.3f} | {pct(t['overall']['frr_at_far5'])} | "
                 f"{pct(t['overall']['frr_at_far1'])} | {pct(t['seen_generators']['eer'])} | {pct(t['heldout_generators']['eer'])} | {d['ece']['test_all']:.3f} |")
    L += ["", "## EER by channel", "", "| Detector | " + " | ".join(CH) + " |", "|---|" + "---|" * len(CH)]
    for k, d in D.items():
        bc = d["test"]["by_channel"]
        L.append(f"| {NAMES.get(k, k)} | " + " | ".join(pct(bc.get(c, {}).get("eer")) for c in CH) + " |")
    L += ["", "## Held-out generators by channel (EER)", "", "| Detector | " + " | ".join(CH) + " |", "|---|" + "---|" * len(CH)]
    for k, d in D.items():
        bc = d["test"]["heldout_by_channel"]
        L.append(f"| {NAMES.get(k, k)} | " + " | ".join(pct(bc.get(c, {}).get("eer")) for c in CH) + " |")
    for k in (["ours"] if "ours" in D else []) + [x for x in D if x != "ours"][:1]:
        gx = D[k]["test"]["by_generator_channel"]
        L += ["", f"## Generator x channel EER: {NAMES.get(k, k)}", "", "| Generator | " + " | ".join(CH) + " |", "|---|" + "---|" * len(CH)]
        for g, row in gx.items():
            L.append(f"| {g} | " + " | ".join(pct(row.get(c, {}).get("eer")) for c in CH) + " |")
    L += ["", "## By language (EER)", ""]
    for k, d in D.items():
        L.append(f"- {NAMES.get(k, k)}: " + ", ".join(f"{l} {pct(v['eer'])}" for l, v in d["test"]["by_lang"].items()))
    L += ["", "## Team speakers (consented; S02 held out) and real phone calls", ""]
    for k, d in D.items():
        ts = d.get("team_subset")
        if ts:
            L.append(f"- {NAMES.get(k, k)}: team EER {pct(ts['overall']['eer'])} (n_spoof {ts['overall']['n_spoof']}, n_bona {ts['overall']['n_bonafide']}); "
                     f"seen gens {pct(ts['seen_generators']['eer'])}, held-out gens {pct(ts['heldout_generators']['eer'])}")
        rc = d.get("real_calls_bonafide")
        if rc:
            L.append(f"  - real calls (bona fide only), share flagged at the dev EER threshold: " +
                     ", ".join(f"{c} {pct(v['frr_at_dev_threshold'])} % of {v['n']}" for c, v in rc.items()))
    if "ours" in D:
        d = D["ours"]
        L += ["", "## Bands and measured likelihood ratios (Pehchaan detector)", "",
              f"Thresholds from dev: `no_strong_evidence` if p <= {d['bands']['p_lo']:.3f}; `likely_synthetic` if p >= {d['bands']['p_hi']:.3f}; otherwise `inconclusive`.",
              "LR = P(band | clone) / P(band | real), on test, with 95 % bootstrap CI.", "",
              "| Test slice | likely_synthetic | inconclusive | no_strong_evidence |", "|---|---|---|---|"]
        for sl, v in d["band_LRs"].items():
            if not v:
                continue
            L.append(f"| {sl} (n_spoof {v['n_spoof']}, n_bona {v['n_bonafide']}) | " + " | ".join(
                f"{v[b]['LR']:.2f} [{v[b]['LR_CI95'][0]:.2f}-{v[b]['LR_CI95'][1]:.2f}]" for b in ("likely_synthetic", "inconclusive", "no_strong_evidence")) + " |")
        L += ["", "FRR at the dev EER threshold (fairness slices):", ""]
        for key in ("by_lang", "by_gender", "by_source"):
            L.append(f"- {key}: " + ", ".join(f"{g} {pct(v['frr'])} % (n={v['n']})" for g, v in d["frr_at_dev_threshold"][key].items()))
    if a.extra:
        ex = json.load(open(a.extra))
        L += ["", "## Other measurements", "", "```json", json.dumps(ex, indent=1), "```"]
    open(a.out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
