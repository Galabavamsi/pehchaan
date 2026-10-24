"""IndicVoices Hindi: many real speakers and their clones (common/protocol.py note "v5", 2026-10-24), on the GPU box.

  python data_prep/add_iv.py select   # ~/data/iv/hindi/train-*.parquet -> ~/work/iv_src/{real,ref}/*.wav,
                                      #   ~/work/iv_src/select.csv, ~/work/jobs/iv_{xtts,f5hi}.jsonl
  (gen/run_xtts.py and gen/run_f5.py --hindi run those jobs into ~/work/gen/iv/<generator>/)
  python data_prep/add_iv.py build    # -> ~/work/manifests/corpus_src_v5.csv, corpus_eval_v5.csv, iv_test.csv

ai4bharat/IndicVoices is CC-BY-4.0 (AI4Bharat, "IndicVoices", arXiv:2403.01926). Its voices are cloned only with
open-source cloners, for detector research, and the clones stay in the research corpus (CLAUDE.md consent rule of
2026-10-24). Every clip gets the same trimming and RMS normalisation as the rest of the corpus (build_corpus._prep),
and dev/test clips get the same five channel versions (build_corpus._chan).
"""
import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.protocol import CHANNELS, IV_GENERATORS, IV_MAX_SPEAKERS, IV_SALT, IV_SHARDS, iv_split  # noqa: E402

H = Path.home()
W = H / "work"
IV_DATA = H / "data" / "iv" / "hindi"
IV_SRC = W / "iv_src"
GEN = W / "gen" / "iv"
JOBS = W / "jobs"
META = ["normalized", "duration", "speaker_id", "scenario", "gender"]
REF_S = (6.0, 15.0)     # reference utterance for cloning
TGT_S = (3.0, 12.0)     # target utterances: real rows, and the text each clone reads
N_TARGETS = 3
DUR_RATIO = (0.5, 2.0)  # a clone outside this multiple of its real twin's duration is dropped


def shard_files():
    return [IV_DATA / f"train-{k:05d}-of-00082.parquet" for k in IV_SHARDS]


def _hash(s):
    return hashlib.sha1(s.encode()).hexdigest()


def clean_text(t):
    t = re.sub(r"\[[^\]]*\]|<[^>]*>", " ", str(t if isinstance(t, str) else ""))
    return re.sub(r"\s+", " ", t).strip()


def mostly_devanagari(t):
    letters = [c for c in t if c.isalpha()]
    return len(letters) >= 8 and sum("ऀ" <= c <= "ॿ" for c in letters) / len(letters) >= 0.9


def read_meta():
    import pyarrow.parquet as pq
    frames = []
    for f in shard_files():
        if not f.exists():
            print("missing shard", f.name)
            continue
        t = pq.read_table(f, columns=META).to_pandas()
        t["shard"] = f.name
        t["row"] = np.arange(len(t))
        frames.append(t)
    return pd.concat(frames, ignore_index=True)


def pick(m):
    """One reference and N_TARGETS targets per eligible speaker, seeded by the speaker id; eligible speakers in a
    salted hash order (a different salt from the split, so the cap doesn't skew the split), first IV_MAX_SPEAKERS."""
    m = m.assign(tx=m.normalized.map(clean_text))
    m = m[m.tx.map(mostly_devanagari)]
    chosen = []
    for spk, g in m.groupby("speaker_id"):
        g = g.sort_values(["shard", "row"])   # the picks must not depend on the order rows were read in
        rng = np.random.default_rng(int(_hash(f"{IV_SALT}:pick:{spk}")[:8], 16))
        refs = g[g.duration.between(*REF_S)]
        if not len(refs):
            continue
        ref = refs.iloc[int(rng.integers(len(refs)))]
        tg = g[g.duration.between(*TGT_S) & (g.index != ref.name)]
        if len(tg) < N_TARGETS:
            continue
        tg = tg.iloc[np.sort(rng.choice(len(tg), N_TARGETS, replace=False))]
        chosen.append((_hash(f"{IV_SALT}:order:{spk}"), spk, ref, tg))
    print(f"speakers in shards {m.speaker_id.nunique()}, eligible {len(chosen)}, cap {IV_MAX_SPEAKERS}")
    chosen.sort(key=lambda c: c[0])
    return chosen[:IV_MAX_SPEAKERS]


def key(r):
    return f"s{int(r.shard.split('-')[1]):02d}r{int(r.row):05d}"


def tag(speaker_id):
    """Corpus speaker name: IndicVoices ids look like "S4259869900354210", and some old code matches team speakers
    ("S01", "S02") as substrings, so the leading S goes."""
    return "iv" + (speaker_id[1:] if speaker_id.startswith("S") else speaker_id)


