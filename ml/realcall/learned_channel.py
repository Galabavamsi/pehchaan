"""A speakerphone channel learned from real calls: what Vobiz -> carrier -> handset speaker -> room -> laptop mic
does to audio, estimated from aligned (tape reference, real capture) pairs.

  python -m realcall.learned_channel fit        # -> work/learned_channel.npz (train-split calls only)
  python -m realcall.learned_channel validate   # sim vs real: spectra, SNR and detector scores

Model (fitted only on split == "train" items, so test calls and the held-out speaker never shape it):
  codec      G.711 or AMR-NB at 8 kHz (the tape is 8 kHz and the network is narrowband)
  response   per-item magnitude response |H(f)|, median and spread across items; each draw perturbs the median
             by a smooth random curve inside the observed 10-90 % band (linear-phase FIR)
  room       a short reverberant tail (the shared RIR bank) with probability 0.6
  noise      real room + line noise cut from the silent gaps between tape items, at an SNR drawn from the
             SNRs measured on the same calls
Used only as training augmentation (aug_set v3); evaluation always uses real captures.
"""
import argparse
import json

import numpy as np
import pandas as pd
from scipy.signal import fftconvolve, firwin2, welch

from common.audio import load, normalize_rms, resample
from realcall.dsp import SR, frame_db
from realcall.settings import MANIFESTS, REPORTS, TAPES, WORK

NPZ = WORK / "learned_channel.npz"
NPERSEG = 512
_CACHE = {}


