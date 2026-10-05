"""Indic Parler-TTS (ai4bharat/indic-parler-tts, Apache-2.0) stock-speaker jobs: an extra HELD-OUT Indic
generator added after the protocol was fixed (never used in training). Test split only.
  python gen/make_parler_jobs.py  -> ~/work/jobs/heldout_parler.jsonl
"""
import json
import os
import random
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.lines import EN, HI_M  # noqa: E402

H = Path.home()
SPK = {"hi": ["Rohit", "Divya", "Aman", "Rani"], "te": ["Prakash", "Lalitha", "Kiran"], "ta": ["Jaya", "Kavitha"],
       "en": ["Thoma", "Mary", "Swapna", "Dinesh"]}
STYLE = ["speaks at a moderate pace with a clear, close recording and almost no background noise.",
         "speaks slightly fast and expressively, in a close recording with very little noise.",
         "has a calm, conversational delivery recorded close to the microphone."]
rnd = random.Random(3)
fl = pd.read_csv(H / "work/manifests/fleurs.csv")
fl = fl[(fl.split == "test") & fl.text.str.len().between(40, 150)].drop_duplicates("line_id")
jobs = []


def add(lang, lid, text):
    s = rnd.choice(SPK[lang])
    jid = f"parler__{s}__{lid}"
    jobs.append(dict(id=jid, text=text, lang=lang, line_id=lid, split="test", voice=s, gender="",
                     description=f"{s} {rnd.choice(STYLE)}", out=str(H / "work/gen/heldout/parler" / f"{jid}.wav")))


for lid, t in HI_M.items():
    add("hi", lid, t)
for lid, t in EN.items():
    add("en", lid, t)
for lang in ("hi", "te", "ta"):
    for r in fl[fl.lang == lang].sample(n=40, random_state=4).itertuples():
        add(lang, r.line_id, r.text)
p = H / "work/jobs/heldout_parler.jsonl"
with open(p, "w", encoding="utf-8") as f:
    for j in jobs:
        f.write(json.dumps(j, ensure_ascii=False) + "\n")
print(len(jobs), "->", p)
