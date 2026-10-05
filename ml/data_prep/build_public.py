"""Build manifests for the public datasets downloaded to ~/data.

Outputs (CSV, one row per source utterance, before channel simulation) in ~/work/manifests/:
  fleurs.csv   bona fide, google/fleurs (CC-BY-4.0); split = FLEURS split (train/dev/test)
  asv19.csv    ASVspoof 2019 LA (ODC-By 1.0) stratified subset; split = train/dev/eval
Columns: utt_id,path,label,generator,speaker,lang,line_id,text,gender,source,split
label: bonafide | spoof
"""
import csv
import os
import random
from pathlib import Path

import pandas as pd

H = Path.home()
OUT = H / "work/manifests"
OUT.mkdir(parents=True, exist_ok=True)
LANG = {"hi_in": "hi", "te_in": "te", "ta_in": "ta", "en_us": "en", "mr_in": "mr", "bn_in": "bn",
        "kn_in": "kn", "ml_in": "ml", "gu_in": "gu"}


def fleurs():
    rows = []
    root = H / "data/fleurs"
    for d in sorted(root.iterdir()):
        if d.name not in LANG:
            continue
        for split in ("train", "dev", "test"):
            tsv = d / f"{split}.tsv"
            adir = d / "audio" / split / split
            if not tsv.exists() or not adir.exists():
                continue
            with open(tsv, encoding="utf-8") as f:
                for line in f:
                    p = line.rstrip("\n").split("\t")
                    if len(p) < 7:
                        continue
                    sid, fn, raw, _, _, nsamp, gender = p[:7]
                    wav = adir / fn
                    if not wav.exists():
                        continue
                    rows.append(dict(utt_id=f"fleurs_{d.name}_{split}_{Path(fn).stem}", path=str(wav), label="bonafide",
                                     generator="bonafide", speaker=f"fleurs_{d.name}_unk", lang=LANG[d.name],
                                     line_id=f"fleurs_{d.name}_{sid}", text=raw, gender=gender.lower(),
                                     source="fleurs", split=split))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "fleurs.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    print("fleurs", len(df), df.groupby(["lang", "split"]).size().to_dict())


def asv19(n_bona={"train": 2580, "dev": 1000, "eval": 1500}, n_spoof={"train": 4000, "dev": 1500, "eval": 3000}):
    root = H / "data/asvspoof2019/LA"
    proto = {"train": "ASVspoof2019.LA.cm.train.trn.txt", "dev": "ASVspoof2019.LA.cm.dev.trl.txt",
             "eval": "ASVspoof2019.LA.cm.eval.trl.txt"}
    adir = {"train": "ASVspoof2019_LA_train", "dev": "ASVspoof2019_LA_dev", "eval": "ASVspoof2019_LA_eval"}
    rows = []
    rnd = random.Random(0)
    for split, pf in proto.items():
        lines = [l.split() for l in open(root / "ASVspoof2019_LA_cm_protocols" / pf)]
        bona = [l for l in lines if l[4] == "bonafide"]
        spoof = [l for l in lines if l[4] == "spoof"]
        rnd.shuffle(bona)
        # stratify spoof by attack id
        by = {}
        for l in spoof:
            by.setdefault(l[3], []).append(l)
        per = max(1, n_spoof[split] // len(by))
        sp = []
        for k in sorted(by):
            rnd.shuffle(by[k])
            sp += by[k][:per]
        for l in bona[:n_bona[split]] + sp:
            spk, fid, _, att, key = l
            rows.append(dict(utt_id=f"asv19_{fid}", path=str(root / adir[split] / "flac" / f"{fid}.flac"),
                             label=key, generator="bonafide" if key == "bonafide" else f"asv19_{att}",
                             speaker=f"asv19_{spk}", lang="en", line_id="", text="", gender="",
                             source="asv19", split=split))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "asv19.csv", index=False)
    print("asv19", len(df), df.groupby(["split", "label"]).size().to_dict())


if __name__ == "__main__":
    fleurs()
    asv19()
