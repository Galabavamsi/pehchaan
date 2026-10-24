"""Generalisation run v5 (2026-10-24, common/protocol.py note "v5"): every model on every test set, one table each.
  aws s3 sync s3://pehchaan-ml-301745146083-use1/work/scores_v5 realcall/work/retrain_v5/scores
  (iv_test.csv: s3 work/manifests/iv_test.csv once the run ends, or copy it from the box)
  python -m eval.compare_v5

Models: A (ours_v3_rc, served), NII MMS-300M zero-shot (nii0), and the three candidates (ours_n1, ours_a3, ours_n3).
Sarvam IVC was never trained by any of them, so S01's and S02's Sarvam clones are unseen-cloner results; S02 is also
an unseen speaker. Each model's threshold is its EER point on the fixed simulated test sample, as in compare_v4.py.
1. Promotion check: EER on the fixed dev set (dev_sim + dev_rc). A candidate replaces A only if it is lower.
2. Real phone calls (pre-registered test split): EER, genuine flagged, clones caught, Sarvam IVC by speaker.
3. Bench, clean and AMR: per speaker, AUC of genuine vs Sarvam clones (threshold-free) and counts at the threshold.
4. Unseen IndicVoices speakers (seen cloners): EER by channel.
5. MLAAD (engines no model trained on): caught at the threshold, and AUC against unseen IndicVoices genuine speech
   on the same channel.
6. Paid-API unseen voices: caught at the threshold.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from realcall.compare_models import auc, eer_thr
from realcall.settings import REPORTS

MODELS = {"ours_v3_rc": "A (served)", "nii0": "NII zero-shot", "ours_n1": "n1: NII init",
          "ours_a3": "a3: + IndicVoices", "ours_n3": "n3: NII init + IndicVoices"}


def wilson(k, n, z=1.96):
    if not n:
        return [float("nan"), float("nan")]
    p, d = k / n, 1 + z * z / n
    c, h = (p + z * z / (2 * n)) / d, z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 3), round(c + h, 3)]


def frac(mask):
    k, n = int(mask.sum()), int(len(mask))
    return {"k": k, "n": n, "rate": round(k / n, 3) if n else None, "ci95": wilson(k, n)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="realcall/work/retrain_v5/scores")
    ap.add_argument("--v4", default="realcall/work/retrain_v4", help="model A's simulated scores and corpus_eval.csv")
    a = ap.parse_args()
    d, v4 = Path(a.dir), Path(a.v4)

    def sc(prefix, m):
        for f in (d / f"{prefix}__{m}.csv", v4 / "scores" / f"{prefix}__{m}.csv"):
            if f.exists():
                return pd.read_csv(f, usecols=["utt_id", "score"]).drop_duplicates("utt_id")
        return None

    def lab(name, cols):
        for f in (d / name, d.parent / name, v4 / "scores" / name, v4 / name):
            if f.exists():
                x = pd.read_csv(f, usecols=lambda c: c in cols, low_memory=False)
                if "label" in x:
                    return x
        return None

    sim_lab = lab("corpus_eval.csv", ("utt_id", "label"))
    dev_lab = pd.concat([lab(f, ("utt_id", "label")) for f in ("dev_sim.csv", "dev_rc.csv")])
    rc_lab = lab("realcall_test.csv", ("utt_id", "label", "generator", "speaker", "split"))
    bench_lab = lab("bench_clean.csv", ("utt_id", "label", "generator", "speaker"))
    iv_lab = lab("iv_test.csv", ("utt_id", "label", "generator", "channel", "speaker"))
    ml_lab = lab("mlaad_clean.csv", ("utt_id", "label", "generator", "lang"))
    api_lab = lab("api2_test.csv", ("utt_id", "label", "generator", "channel"))

    out = {}
    for m, name in MODELS.items():
        r = {"model": name}
        sim = sc("sim", m)
        if sim is None or sim_lab is None:
            continue
        sim = sim.merge(sim_lab, on="utt_id")
        sim_eer, thr = eer_thr((sim.label == "spoof").astype(int).values, sim.score.values)
        r.update(sim_EER=round(sim_eer, 4), threshold=round(thr, 4), n_sim=int(len(sim)))

        dv = [sc(p, m) for p in ("devsim", "devrc")]
        if all(x is not None for x in dv):
            dv = pd.concat(dv).merge(dev_lab, on="utt_id")
            r["dev_EER"] = round(eer_thr((dv.label == "spoof").astype(int).values, dv.score.values)[0], 4)
            r["n_dev"] = int(len(dv))

        rt = sc("realtest", m)
        if rt is not None and rc_lab is not None:
            t = rt.merge(rc_lab, on="utt_id")
            t = t[t.split == "test"]
            y = (t.label == "spoof").astype(int).values
            g, s = t[t.label == "bonafide"], t[t.label == "spoof"]
            r["real_calls"] = {
                "EER": round(eer_thr(y, t.score.values)[0], 4), "n": int(len(t)),
                "S02_EER": round(eer_thr((t[t.speaker == "S02"].label == "spoof").astype(int).values,
                                         t[t.speaker == "S02"].score.values)[0], 4),
                "genuine_flagged": frac(g.score >= thr), "clones_caught": frac(s.score >= thr),
                "sarvam_ivc_caught": {spk: frac(x.score >= thr) for spk, x in s[s.generator == "sarvam_ivc"].groupby("speaker")}}

        for cond in ("clean", "amr"):
            b = sc(f"bench{cond}", m)
            if b is None or bench_lab is None:
                continue
            b = b.merge(bench_lab, on="utt_id")
            res = {}
            for spk, x in b.groupby("speaker"):
                gen = x[x.label == "bonafide"]
                mic, dialer = gen[~gen.utt_id.str.contains("Ecellular")], gen[gen.utt_id.str.contains("Ecellular")]
                sv = x[x.generator == "sarvam_ivc"]
                res[spk] = {"AUC_genuine_vs_sarvam": round(auc(np.r_[np.zeros(len(gen)), np.ones(len(sv))],
                                                               np.r_[gen.score.values, sv.score.values]), 3) if len(sv) else None,
                            "sarvam_caught": frac(sv.score >= thr), "mic_genuine_flagged": frac(mic.score >= thr),
                            "dialer_genuine_flagged": frac(dialer.score >= thr),
                            "other_clones_caught": {gname: frac(z.score >= thr) for gname, z in
                                                    x[(x.label == "spoof") & (x.generator != "sarvam_ivc")].groupby("generator")}}
            r[f"bench_{cond}"] = res

        iv = sc("ivtest", m)
        if iv is not None and iv_lab is not None:
            v = iv.merge(iv_lab, on="utt_id")
            r["iv_unseen_speakers"] = {
                "EER_all": round(eer_thr((v.label == "spoof").astype(int).values, v.score.values)[0], 4), "n": int(len(v)),
                "EER_by_channel": {ch: round(eer_thr((z.label == "spoof").astype(int).values, z.score.values)[0], 4)
                                   for ch, z in v.groupby("channel")},
                "genuine_flagged": frac(v[v.label == "bonafide"].score >= thr),
                "caught_by_cloner": {gname: frac(z.score >= thr) for gname, z in v[v.label == "spoof"].groupby("generator")}}

        for cond, ivch in (("clean", "clean"), ("amr", "amr")):
            ml = sc(f"mlaad{cond}", m)
            if ml is None or ml_lab is None:
                continue
            x = ml.merge(ml_lab, on="utt_id")
            res = {"caught_all": frac(x.score >= thr),
                   "caught_by_engine": {f"{lang}/{gname}": frac(z.score >= thr) for (lang, gname), z in x.groupby(["lang", "generator"])}}
            if iv is not None and iv_lab is not None:
                bona = iv.merge(iv_lab, on="utt_id")
                bona = bona[(bona.label == "bonafide") & (bona.channel == ivch)]
                res["AUC_vs_iv_genuine"] = round(auc(np.r_[np.zeros(len(bona)), np.ones(len(x))],
                                                     np.r_[bona.score.values, x.score.values]), 3)
                res["n_iv_genuine"] = int(len(bona))
            r[f"mlaad_{cond}"] = res

        ap2 = sc("api2", m)
        if ap2 is not None and api_lab is not None:
            x = ap2.merge(api_lab, on="utt_id")
            r["api2_caught"] = frac(x.score >= thr)
        out[m] = r

    if not out:
        raise SystemExit(f"no scores in {d}")
    pct = lambda v: "  n/a" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:5.1%}"
    kn = lambda f: f"{f['k']}/{f['n']}" if f else "-"
    print("1. Promotion check, fixed dev set (lower is better; replaces A only if lower than A):")
    for r in out.values():
        print(f"   {r['model']:28s} dev EER {pct(r.get('dev_EER'))} (n={r.get('n_dev', 0)})   sim EER {pct(r['sim_EER'])}")
    print("\n2. Real phone calls, pre-registered test split (threshold = sim EER point):")
    for r in out.values():
        c = r.get("real_calls")
        if c:
            print(f"   {r['model']:28s} EER {pct(c['EER'])}  S02 EER {pct(c['S02_EER'])}  genuine flagged {kn(c['genuine_flagged'])}"
                  f"  clones caught {kn(c['clones_caught'])}  Sarvam {({k: kn(v) for k, v in c['sarvam_ivc_caught'].items()})}")
    for cond in ("clean", "amr"):
        print(f"\n3. Bench ({cond}): AUC genuine vs Sarvam clones (0.5 = chance) and Sarvam caught, by speaker:")
        for r in out.values():
            b = r.get(f"bench_{cond}")
            if b:
                print(f"   {r['model']:28s} " + "  ".join(f"{s}: AUC {v['AUC_genuine_vs_sarvam']} caught {kn(v['sarvam_caught'])}"
                                                    f" mic-genuine flagged {kn(v['mic_genuine_flagged'])}" for s, v in b.items()))
    print("\n4. Unseen IndicVoices speakers (seen cloners): EER all / by channel, genuine flagged:")
    for r in out.values():
        v = r.get("iv_unseen_speakers")
        if v:
            print(f"   {r['model']:28s} {pct(v['EER_all'])}  {({k: pct(x).strip() for k, x in v['EER_by_channel'].items()})}"
                  f"  genuine flagged {kn(v['genuine_flagged'])}")
    for cond in ("clean", "amr"):
        print(f"\n5. MLAAD engines no model trained on ({cond}): caught at threshold, AUC vs IndicVoices genuine:")
        for r in out.values():
            x = r.get(f"mlaad_{cond}")
            if x:
                print(f"   {r['model']:28s} caught {kn(x['caught_all'])} ({pct(x['caught_all']['rate'])})  AUC {x.get('AUC_vs_iv_genuine')}")
    print("\n6. Paid-API unseen voices: caught at threshold:")
    for r in out.values():
        if "api2_caught" in r:
            print(f"   {r['model']:28s} {kn(r['api2_caught'])} ({pct(r['api2_caught']['rate'])})")
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "retrain_v5.json").write_text(json.dumps(out, indent=1))
    print(f"\nwrote {REPORTS / 'retrain_v5.json'}")


if __name__ == "__main__":
    main()
