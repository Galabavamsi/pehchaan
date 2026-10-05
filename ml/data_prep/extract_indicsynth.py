"""Extract a subset of IndicSynth (vdivyasharma/IndicSynth, CC-BY-NC-4.0: NON-COMMERCIAL) parquet shards
to WAV + manifest. Published spoof data only (XTTS-v2 / VITS / FreeVC24 outputs); we do not generate
anything from these speakers. Split by target speaker id (70/10/20) so no speaker crosses splits.
  python data_prep/extract_indicsynth.py --per_group 400
"""
import argparse
import glob
import hashlib
import io
import os
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import soundfile as sf

H = Path.home()
LANG = {"Hindi": "hi", "Telugu": "te", "Tamil": "ta"}


def split_of(spk):
    h = int(hashlib.md5(str(spk).encode()).hexdigest()[:8], 16) % 10
    return "train" if h < 7 else ("dev" if h < 8 else "test")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per_group", type=int, default=400)
    a = ap.parse_args()
    rows, count = [], {}
    out = H / "data/indicsynth/wav"
    for f in sorted(glob.glob(str(H / "data/indicsynth/*/*.parquet"))):
        lang = LANG[Path(f).parent.name]
        pf = pq.ParquetFile(f)
        for rg in range(pf.num_row_groups):
            t = pf.read_row_group(rg).to_pandas()
            for i, r in t.iterrows():
                gen = str(r["Generative Model"]).lower().replace("-", "").replace("_", "")
                key = (lang, gen)
                if count.get(key, 0) >= a.per_group:
                    continue
                spk = r["Target Speaker ID"]
                uid = f"isynth_{lang}_{gen}_{Path(f).stem[-14:-9]}_{rg}_{i}"
                p = out / lang / f"{uid}.wav"
                p.parent.mkdir(parents=True, exist_ok=True)
                try:
                    x, sr = sf.read(io.BytesIO(r["audio"]["bytes"]), dtype="float32")
                    sf.write(p, x, sr, subtype="PCM_16")
                except Exception:
                    continue
                count[key] = count.get(key, 0) + 1
                rows.append(dict(utt_id=uid, path=str(p), label="spoof", generator=f"indicsynth_{gen}", speaker=f"isynth_{spk}",
                                 lang=lang, line_id="", text=str(r.get("TTS Transcript") or ""), gender=str(r["Gender"]).lower()[:1],
                                 source="indicsynth", split=split_of(spk)))
    df = pd.DataFrame(rows)
    df.to_csv(H / "work/manifests/indicsynth.csv", index=False)
    print(df.groupby(["lang", "generator", "split"]).size())


if __name__ == "__main__":
    main()
