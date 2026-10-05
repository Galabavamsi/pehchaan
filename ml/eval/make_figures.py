"""Publication SVG figures for the deck (run on the laptop after pulling results).

  python ml/eval/make_figures.py --metrics ml/results/metrics.json --scores ml/results/test_scores.csv --out ml/results/figures

Palette (validated with the dataviz validator against paper #f5f0e6): ours = orange #e8742a, baseline = slate
#6b7280 (passes CVD for the two-series comparison; orange is below 3:1 contrast so every series is also
direct-labelled). Extra baselines reuse slate with a dashed line + direct label (secondary encoding).
Heatmaps use a single-hue sequential ramp (paper -> red #c8372d), with the value printed in each cell.
"""
import argparse
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from scipy.stats import norm  # noqa: E402

PAPER, INK, ORANGE, SLATE, TEAL, RED = "#f5f0e6", "#1b1f24", "#e8742a", "#6b7280", "#13796f", "#c8372d"
MUTED = "#4b5563"
plt.rcParams.update({
    "svg.fonttype": "none", "font.family": ["Inter", "Space Grotesk", "DejaVu Sans"], "font.size": 15,
    "axes.titlesize": 17, "axes.labelsize": 15, "xtick.labelsize": 13, "ytick.labelsize": 13, "legend.fontsize": 13,
    "figure.facecolor": PAPER, "axes.facecolor": PAPER, "savefig.facecolor": PAPER, "text.color": INK,
    "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED, "axes.edgecolor": "#cfc8b8",
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e4dccb", "grid.linewidth": 0.8,
})
NAMES = {"ours": "Pehchaan (fine-tuned)", "ssl_la": "XLS-R+AASIST (LA, off-the-shelf)",
         "ssl_df": "XLS-R+AASIST (DF, off-the-shelf)", "nii": "NII MMS-300M AntiDeepfake (off-the-shelf)"}
CH_NAMES = {"clean": "Clean 16 kHz", "pstn": "PSTN G.711", "amr": "AMR-NB 12.2k", "opus": "Opus (WhatsApp-like)", "replay": "Speaker→mic replay"}
GEN_NAMES = {"f5": "F5-TTS", "f5hi": "F5-Hindi", "indicf5": "IndicF5", "xtts": "XTTS-v2", "cosyvoice2": "CosyVoice2", "mms": "MMS-TTS",
             "kokoro": "Kokoro", "seedvc": "Seed-VC (VC) †", "chatterbox": "Chatterbox †", "sarvam": "Sarvam Bulbul †",
             "openai": "OpenAI TTS †", "deepgram": "Deepgram Aura †"}


def det_xy(y, s):
    y, s = np.asarray(y), np.asarray(s)
    thr = np.unique(np.quantile(s, np.linspace(0, 1, 400)))
    far = np.array([(s[y == 1] < t).mean() for t in thr])
    frr = np.array([(s[y == 0] >= t).mean() for t in thr])
    lim = 1e-3
    return norm.ppf(np.clip(far, lim, 1 - lim)), norm.ppf(np.clip(frr, lim, 1 - lim))


def fig_det(sc, metrics, out, baselines):
    ticks = [0.01, 0.02, 0.05, 0.1, 0.2, 0.4]
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.6), sharey=True)
    for ax, (title, mask_fn) in zip(axes, [("Seen generators", lambda d: (d.y == 0) | (~d.heldout_gen)),
                                          ("Held-out generators (never trained on)", lambda d: (d.y == 0) | (d.heldout_gen))]):
        for name in baselines + ["ours"]:
            d = sc[sc.detector == name]
            d = d[mask_fn(d) & ~d.channel.str.startswith("real_")]
            if d.y.nunique() < 2:
                continue
            x, yv = det_xy(d.y, d.score)
            is_ours = name == "ours"
            ls = "-" if (is_ours or name == baselines[0]) else "--"
            ax.plot(x, yv, color=ORANGE if is_ours else SLATE, lw=2.4 if is_ours else 2, ls=ls)
            key = "seen_generators" if "Seen" in title else "heldout_generators"
            e = metrics["detectors"][name]["test"][key]["eer"]
            # direct label at the EER point
            i = np.argmin(np.abs(x - yv))
            ax.annotate(f"{NAMES.get(name, name).split(' (')[0]}  EER {e * 100:.1f}%", (x[i], yv[i]),
                        xytext=(8, 6 if is_ours else -16), textcoords="offset points", fontsize=12.5,
                        color=INK, fontweight="bold" if is_ours else "normal")
            ax.scatter([x[i]], [yv[i]], s=40, color=ORANGE if is_ours else SLATE, zorder=5, edgecolor=PAPER, linewidth=1.5)
        ax.plot(norm.ppf([1e-3, 0.6]), norm.ppf([1e-3, 0.6]), color="#cfc8b8", lw=1, ls=":")
        ax.set_xticks(norm.ppf(ticks), [f"{t * 100:g}%" for t in ticks])
        ax.set_yticks(norm.ppf(ticks), [f"{t * 100:g}%" for t in ticks])
        ax.set_xlim(norm.ppf(0.005), norm.ppf(0.6))
        ax.set_ylim(norm.ppf(0.005), norm.ppf(0.6))
        ax.set_title(title, loc="left", fontweight="bold")
        ax.set_xlabel("Missed clones (FAR)")
    axes[0].set_ylabel("Real callers flagged (FRR)")
    fig.suptitle("DET curves on Indian-language test audio, all simulated channels pooled", x=0.01, ha="left", fontsize=17)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "det_baseline_vs_ours.svg"))
    plt.close(fig)


