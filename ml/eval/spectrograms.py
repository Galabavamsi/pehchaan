"""Anonymised example spectrograms: a consented team speaker's real line vs. clones of the SAME line.
  python eval/spectrograms.py --speaker S01 --line E06 --out ~/work/results/figures
Speaker identity is never shown (labelled "Speaker A"). PNG, 1600 px wide.
"""
import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.audio import load_any  # noqa: E402

PAPER, INK = "#f5f0e6", "#1b1f24"
GEN = {"bonafide": "Real recording", "xtts": "Clone: XTTS-v2", "f5": "Clone: F5-TTS", "f5hi": "Clone: F5-Hindi",
       "cosyvoice2": "Clone: CosyVoice2", "chatterbox": "Clone: Chatterbox (held-out)", "seedvc": "Voice conversion: Seed-VC (held-out)"}


def logmel(x, sr=16000):
    import librosa
    S = librosa.feature.melspectrogram(y=x, sr=sr, n_fft=1024, hop_length=160, n_mels=96, fmax=8000)
    return librosa.power_to_db(S, ref=np.max)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--speaker", default="S01")
    ap.add_argument("--lines", nargs="+", default=["E06", "H05"])
    ap.add_argument("--channels", nargs="+", default=["clean", "amr"])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    ev = pd.read_csv(os.path.expanduser("~/work/manifests/corpus_eval.csv"), low_memory=False)
    src = pd.read_csv(os.path.expanduser("~/work/manifests/corpus_src.csv"), low_memory=False)
    plt.rcParams.update({"svg.fonttype": "none", "font.family": ["Inter", "DejaVu Sans"], "font.size": 13,
                         "figure.facecolor": PAPER, "text.color": INK})
    for line in a.lines:
        rows = src[(src.speaker.astype(str) == a.speaker) & (src.line_id == line)]
        if not len(rows):
            print("no rows for", line)
            continue
        order = ["bonafide", "xtts", "f5", "f5hi", "cosyvoice2", "chatterbox", "seedvc"]
        rows = rows.assign(o=rows.generator.map({g: i for i, g in enumerate(order)})).sort_values("o").drop_duplicates("generator")
        rows = rows[rows.generator.isin(order)].head(4)
        for ch in a.channels:
            fig, axes = plt.subplots(1, len(rows), figsize=(16, 3.6), sharey=True)
            axes = np.atleast_1d(axes)
            for ax, r in zip(axes, rows.itertuples()):
                if ch == "clean":
                    x = load_any(r.src16)
                else:
                    e = ev[ev.utt_id == f"{r.utt_id}__{ch}"]
                    if len(e):
                        x = load_any(e.path.iloc[0])
                    else:  # train-split line: no pre-rendered eval copy, so apply the same channel here
                        from channel.channels import apply, seeded_rng
                        x = apply(load_any(r.src16), ch, seeded_rng(r.utt_id, ch))
                x = x[: 16000 * 6]
                ax.imshow(logmel(x), origin="lower", aspect="auto", cmap="magma", extent=[0, len(x) / 16000, 0, 96])
                ax.set_title(GEN.get(r.generator, r.generator), fontsize=13, loc="left")
                ax.set_xlabel("seconds")
                ax.set_yticks([])
            axes[0].set_ylabel("mel bins (0-8 kHz)")
            fig.suptitle(f"Speaker A, line {line}, channel: {ch}  (real vs clones of the same sentence)", x=0.01, ha="left", fontsize=14)
            fig.tight_layout()
            fn = os.path.join(a.out, f"spectrogram_speakerA_{line}_{ch}.png")
            fig.savefig(fn, dpi=100)
            plt.close(fig)
            print("wrote", fn)


if __name__ == "__main__":
    main()
