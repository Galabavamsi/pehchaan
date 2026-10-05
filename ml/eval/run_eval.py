"""Full evaluation: calibration, bands, likelihood ratios and sliced metrics for every detector.

  python eval/run_eval.py --eval_manifest corpus_eval.csv --scores ssl_la=S1.csv ssl_df=S2.csv nii=S3.csv ours=S4.csv \
        --ours ours --out results/metrics.json

Calibration: Platt scaling (1-D logistic regression on the raw score) fitted on the DEV split
(seen generators and seen speakers only, ASVspoof excluded). Bands are chosen on DEV too:
  likely_synthetic   p >= p_hi = max(0.8, 98th percentile of dev bona fide p)
  no_strong_evidence p <= p_lo = min(0.2, 5th percentile of dev spoof p)
  inconclusive       otherwise
Measured LR(band) = P(band | spoof) / P(band | bona fide) on TEST, with +0.5 smoothing and bootstrap CIs,
reported for seen generators, held-out generators and all. Nothing on TEST is used to fit anything.
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.protocol import HELDOUT_GENERATORS, HELDOUT_SPEAKERS  # noqa: E402
from eval.metrics import ece, eer, summary  # noqa: E402

BONA = "bonafide"


def platt_fit(s, y):
    from sklearn.linear_model import LogisticRegression
    lr = LogisticRegression(C=1e4, max_iter=1000)
    lr.fit(np.asarray(s).reshape(-1, 1), y)
    return float(lr.coef_[0, 0]), float(lr.intercept_[0])


def sigmoid(z):
    return 1 / (1 + np.exp(-z))


def bands_from_dev(p, y, bona_budget=0.02, spoof_budget=0.05, min_hi=0.8, max_lo=0.2):
    """Band cut points on calibrated p. likely_synthetic needs p >= p_hi with p_hi = max(0.8, 98th pct of dev
    bona fide); no_strong_evidence needs p <= p_lo with p_lo = min(0.2, 5th pct of dev spoofs). The fixed
    floors keep the bands meaningful when dev is almost separable (then quantiles collapse to ~0.5)."""
    p = np.asarray(p)
    y = np.asarray(y)
    pb, ps = p[y == 0], p[y == 1]
    p_hi = max(min_hi, float(np.quantile(pb, 1 - bona_budget))) if len(pb) else 0.9
    p_lo = min(max_lo, float(np.quantile(ps, spoof_budget))) if len(ps) else 0.1
    return p_lo, p_hi


def band_of(p, p_lo, p_hi):
    return np.where(p >= p_hi, "likely_synthetic", np.where(p <= p_lo, "no_strong_evidence", "inconclusive"))


def band_lrs(bands, y, n_boot=500, seed=0):
    bands, y = np.asarray(bands), np.asarray(y)
    names = ["likely_synthetic", "inconclusive", "no_strong_evidence"]
    out = {}
    r = np.random.default_rng(seed)
    pos, neg = np.where(y == 1)[0], np.where(y == 0)[0]

    def lr_of(idx_pos, idx_neg, b):
        ps = ((bands[idx_pos] == b).sum() + 0.5) / (len(idx_pos) + 1.0)
        pb = ((bands[idx_neg] == b).sum() + 0.5) / (len(idx_neg) + 1.0)
        return ps / pb, ps, pb

    for b in names:
        lr, ps, pb = lr_of(pos, neg, b)
        boots = [lr_of(r.choice(pos, len(pos)), r.choice(neg, len(neg)), b)[0] for _ in range(n_boot)] if len(pos) and len(neg) else [np.nan]
        out[b] = {"LR": round(float(lr), 3), "P_band_given_spoof": round(float(ps), 4), "P_band_given_bonafide": round(float(pb), 4),
                  "LR_CI95": [round(float(np.nanpercentile(boots, 2.5)), 3), round(float(np.nanpercentile(boots, 97.5)), 3)]}
    out["n_spoof"], out["n_bonafide"] = int(len(pos)), int(len(neg))
    return out


def slice_metrics(d):
    """d has columns y, score, p, channel, generator, lang, heldout_gen, ..."""
    out = {"overall": summary(d.y, d.score)}
    bona = d[d.y == 0]
    out["by_channel"] = {ch: summary(g.y, g.score) for ch, g in d.groupby("channel") if g.y.nunique() == 2}
    gx = {}
    for (gen, ch), g in d[d.y == 1].groupby(["generator", "channel"]):
        b = bona[bona.channel == ch]
        if len(b) and len(g) >= 5:
            gg = pd.concat([g, b])
            gx.setdefault(gen, {})[ch] = summary(gg.y, gg.score)
    out["by_generator_channel"] = gx
    out["by_generator"] = {gen: summary(pd.concat([g, bona]).y, pd.concat([g, bona]).score)
                           for gen, g in d[d.y == 1].groupby("generator") if len(g) >= 5}
    seen = d[(d.y == 0) | (~d.heldout_gen)]
    held = d[(d.y == 0) | (d.heldout_gen)]
    out["seen_generators"] = summary(seen.y, seen.score)
    out["heldout_generators"] = summary(held.y, held.score)
    out["seen_by_channel"] = {ch: summary(g.y, g.score) for ch, g in seen.groupby("channel") if g.y.nunique() == 2}
    out["heldout_by_channel"] = {ch: summary(g.y, g.score) for ch, g in held.groupby("channel") if g.y.nunique() == 2}
    out["by_lang"] = {l: summary(g.y, g.score) for l, g in d.groupby("lang") if g.y.nunique() == 2 and len(g) >= 20}
    return out


def frr_at(d, thr, by):
    b = d[d.y == 0]
    return {str(k): {"frr": round(float((g.score >= thr).mean()), 4), "n": int(len(g))} for k, g in b.groupby(by) if len(g) >= 5}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval_manifest", required=True)
    ap.add_argument("--scores", nargs="+", required=True, help="name=path.csv")
    ap.add_argument("--ours", default="ours")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dump_scores", default="")
    a = ap.parse_args()
    ev = pd.read_csv(a.eval_manifest)
    ev["y"] = (ev.label == "spoof").astype(int)
    ev["heldout_gen"] = ev.generator.isin(HELDOUT_GENERATORS)
    ev["heldout_spk"] = ev.speaker.astype(str).apply(lambda s: any(h in s for h in HELDOUT_SPEAKERS))
    res = {"definitions": {
        "label": "1 = spoof (synthetic or converted), 0 = bona fide",
        "FAR": "share of spoof clips accepted as bona fide (missed clones)",
        "FRR": "share of bona fide clips flagged as synthetic (false alarms on real people)",
        "frr_at_far5": "FRR when the threshold is set so that FAR = 5 %", "far_at_frr5": "FAR when FRR = 5 %",
        "heldout_generators": sorted(HELDOUT_GENERATORS), "heldout_speakers": sorted(HELDOUT_SPEAKERS),
        "calibration": "Platt scaling fitted on dev (seen generators/speakers), applied to test",
        "bands": "chosen on dev: p_hi = max(0.8, 98th pct of dev bona fide); p_lo = min(0.2, 5th pct of dev spoofs); inconclusive in between; quality-gate failures are inconclusive in the service",
    }, "detectors": {}}
    dumps = []
    for spec in a.scores:
        name, path = spec.split("=", 1)
        s = pd.read_csv(path)
        d = ev.merge(s, on="utt_id", how="inner")
        dev = d[(d.split == "dev") & (d.source != "asv19") & (~d.heldout_gen) & (~d.heldout_spk)]
        test = d[d.split == "test"].copy()
        if len(dev) == 0 or len(test) == 0:
            print("skip", name, len(dev), len(test))
            continue
        A, B = platt_fit(dev.score, dev.y)
        d["p"] = sigmoid(A * d.score + B)
        test["p"] = sigmoid(A * test.score + B)
        dev = d[(d.split == "dev") & (d.source != "asv19") & (~d.heldout_gen) & (~d.heldout_spk)]
        r = {"n_test": int(len(test)), "n_dev": int(len(dev)), "platt": {"a": A, "b": B}}
        r["dev"] = summary(dev.y, dev.score)
        r["test"] = slice_metrics(test)
        r["ece"] = {"dev": round(ece(dev.y, dev.p), 4), "test_all": round(ece(test.y, test.p), 4),
                    "test_seen": round(ece(test[(test.y == 0) | (~test.heldout_gen)].y, test[(test.y == 0) | (~test.heldout_gen)].p), 4),
                    "test_heldout": round(ece(test[(test.y == 0) | (test.heldout_gen)].y, test[(test.y == 0) | (test.heldout_gen)].p), 4)}
        # operating threshold = dev EER threshold, used for FRR fairness slices
        _, thr = eer(dev.y.values, dev.score.values)
        r["dev_eer_threshold"] = thr
        r["frr_at_dev_threshold"] = {"by_lang": frr_at(test, thr, "lang"), "by_gender": frr_at(test, thr, "gender"),
                                     "by_channel": frr_at(test, thr, "channel"), "by_source": frr_at(test, thr, "source")}
        team = test[test.source.isin(["team", "team_clone"])]
        if len(team) and team.y.nunique() == 2:
            r["team_subset"] = slice_metrics(team)
        tb = test[test.source == "team"]
        if len(tb):
            r["team_bonafide_flag_rate_at_dev_threshold"] = {"by_speaker": frr_at(tb, thr, "speaker"), "by_section": frr_at(tb, thr, "section"),
                                                            "by_channel": frr_at(tb, thr, "channel")}
        calls = test[test.channel.str.startswith("real_")]
        if len(calls):
            r["real_calls_bonafide"] = {ch: {"frr_at_dev_threshold": round(float((g.score >= thr).mean()), 4), "n": int(len(g)),
                                             "mean_p": round(float(g.p.mean()), 4)} for ch, g in calls.groupby("channel")}
        p_lo, p_hi = bands_from_dev(dev.p.values, dev.y.values)
        r["bands"] = {"p_lo": round(p_lo, 4), "p_hi": round(p_hi, 4)}
        test["band"] = band_of(test.p.values, p_lo, p_hi)
        ph = test[test.channel.isin(["pstn", "amr", "opus", "replay"])]
        ph_held = ph[(ph.y == 0) | (ph.heldout_gen)]
        r["band_LRs"] = {
            "test_all": band_lrs(test.band, test.y),
            "test_seen_generators": band_lrs(test[(test.y == 0) | (~test.heldout_gen)].band, test[(test.y == 0) | (~test.heldout_gen)].y),
            "test_heldout_generators": band_lrs(test[(test.y == 0) | (test.heldout_gen)].band, test[(test.y == 0) | (test.heldout_gen)].y),
            "test_phone_channels": band_lrs(ph.band, ph.y) if ph.y.nunique() == 2 else None,
            "test_phone_channels_heldout_generators": band_lrs(ph_held.band, ph_held.y) if ph_held.y.nunique() == 2 else None,
        }
        r["band_share"] = {lab: test[test.y == yv].band.value_counts(normalize=True).round(4).to_dict()
                           for lab, yv in (("spoof", 1), ("bonafide", 0))}
        rc = test[test.channel.str.startswith("real_")]
        if len(rc) and ph_held.y.nunique() == 2:
            # Real-network stress test: numerator = held-out-generator clones on simulated phone channels,
            # denominator = genuine speech from the real cellular call (no clones exist over a real network yet)
            mix = pd.concat([ph_held[ph_held.y == 1], rc])
            r["band_share"]["real_call_bonafide"] = rc.band.value_counts(normalize=True).round(4).to_dict()
            r["band_LRs"]["real_call_stress_heldout_clones_vs_real_call_bonafide"] = band_lrs(mix.band, mix.y)
        res["detectors"][name] = r
        test["detector"] = name
        dumps.append(test[["utt_id", "detector", "y", "score", "p", "band", "channel", "generator", "lang", "split", "source",
                           "heldout_gen", "heldout_spk", "speaker", "gender"]])
        print(name, "test EER", r["test"]["overall"].get("eer"), "seen", r["test"]["seen_generators"].get("eer"),
              "heldout", r["test"]["heldout_generators"].get("eer"), "ECE", r["ece"]["test_all"], flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=1, default=float)
    if a.dump_scores and dumps:
        pd.concat(dumps).to_csv(a.dump_scores, index=False)


if __name__ == "__main__":
    main()