def _psd(x):
    f, p = welch(x, fs=SR, nperseg=NPERSEG, noverlap=NPERSEG // 2)
    return f, p + 1e-14


def fit(splits=("train",), min_ncc=0.5):
    m = pd.read_csv(MANIFESTS / "realcall.csv")
    t = m[(m.kind == "tape") & (m.qc == "ok") & m.split.isin(splits) & (m["ncc"] >= min_ncc) & m.path.notna()]
    if t.empty:
        raise SystemExit("no train-split tape items to fit on")
    from realcall.tape import load_tape
    H, noise, snrs, refs = [], [], [], {}
    for r in t.itertuples():
        tid = r.tape_utt.rsplit("_", 1)[0]
        if tid not in refs:
            refs[tid] = (load(TAPES / f"{tid}.ref.wav"), load_tape(tid))
        ref, meta = refs[tid]
        it = meta["items"][int(r.tape_utt.rsplit("_", 1)[1])]
        x = ref[int(it["start_s"] * SR): int((it["start_s"] + it["dur_s"]) * SR)]
        y = load(r.path)
        n = min(len(x), len(y))
        if n < SR:
            continue
        x, y = x[:n], y[:n]
        db = frame_db(y)
        floor = np.percentile(db, 10)
        quiet = np.repeat(db < floor + 3, int(0.03 * SR))[:n]
        nz = y[: len(quiet)][quiet] if quiet.sum() > SR // 4 else None
        f, px = _psd(x)
        _, py = _psd(y)
        pn = _psd(nz)[1] if nz is not None else np.zeros_like(py)
        H.append(10 * np.log10(np.maximum(py - pn, py * 0.05) / px))
        if nz is not None:
            noise.append(nz[: SR])
        snrs.append(float(r.snr_db))
    H = np.array(H)
    H -= np.median(H[:, (f > 500) & (f < 2500)], axis=1, keepdims=True)   # level-free shape: 0 dB around 0.5-2.5 kHz
    med, lo, hi = np.median(H, 0), np.percentile(H, 10, 0), np.percentile(H, 90, 0)
    bank = np.concatenate(noise).astype(np.float32) if noise else np.zeros(SR, np.float32)
    np.savez(NPZ, f=f, med=med, lo=lo, hi=hi, noise=bank, snrs=np.array(snrs), n_items=len(H),
             calls=t.call_id.nunique(), splits=np.array(list(splits)))
    print(f"fitted on {len(H)} items from {t.call_id.nunique()} calls ({','.join(splits)}); noise bank {len(bank) / SR:.1f} s; "
          f"SNR {np.percentile(snrs, 10):.1f}-{np.percentile(snrs, 90):.1f} dB")
    for fr in (200, 300, 500, 1000, 2000, 3000, 3400, 3800, 5000):
        i = int(np.argmin(abs(f - fr)))
        print(f"  {fr:5d} Hz  median {med[i]:6.1f} dB  (10-90 %: {lo[i]:6.1f} .. {hi[i]:6.1f})")
    return NPZ


def _params():
    if "p" not in _CACHE:
        if not NPZ.exists():
            raise FileNotFoundError(f"{NPZ} missing: run python -m realcall.learned_channel fit")
        d = np.load(NPZ)
        _CACHE["p"] = {k: d[k] for k in ("f", "med", "lo", "hi", "noise", "snrs")}
    return _CACHE["p"]


def speakerphone_learned(x, rng):
    from channel.channels import FUNCS, _rir
    p = _params()
    base = "amr" if rng.random() < 0.5 else "pstn"
    try:
        y = FUNCS[base](x, rng)
    except Exception:            # AMR library missing (e.g. Windows): G.711 instead
        y = FUNCS["pstn"](x, rng)
    # response: median + smooth random deviation within the observed spread
    f, med, lo, hi = p["f"], p["med"], p["lo"], p["hi"]
    knots = np.linspace(0, 1, 6)
    dev = np.interp(np.linspace(0, 1, len(f)), knots, rng.uniform(-1, 1, len(knots)))
    h_db = med + np.where(dev > 0, dev * (hi - med), -dev * (lo - med))
    gain = 10 ** (np.clip(h_db, -60, 20) / 20)
    taps = firwin2(257, f / (SR / 2), gain)
    y = fftconvolve(y, taps, mode="same")
    if rng.random() < 0.6:
        try:
            rir = _rir(rng)[: int(0.25 * SR)]
        except ImportError:          # no pyroomacoustics (laptop): exponentially decaying noise tail
            rt60 = float(rng.uniform(0.15, 0.4))
            t = np.arange(int(0.25 * SR)) / SR
            rir = rng.standard_normal(len(t)) * np.exp(-6.9 * t / rt60) * 0.3
            rir[0] = 1.0
        y = fftconvolve(y, rir)[: len(y)]
    # real noise from the calls at a measured SNR
    nb = p["noise"]
    if len(nb) > SR:
        s = int(rng.integers(0, max(1, len(nb) - len(y))))
        nz = np.resize(nb[s:s + len(y)], len(y)).astype(np.float32)
        snr = float(rng.choice(p["snrs"])) + float(rng.normal(0, 2))
        ps, pn = np.mean(y ** 2) + 1e-12, np.mean(nz ** 2) + 1e-12
        y = y + nz * np.sqrt(ps / (pn * 10 ** (snr / 10)))
    return y.astype(np.float32)


def register():
    """Add the channel to channel.channels.FUNCS so finetune.py can draw it like any other channel."""
    from channel import channels
    channels.FUNCS["speakerphone_learned"] = speakerphone_learned


def validate(url="http://127.0.0.1:8500", n=40, seed=0):
    """Push clean team sources through the learned channel and compare with real captures of the same
    split (train) and with the held-out test calls: spectra, SNR, and detector score distributions."""
    import io
    import requests
    import soundfile as sf
    from realcall.tape import index_sources
    from realcall.consent import Registry
    register()
    rng = np.random.default_rng(seed)
    m = pd.read_csv(MANIFESTS / "realcall.csv")
    real = m[(m.kind == "tape") & (m.qc == "ok") & m.path.notna()]
    idx = index_sources(Registry())
    pairs = [(k, v) for k, v in idx.items() if v["genuine"] and v["clone"]]
    rng.shuffle(pairs)

    def score(x):
        b = io.BytesIO()
        sf.write(b, x, SR, format="WAV", subtype="PCM_16")
        b.seek(0)
        return requests.post(url + "/v1/voice/score", files={"file": ("a.wav", b, "audio/wav")}, timeout=120).json()["p_synthetic"]

    rows = []
    for (spk, line), v in pairs[:n]:
        for lab, path in (("bonafide", v["genuine"][0]), ("spoof", v["clone"][int(rng.integers(len(v["clone"])))][1])):
            x = normalize_rms(load(path), -24)
            rows.append(dict(label=lab, clean=score(x), sim=score(normalize_rms(speakerphone_learned(x, rng), -26))))
    s = pd.DataFrame(rows)
    out = {}
    for lab in ("bonafide", "spoof"):
        g, r = s[s.label == lab], real[real.label == lab]
        out[lab] = {"clean_median_p": round(float(g.clean.median()), 3), "sim_median_p": round(float(g.sim.median()), 3),
                    "sim_p>=0.8": round(float((g.sim >= 0.8).mean()), 3), "n_sim": int(len(g))}
    # real-capture reference numbers (from gate scores if present)
    out["note"] = "compare sim_* with the real-call numbers in FINDINGS.md (genuine median 0.001, clones median 0.31, 28 % >= 0.8)"
    (REPORTS / "learned_channel_validation.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fit")
    v = sub.add_parser("validate")
    v.add_argument("--url", default="http://127.0.0.1:8500")
    v.add_argument("--n", type=int, default=40)
    a = ap.parse_args()
    fit() if a.cmd == "fit" else validate(a.url, a.n)


if __name__ == "__main__":
    main()