def fig_heatmap(metrics, out, det_names):
    cmap = LinearSegmentedColormap.from_list("eer", ["#fbf8f2", "#f2c9a8", RED])
    chans = ["clean", "pstn", "amr", "opus", "replay"]
    n = len(det_names)
    fig, axes = plt.subplots(1, n, figsize=(6.4 * n, 7.2), squeeze=False)
    for ax, name in zip(axes[0], det_names):
        gx = metrics["detectors"][name]["test"]["by_generator_channel"]
        gens = [g for g in GEN_NAMES if g in gx] + sorted(g for g in gx if g not in GEN_NAMES)
        M = np.array([[gx[g].get(c, {}).get("eer", np.nan) if gx[g].get(c) else np.nan for c in chans] for g in gens], dtype=float)
        ax.imshow(M, cmap=cmap, vmin=0, vmax=0.5, aspect="auto")
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                if np.isfinite(M[i, j]):
                    ax.text(j, i, f"{M[i, j] * 100:.0f}", ha="center", va="center", fontsize=12.5,
                            color="white" if M[i, j] > 0.33 else INK)
        ax.set_xticks(range(len(chans)), [CH_NAMES[c].replace(" (", "\n(").replace(" ", "\n", 1) if len(CH_NAMES[c]) > 12 else CH_NAMES[c] for c in chans], fontsize=12)
        ax.set_yticks(range(len(gens)), [GEN_NAMES.get(g, g) for g in gens], fontsize=13)
        ax.grid(False)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_title(NAMES.get(name, name), loc="left", fontweight="bold", fontsize=15)
    fig.suptitle("EER (%) by generator × channel   († = held-out generator, never seen in training)", x=0.01, ha="left", fontsize=16)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "eer_heatmap_generator_channel.svg"))
    plt.close(fig)


def fig_gap(metrics, out, base):
    chans = ["clean", "pstn", "amr", "opus", "replay"]
    fig, ax = plt.subplots(figsize=(12.8, 5.4))
    w = 0.2
    groups = [(base, "seen_by_channel", SLATE, None), (base, "heldout_by_channel", SLATE, "///"),
              ("ours", "seen_by_channel", ORANGE, None), ("ours", "heldout_by_channel", ORANGE, "///")]
    for k, (name, key, col, hatch) in enumerate(groups):
        v = [metrics["detectors"][name]["test"][key].get(c, {}).get("eer", np.nan) for c in chans]
        xs = np.arange(len(chans)) + (k - 1.5) * w
        bars = ax.bar(xs, np.array(v) * 100, width=w - 0.02, color=col if hatch is None else PAPER, edgecolor=col,
                      hatch=hatch, linewidth=1.6)
        for x, val in zip(xs, v):
            if np.isfinite(val):
                ax.text(x, val * 100 + 0.8, f"{val * 100:.0f}", ha="center", va="bottom", fontsize=11.5, color=INK)
    ax.set_xticks(range(len(chans)), [CH_NAMES[c] for c in chans])
    ax.set_ylabel("EER (%)  - lower is better")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(facecolor=SLATE, edgecolor=SLATE, label=f"{NAMES[base].split(' (')[0]} - seen generators"),
                       Patch(facecolor=PAPER, edgecolor=SLATE, hatch="///", label="… held-out generators"),
                       Patch(facecolor=ORANGE, edgecolor=ORANGE, label="Pehchaan fine-tuned - seen generators"),
                       Patch(facecolor=PAPER, edgecolor=ORANGE, hatch="///", label="… held-out generators")],
              frameon=False, ncol=2, loc="upper left", fontsize=12.5)
    ax.set_ylim(0, max(55, ax.get_ylim()[1]))
    ax.set_title("The held-out-generator gap: unseen cloners are much harder, on every channel", loc="left", fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "heldout_gap_bars.svg"))
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", required=True)
    ap.add_argument("--scores", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--baselines", default="ssl_la,nii")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    m = json.load(open(a.metrics))
    sc = pd.read_csv(a.scores)
    sc["heldout_gen"] = sc.heldout_gen.astype(bool)
    bl = [b for b in a.baselines.split(",") if b in m["detectors"]]
    if "ours" in m["detectors"]:
        fig_det(sc, m, a.out, bl)
        fig_heatmap(m, a.out, [bl[0], "ours"])
        fig_gap(m, a.out, bl[0])
    else:
        fig_heatmap(m, a.out, bl)
    print("figures ->", a.out)


if __name__ == "__main__":
    main()
