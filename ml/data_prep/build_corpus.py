"""Assemble every source utterance into one manifest, normalise it, and pre-compute channel versions
of the dev/test sets.

  python data_prep/build_corpus.py            # -> ~/work/manifests/corpus_src.csv, corpus_eval.csv

1. Collect rows (bona fide + spoof) from FLEURS, ASVspoof19 subset, IndicSynth subset, SynRef, commercial
   stock-voice TTS, team recordings and team clones. Each row gets: label, generator, speaker, lang,
   line_id, split, heldout flag, source.
2. Every clip -> 16 kHz mono, same silence trimming for real and fake (no leading-silence shortcut),
   written to ~/work/src16/<utt_id>.wav.
3. dev/test clips -> 5 channels (clean, pstn, amr, opus, replay), deterministic per (utt, channel),
   written to ~/work/eval16/<channel>/<utt_id>.wav. Training applies channels on the fly instead.
   Real phone calls (team section E) are already phone-channel audio: they are kept as-is under the
   channels real_cellular / real_whatsapp.
Generated clips whose Whisper CER vs. the intended text is > 0.5 (when QC is available) are dropped, so
broken generations cannot make detection look easy.
"""
import glob
import json
import os
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.audio import load_any, save, trim_silence, normalize_rms  # noqa: E402
from common.protocol import CHANNELS, HELDOUT_GENERATORS, HELDOUT_SPEAKERS, team_split  # noqa: E402

H = Path.home()
W = H / "work"
SRC = W / "src16"
EVAL = W / "eval16"
GEN_NAME = {"cosy": "cosyvoice2", "cb": "chatterbox"}


def rows_fleurs():
    m = pd.read_csv(W / "manifests/fleurs.csv")
    keep = []
    rnd = np.random.default_rng(0)
    for (lang, split), g in m.groupby(["lang", "split"]):
        main = lang in ("hi", "te", "ta", "en")
        n = {"train": 10 ** 9, "dev": 120 if main else 50, "test": 250 if main else 100}[split]
        keep.append(g.sample(n=min(n, len(g)), random_state=int(rnd.integers(1e6))))
    m = pd.concat(keep)
    m["heldout"] = False
    return m


def rows_asv19():
    m = pd.read_csv(W / "manifests/asv19.csv")
    m["heldout"] = False
    m["split"] = m["split"].replace({"eval": "asv_eval"})
    return m


def rows_jobs(pattern, source, gen_from_id=True):
    out = []
    for jf in sorted(glob.glob(str(W / "jobs" / pattern))):
        for l in open(jf, encoding="utf-8"):
            j = json.loads(l)
            if not os.path.exists(j["out"]) or os.path.getsize(j["out"]) < 2000:
                continue
            gen = j["id"].split("__")[0] if gen_from_id else j.get("engine")
            gen = GEN_NAME.get(gen, gen)
            spk = j.get("speaker_id") or f"syn_{j.get('voice', 'unk')}"
            split = j.get("split", "test")
            if source == "team_clone" and gen in HELDOUT_GENERATORS:
                split = "test"  # never trained/calibrated on, so every held-out clone can be a test item
            out.append(dict(utt_id=j["id"].replace(" ", "_"), path=j["out"], label="spoof", generator=gen,
                            speaker=spk, lang=j.get("lang"), line_id=j.get("line_id", ""), text=j.get("text", ""),
                            gender=j.get("gender", ""), source=source, split=split,
                            heldout=gen in HELDOUT_GENERATORS or spk in HELDOUT_SPEAKERS))
    return pd.DataFrame(out)


def rows_api():
    out = []
    for jf in sorted(glob.glob(str(W / "gen/api/jobs_*.jsonl"))):
        for l in open(jf, encoding="utf-8"):
            j = json.loads(l)
            p = W / "gen/api" / j["engine"] / os.path.basename(j["out"].replace("\\", "/"))
            if not p.exists() or p.stat().st_size < 2000:
                continue
            out.append(dict(utt_id=j["id"], path=str(p), label="spoof", generator=j["engine"], speaker=f"stock_{j['engine']}_{j['voice']}",
                            lang=j["lang"], line_id=j["line_id"], text=j["text"], gender=j.get("gender", ""), source="commercial",
                            split="test", heldout=True))
    return pd.DataFrame(out)


def rows_team():
    p = W / "manifests/team_bona.csv"
    if not p.exists():
        return pd.DataFrame()
    m = pd.read_csv(p)
    m["split"] = [team_split(s, l, sec) for s, l, sec in zip(m.speaker, m.line_id, m.section)]
    m["heldout"] = m.speaker.astype(str).apply(lambda s: any(h in s for h in HELDOUT_SPEAKERS))
    return m


