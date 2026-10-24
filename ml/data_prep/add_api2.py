"""Add the 2026-10-24 paid-API training set (common/protocol.py note of that date) to the corpus, on the GPU box.
  python data_prep/add_api2.py      # -> ~/work/manifests/corpus_src_v4.csv, corpus_eval_v4.csv

Inputs (synced from S3 by infra/retrain_v4.sh):
  ~/work/api2_src/manifest.csv + <engine>/<id>.flac    stock-voice clips from gen/run_api.py build2 (16 kHz FLAC)
  ~/work/api2_src/sarvam_ivct/*.flac                   Sarvam clones of S01 (consented), train split
  ~/data/fleurs/<lang>/train.tsv + audio/train/train/  FLEURS train speech for the languages that had no bona fide
                                                       training audio (otherwise "this language = fake" is learnable)
Every new clip goes through the same trimming and RMS normalisation as the rest of the corpus (build_corpus._prep),
and dev/test clips get the same five channel versions (build_corpus._chan).
"""
import os
import random
import sys
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.protocol import CHANNELS, api2_split  # noqa: E402
from data_prep.build_corpus import EVAL, SRC, _chan, _prep  # noqa: E402

H = Path.home()
W = H / "work"
A2 = W / "api2_src"
NEW_FLEURS = {"bn_in": "bn", "gu_in": "gu", "kn_in": "kn", "ml_in": "ml", "mr_in": "mr", "pa_in": "pa", "or_in": "od"}
FLEURS_PER_LANG = 400


def rows_api2():
    m = pd.read_csv(A2 / "manifest.csv")
    rows = []
    for r in m.itertuples(index=False):
        p = A2 / r.engine / f"{r.id}.flac"
        if not p.exists():
            continue
        assert api2_split(r.engine, r.voice) == r.split, r.id   # the split on disk must match the registered rule
        rows.append(dict(utt_id=r.id, path=str(p), label="spoof", generator=r.engine, speaker=r.voice, lang=r.lang,
                         line_id=r.line_id, text=r.text, gender="", source="api2", split=r.split, heldout=False,
                         native_channel="clean"))
    for p in sorted((A2 / "sarvam_ivct").glob("*.flac")):
        _, spk, lang, fid = p.stem.split("__")
        rows.append(dict(utt_id=p.stem, path=str(p), label="spoof", generator="sarvam_ivct", speaker=spk, lang=lang,
                         line_id=f"fleurs{fid[1:]}", text="", gender="", source="api2", split="train", heldout=False,
                         native_channel="clean"))
    return pd.DataFrame(rows)


def rows_new_fleurs():
    rnd = random.Random(24)
    rows = []
    for code, lang in NEW_FLEURS.items():
        d = H / "data/fleurs" / code
        tsv, adir = d / "train.tsv", d / "audio" / "train" / "train"
        if not tsv.exists() or not adir.exists():
            print("missing FLEURS train for", code)
            continue
        got = []
        for line in tsv.read_text(encoding="utf-8").splitlines():
            p = line.split("\t")
            if len(p) < 7 or not (adir / p[1]).exists():
                continue
            got.append(dict(utt_id=f"fleurs_{code}_train_{Path(p[1]).stem}", path=str(adir / p[1]), label="bonafide",
                            generator="bonafide", speaker=f"fleurs_{code}_unk", lang=lang, line_id=f"fleurs_{code}_{p[0]}",
                            text=p[2], gender=p[6].lower(), source="fleurs", split="train", heldout=False,
                            native_channel="clean"))
        rows += rnd.sample(got, min(FLEURS_PER_LANG, len(got)))
    return pd.DataFrame(rows)


def main():
    old_src = pd.read_csv(W / "manifests/corpus_src.csv")
    old_ev = pd.read_csv(W / "manifests/corpus_eval.csv")
    new = pd.concat([rows_api2(), rows_new_fleurs()], ignore_index=True)
    new = new[~new.utt_id.isin(old_src.utt_id)].drop_duplicates("utt_id")
    with Pool(8) as pool:
        ok = dict(pool.map(_prep, list(zip(new.utt_id, new.path)), chunksize=16))
    new = new[new.utt_id.map(ok)].copy()
    new["src16"] = [str(SRC / f"{u}.wav") for u in new.utt_id]
    print("new rows", len(new))
    print(new.groupby(["split", "label", "generator"]).size().to_string())

    ev = new[new.split.isin(["dev", "test"])]
    tasks = [(u, ch) for u in ev.utt_id for ch in CHANNELS]
    for ch in CHANNELS:
        (EVAL / ch).mkdir(parents=True, exist_ok=True)
    with Pool(8) as pool:
        pool.map(_chan, tasks, chunksize=16)
    erows = []
    for r in ev.to_dict("records"):
        for ch in CHANNELS:
            d = dict(r, channel=ch, src_utt_id=r["utt_id"], utt_id=f"{r['utt_id']}__{ch}", path=str(EVAL / ch / f"{r['utt_id']}.wav"))
            erows.append(d)
    em = pd.DataFrame(erows)
    em = em[em.path.map(os.path.exists)]
    print("new eval rows", len(em))

    pd.concat([old_src, new], ignore_index=True).to_csv(W / "manifests/corpus_src_v4.csv", index=False)
    pd.concat([old_ev, em], ignore_index=True).to_csv(W / "manifests/corpus_eval_v4.csv", index=False)
    # the new test split on its own (unseen voices of the new engines), for scoring before and after
    em[em.split == "test"][["utt_id", "path", "label", "generator", "channel", "speaker", "lang"]].to_csv(
        W / "manifests/api2_test.csv", index=False)
    print("wrote corpus_src_v4.csv, corpus_eval_v4.csv, api2_test.csv")


if __name__ == "__main__":
    main()
