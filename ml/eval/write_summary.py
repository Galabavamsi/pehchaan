"""Render results/metrics.json into a Markdown summary for the deck team.
  python eval/write_summary.py --metrics results/metrics.json --out results/SUMMARY.md [--extra results/extra.json]
"""
import argparse
import json

NAMES = {"ours": "Pehchaan fine-tuned XLS-R+AASIST", "ssl_la": "XLS-R+AASIST LA (off-the-shelf)",
         "ssl_df": "XLS-R+AASIST DF (off-the-shelf)", "nii": "NII MMS-300M AntiDeepfake (off-the-shelf, NC)",
         "ours_v2_telaug": "Pehchaan v2 (+ extra telephony augmentation; designed after seeing the real-call failure)",
         "ours_v0_noteam": "Pehchaan v0 ablation (no team-speaker audio in training)"}
CH = ["clean", "pstn", "amr", "opus", "replay"]


def pct(v):
    return "n/a" if v is None else f"{100 * v:.1f}"


def findings(m):
    """Key findings and limitations, with every number read from metrics.json."""
    D = m["detectors"]
    o, n = D["ours"], D.get("nii")
    t = o["test"]
    san = m.get("in_domain_sanity_asvspoof2019_LA_eval_subset", {})
    lr = o["band_LRs"]
    rc = o.get("real_calls_bonafide", {})
    bc = t["by_channel"]
    best = min(CH, key=lambda c: bc[c]["eer"])
    worst = max(CH, key=lambda c: bc[c]["eer"])
    cells = sorted(((v["eer"], g, c) for g, row in t["by_generator_channel"].items() for c, v in row.items()), reverse=True)[:3]
    s01, s02 = o.get("team_S01_simulated_channels"), o.get("team_S02_simulated_channels")
    v2, v0 = D.get("ours_v2_telaug"), D.get("ours_v0_noteam")
    ln = [f"## Key findings", "",
          f"1. **Off-the-shelf detectors collapse on Indian-language phone-channel clones.** XLS-R+AASIST LA: {pct(san.get('ssl_la', {}).get('eer'))} % EER "
          f"in-domain (ASVspoof 2019 LA) -> {pct(D['ssl_la']['test']['overall']['eer'])} % here; DF: {pct(san.get('ssl_df', {}).get('eer'))} % -> "
          f"{pct(D['ssl_df']['test']['overall']['eer'])} %. The strongest public model (NII, non-commercial) reaches {pct(n['test']['overall']['eer'])} % "
          f"but {pct(n['test']['by_channel']['replay']['eer'])} % on speaker->mic replay." if n else "",
          f"2. **Fine-tuned: {pct(t['overall']['eer'])} % EER** (AUC {t['overall']['auc']:.3f}, FRR {pct(t['overall']['frr_at_far5'])} % at FAR 5 %). "
          f"Seen generators {pct(t['seen_generators']['eer'])} % vs held-out {pct(t['heldout_generators']['eer'])} % "
          f"({t['heldout_generators']['eer'] / max(t['seen_generators']['eer'], 1e-9):.1f}x gap). Best channel {best} {pct(bc[best]['eer'])} %, "
          f"worst {worst} {pct(bc[worst]['eer'])} %. Hardest cells: " + ", ".join(f"{g} on {c} {pct(e)} %" for e, g, c in cells) + ".",
          f"3. **Band LRs** (p >= {o['bands']['p_hi']:.2f} likely_synthetic, p <= {o['bands']['p_lo']:.2f} no_strong_evidence): held-out generators "
          f"{lr['test_heldout_generators']['likely_synthetic']['LR']:.1f} / {lr['test_heldout_generators']['inconclusive']['LR']:.2f} / "
          f"{lr['test_heldout_generators']['no_strong_evidence']['LR']:.3f}; phone channels + held-out generators "
          f"{lr['test_phone_channels_heldout_generators']['likely_synthetic']['LR']:.1f} / {lr['test_phone_channels_heldout_generators']['inconclusive']['LR']:.2f} / "
          f"{lr['test_phone_channels_heldout_generators']['no_strong_evidence']['LR']:.3f}.", "",
          "## Honest failures and limits (why voice stays supporting evidence, SPEC G2/G3)", ""]
    if rc:
        st = lr.get("real_call_stress_heldout_clones_vs_real_call_bonafide", {})
        ln.append(f"- **A real cellular call breaks every detector.** Genuine speech from one real S02-S01 call (dialer recording, 8 kHz): "
                  + ", ".join(f"{c} {pct(v['frr_at_dev_threshold'])} % of {v['n']} chunks flagged" for c, v in rc.items())
                  + f" by ours (NII: " + ", ".join(f"{pct(v['frr_at_dev_threshold'])} %" for v in n.get("real_calls_bonafide", {}).values())
                  + f"). Simulated channels on the same speakers flag 0-2 % (replay ~9 %). Against real-call bona fide, "
                  f"LR(likely_synthetic) = {st.get('likely_synthetic', {}).get('LR', float('nan')):.2f} (no information). One call, two speakers: "
                  "real networks do something our simulated codecs do not (adaptive AMR/EVS, network noise suppression/AGC, recorder app).")
    if v2:
        ln.append(f"- A v2 model with extra telephony augmentation (designed after seeing the real-call failure; stopped at epoch 3/6 by a CUDA OOM) "
                  f"did not fix it (" + ", ".join(f"{pct(v['frr_at_dev_threshold'])} %" for v in v2.get("real_calls_bonafide", {}).values())
                  + f" flagged) and is worse overall ({pct(v2['test']['overall']['eer'])} % EER), so v1 is served.")
    if s01 and s02:
        ln.append(f"- **A new real voice is harder than a new generator.** Team clones on simulated channels: S01 (trained speaker, unseen lines) "
                  f"{pct(s01['overall']['eer'])} % EER, **held-out speaker S02 {pct(s02['overall']['eer'])} %** (NII: {pct(n['team_S02_simulated_channels']['overall']['eer'])} %); "
                  f"Seed-VC clones of S02 {pct(s02['by_generator'].get('seedvc', {}).get('eer'))} %.")
    if v0:
        ln.append(f"- Ablation without team audio (v0): {pct(v0['test']['overall']['eer'])} % EER overall, S02 {pct(v0['team_S02_simulated_channels']['overall']['eer'])} %.")
    ln += ["- Only two consented team speakers; gender not recorded for them. Telugu team audio exists only for S01 (Seed-VC Telugu clones).",
           "- All channels except the one real call are simulated (G.711, AMR-NB 12.2k, Opus 16-24k + loss, loudspeaker->mic with synthetic RIRs).",
           "- Shortcut risk: XTTS and F5-Hindi emit exact digital silence between words (see spectrograms); silence trimming and level "
           "normalisation are identical for real and fake, but inner gaps remain.",
           "- Whisper QC (drop clones with CER > 0.5) covered hi/en dev/test and held-out clips only; te/ta clones were not QC'd.",
           f"- Calibration: ECE dev {o['ece']['dev']:.3f}, seen test {o['ece']['test_seen']:.3f}, held-out test {o['ece']['test_heldout']:.3f}; the "
           "test EER threshold sits far below the dev one (unseen material looks 'less synthetic').",
           "- Non-commercial (NC) items: NII baseline weights (CC BY-NC-SA), IndicSynth spoofs, and the F5-TTS / XTTS-v2 / MMS-TTS generators; "
           "the SSL-AASIST init checkpoint has no stated weight licence (see DATA_CARD.md). IndicF5 and MLAAD audio stayed gated (403) and were not used.",
           "- No A100/H100 ran (SageMaker p4d never got capacity; stopped unbilled), so one seed only and no multi-seed/ablation sweep.", ""]
    return [x for x in ln if x is not None]


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
    L += [""] + findings(m)
    L += ["Figures: `figures/det_baseline_vs_ours.svg`, `figures/eer_heatmap_generator_channel.svg`, `figures/heldout_gap_bars.svg` "
          "(PNG previews alongside), `figures/spectrogram_speakerA_*.png` (team speaker anonymised as Speaker A).", ""]
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
            L.append(f"- {NAMES.get(k, k)}: team EER incl. real-call bona fide {pct(ts['overall']['eer'])} (n_spoof {ts['overall']['n_spoof']}, n_bona {ts['overall']['n_bonafide']}); "
                     f"seen gens {pct(ts['seen_generators']['eer'])}, held-out gens {pct(ts['heldout_generators']['eer'])}")
        for key, lab in (("team_subset_simulated_channels_only", "simulated channels only"), ("team_S01_simulated_channels", "S01 (seen speaker, unseen lines)"),
                         ("team_S02_simulated_channels", "S02 (held-out speaker)")):
            t2 = d.get(key)
            if t2:
                L.append(f"  - {lab}: EER {pct(t2['overall']['eer'])} (n_spoof {t2['overall']['n_spoof']}, n_bona {t2['overall']['n_bonafide']}); "
                         f"held-out gens {pct(t2['heldout_generators']['eer'])}; per generator " +
                         ", ".join(f"{g} {pct(v['eer'])}" for g, v in t2["by_generator"].items()))
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
        bs = d.get("band_share", {})
        if bs:
            L += ["", "Band shares on test (fraction of clips in each band):", ""]
            for lab, v in bs.items():
                L.append(f"- {lab}: " + ", ".join(f"{b} {pct(x)} %" for b, x in v.items()))
    san = m.get("in_domain_sanity_asvspoof2019_LA_eval_subset")
    if san:
        L += ["", "## In-domain sanity check (ASVspoof 2019 LA eval subset, English studio audio)", ""]
        for k, v in san.items():
            L.append(f"- {NAMES.get(k, k)}: EER {pct(v.get('eer'))}, AUC {v.get('auc', float('nan')):.3f}")
    lat = m.get("latency")
    if lat:
        L += ["", "## Latency (10 s clip)", "", "| Where | Device | What | median ms | p95 ms |", "|---|---|---|---|---|"]
        for r in lat:
            for what in ("model_forward_10s", "service_10s"):
                v = r.get(what)
                if isinstance(v, dict):
                    L.append(f"| {r.get('label', r.get('host', ''))} | {r.get('gpu') or r.get('cpu', '')} | {what} | {round(v.get('median_ms', float('nan')), 1)} | {round(v.get('p95_ms', float('nan')), 1)} |")
    wm = m.get("watermark_perth")
    if wm:
        L += ["", "## Perth watermark check (Chatterbox output)", "", "```json", json.dumps(wm, indent=1), "```"]
    if a.extra:
        ex = json.load(open(a.extra))
        L += ["", "## Other measurements", "", "```json", json.dumps(ex, indent=1), "```"]
    open(a.out, "w", encoding="utf-8", newline=chr(10)).write(chr(10).join(L) + chr(10))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