def select():
    m = read_meta()
    rows = []
    for _, spk_id, ref, tg in pick(m):
        spk, split = tag(spk_id), iv_split(spk_id)
        rows.append(dict(utt_id=f"iv_ref__{spk}", speaker=spk, speaker_id=spk_id, split=split, role="ref", text=ref.tx,
                         duration=ref.duration, gender=ref.gender, scenario=ref.scenario, shard=ref.shard, row=ref.row,
                         key=key(ref), path=str(IV_SRC / "ref" / f"{spk}.wav")))
        for _, r in tg.iterrows():
            uid = f"iv_real__{spk}__{key(r)}"
            rows.append(dict(utt_id=uid, speaker=spk, speaker_id=spk_id, split=split, role="target", text=r.tx,
                             duration=r.duration, gender=r.gender, scenario=r.scenario, shard=r.shard, row=r.row,
                             key=key(r), path=str(IV_SRC / "real" / f"{uid}.wav")))
    sel = pd.DataFrame(rows)
    extract(sel)
    sel = sel[sel.path.map(os.path.exists)]
    ok_spk = set(sel[sel.role == "ref"].speaker) & set(sel[sel.role == "target"].speaker)
    sel = sel[sel.speaker.isin(ok_spk)]
    IV_SRC.mkdir(parents=True, exist_ok=True)
    sel.to_csv(IV_SRC / "select.csv", index=False)

    JOBS.mkdir(parents=True, exist_ok=True)
    refs = sel[sel.role == "ref"].set_index("speaker")
    for g in IV_GENERATORS:
        with open(JOBS / f"iv_{g}.jsonl", "w", encoding="utf-8") as f:
            for r in sel[sel.role == "target"].itertuples():
                cid = f"iv_{g}__{r.speaker}__{r.key}"
                f.write(json.dumps({"id": cid, "text": r.text, "lang": "hi", "ref_wav": refs.path[r.speaker],
                                    "ref_text": refs.text[r.speaker], "out": str(GEN / g / f"{cid}.wav"),
                                    "seed": int(_hash(cid)[:6], 16) % 10000}, ensure_ascii=False) + "\n")
    t = sel[sel.role == "target"]
    print(f"selected {sel.speaker.nunique()} speakers, {len(t)} targets ({t.duration.sum() / 3600:.2f} h)")
    print(t.drop_duplicates("speaker").groupby(["split", "gender"]).size().to_string())
    print("scenarios:", t.scenario.value_counts().to_dict())


def extract(sel):
    """Decode the chosen rows' audio from the parquet shards to 16 kHz mono WAV."""
    import pyarrow.parquet as pq
    from common.audio import decode_bytes, save
    for d in ("real", "ref"):
        (IV_SRC / d).mkdir(parents=True, exist_ok=True)
    bad = 0
    for shard, g in sel.groupby("shard"):
        col = pq.read_table(IV_DATA / shard, columns=["audio_filepath"]).column("audio_filepath")
        for r in g.itertuples():
            if os.path.exists(r.path):
                continue
            try:
                x, _, _ = decode_bytes(col[int(r.row)].as_py()["bytes"])
                save(r.path, x)
            except Exception as e:  # keep going; the speaker is dropped below if its reference is missing
                bad += 1
                print("decode fail", r.utt_id, repr(e)[:120])
        del col
    print("decode failures", bad)


def build():
    import soundfile as sf
    from data_prep.build_corpus import EVAL, SRC, _chan, _prep
    sel = pd.read_csv(IV_SRC / "select.csv", dtype={"speaker": str, "speaker_id": str})
    rows, drops = [], Counter()
    for r in sel[sel.role == "target"].itertuples():
        base = dict(speaker=r.speaker, lang="hi", line_id=f"iv_{r.key}", text=r.text, gender=str(r.gender).lower(),
                    split=r.split, heldout=False, native_channel="clean")
        rows.append(dict(base, utt_id=r.utt_id, path=r.path, label="bonafide", generator="bonafide", source="iv"))
        real_s = sf.info(r.path).duration
        for g in IV_GENERATORS:
            cid = f"iv_{g}__{r.speaker}__{r.key}"
            p = GEN / g / f"{cid}.wav"
            if not p.exists():
                drops[f"{g}: not generated"] += 1
                continue
            ratio = sf.info(str(p)).duration / real_s
            if not DUR_RATIO[0] <= ratio <= DUR_RATIO[1]:
                drops[f"{g}: duration {'short' if ratio < 1 else 'long'}"] += 1
                continue
            rows.append(dict(base, utt_id=cid, path=str(p), label="spoof", generator=g, source="iv_clone"))
    print("clones dropped:", dict(drops) or "none")
    new = pd.DataFrame(rows)
    old_src = pd.read_csv(W / "manifests/corpus_src_v4.csv", low_memory=False)
    old_ev = pd.read_csv(W / "manifests/corpus_eval_v4.csv", low_memory=False)
    new = new[~new.utt_id.isin(old_src.utt_id)].drop_duplicates("utt_id")
    with Pool(8) as pool:
        ok = dict(pool.map(_prep, list(zip(new.utt_id, new.path)), chunksize=16))
    new = new[new.utt_id.map(ok)].copy()
    new["src16"] = [str(SRC / f"{u}.wav") for u in new.utt_id]
    print("new rows", len(new))
    print(new.groupby(["split", "label", "generator"]).size().to_string())

    ev = new[new.split.isin(["dev", "test"])]
    for ch in CHANNELS:
        (EVAL / ch).mkdir(parents=True, exist_ok=True)
    with Pool(8) as pool:
        pool.map(_chan, [(u, ch) for u in ev.utt_id for ch in CHANNELS], chunksize=16)
    em = pd.DataFrame([dict(r, channel=ch, src_utt_id=r["utt_id"], utt_id=f"{r['utt_id']}__{ch}",
                            path=str(EVAL / ch / f"{r['utt_id']}.wav"))
                       for r in ev.to_dict("records") for ch in CHANNELS])
    em = em[em.path.map(os.path.exists)]
    print("new eval rows", len(em))

    pd.concat([old_src, new], ignore_index=True).to_csv(W / "manifests/corpus_src_v5.csv", index=False)
    pd.concat([old_ev, em], ignore_index=True).to_csv(W / "manifests/corpus_eval_v5.csv", index=False)
    # unseen IndicVoices speakers on their own (seen cloners), for scoring every model
    em[em.split == "test"][["utt_id", "path", "label", "generator", "channel", "speaker", "lang"]].to_csv(
        W / "manifests/iv_test.csv", index=False)
    print("wrote corpus_src_v5.csv, corpus_eval_v5.csv, iv_test.csv")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["select", "build"])
    {"select": select, "build": build}[ap.parse_args().step]()