def rows_indicsynth():
    p = W / "manifests/indicsynth.csv"
    if not p.exists():
        return pd.DataFrame()
    m = pd.read_csv(p)
    m["heldout"] = False
    return m


def qc_filter(df):
    """Drop generated clips whose ASR CER > 0.5 (if a QC file exists for them)."""
    qcs = [pd.read_csv(f) for f in glob.glob(str(W / "qc/*.csv"))]
    if not qcs:
        df["qc_cer"] = np.nan
        return df
    qc = pd.concat(qcs).drop_duplicates("id", keep="last").rename(columns={"id": "utt_id", "cer": "qc_cer"})[["utt_id", "qc_cer"]]
    df = df.merge(qc, on="utt_id", how="left")
    bad = (df.label == "spoof") & (df.qc_cer > 0.5)
    print("QC drops (CER>0.5):", df[bad].groupby("generator").size().to_dict())
    return df[~bad]


def _prep(args):
    uid, path = args
    out = SRC / f"{uid}.wav"
    if out.exists():
        return uid, True
    try:
        x = load_any(path)
        x = trim_silence(x)
        if len(x) < 16000 * 0.8:
            return uid, False
        save(out, normalize_rms(x, -26))
        return uid, True
    except Exception:
        return uid, False


def _chan(args):
    uid, ch = args
    from channel.channels import apply, seeded_rng
    out = EVAL / ch / f"{uid}.wav"
    if out.exists():
        return True
    try:
        x = load_any(SRC / f"{uid}.wav")
        y = apply(x, ch, seeded_rng(uid, ch))
        save(out, y)
        return True
    except Exception as e:  # noqa
        print("chan fail", uid, ch, repr(e)[:100])
        return False


def main():
    SRC.mkdir(parents=True, exist_ok=True)
    parts = [rows_fleurs(), rows_asv19(), rows_indicsynth(), rows_team(),
             rows_jobs("synref_stock_*.jsonl", "synref"), rows_jobs("synref_clone_*.jsonl", "synref"),
             rows_jobs("team_*.jsonl", "team_clone"), rows_jobs("heldout_*.jsonl", "heldout_extra"), rows_api()]
    df = pd.concat([p for p in parts if len(p)], ignore_index=True)
    df = df.drop_duplicates("utt_id")
    df = qc_filter(df)
    with Pool(8) as pool:
        ok = dict(pool.map(_prep, list(zip(df.utt_id, df.path)), chunksize=16))
    df = df[df.utt_id.map(ok)].copy()
    df["src16"] = [str(SRC / f"{u}.wav") for u in df.utt_id]
    df.to_csv(W / "manifests/corpus_src.csv", index=False)
    print(df.groupby(["split", "label"]).size())
    print(df[df.label == "spoof"].groupby(["generator", "split"]).size().unstack(fill_value=0))

    ev = df[df.split.isin(["dev", "test"])]
    tasks, rows = [], []
    for r in ev.itertuples(index=False):
        native = getattr(r, "native_channel", "clean")
        if isinstance(native, str) and native.startswith(("cellular", "whatsapp")):
            chs = [f"real_{native}"]
        else:
            chs = CHANNELS
        for ch in chs:
            if ch.startswith("real_"):
                (EVAL / ch).mkdir(parents=True, exist_ok=True)
                dst = EVAL / ch / f"{r.utt_id}.wav"
                if not dst.exists():
                    os.link(SRC / f"{r.utt_id}.wav", dst)
            else:
                (EVAL / ch).mkdir(parents=True, exist_ok=True)
                tasks.append((r.utt_id, ch))
            d = r._asdict()
            d.update(channel=ch, eval_id=f"{r.utt_id}__{ch}", path=str(EVAL / ch / f"{r.utt_id}.wav"))
            rows.append(d)
    with Pool(8) as pool:
        pool.map(_chan, tasks, chunksize=16)
    em = pd.DataFrame(rows)
    em = em[em.path.map(os.path.exists)]
    em = em.rename(columns={"utt_id": "src_utt_id"}).rename(columns={"eval_id": "utt_id"})
    em.to_csv(W / "manifests/corpus_eval.csv", index=False)
    print("eval rows", len(em))
    print(em.groupby(["split", "channel", "label"]).size().unstack(fill_value=0))


if __name__ == "__main__":
    main()
