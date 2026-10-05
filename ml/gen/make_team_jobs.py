"""Job files for cloning the CONSENTED team speakers (content-matched to their own real lines).

  python gen/make_team_jobs.py --speakers S01 [S02 ...]

Consent gate: a speaker is only cloned if ~/work/team_raw/<SPK>_consent.* exists (copied from
data/raw/recordings together with the audio). Missing consent -> speaker skipped, loudly.

References: en = real E14+E15 joined, hi = real H14+H15 joined (texts known exactly), te = longest
mother-tongue segment. Those reference lines are not cloned. Every other aligned line is cloned by
every generator that supports its language:
  en: f5, xtts, cosyvoice2, chatterbox(held-out)       hi: f5hi, xtts, chatterbox(held-out), indicf5*
  te/ta: indicf5* (* only if its weights are available)
  seedvc (held-out): source = commercial stock voice reading the same line (and the other team speaker's
  real line when both speakers exist), converted to the target speaker's voice.
"""
import argparse
import glob
import json
import os
import random
from pathlib import Path

import numpy as np
import pandas as pd

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.audio import load, save  # noqa: E402
from common.protocol import team_split  # noqa: E402

H = Path.home()
W = H / "work"
OUT = W / "gen/team"
EN_GENS = ["f5", "xtts", "cosy", "chatterbox"]
HI_GENS = ["f5hi", "xtts", "chatterbox", "indicf5"]
IND_GENS = ["indicf5"]


def make_ref(rows, ids, path):
    xs = []
    for i in ids:
        r = rows.get(i)
        if r is None:
            return None, None
        xs.append(load(r["path"]))
        xs.append(np.zeros(int(0.3 * 16000), dtype=np.float32))
    save(path, np.concatenate(xs[:-1]))
    return str(path), " ".join(rows[i]["text"] for i in ids)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--speakers", nargs="+", required=True)
    ap.add_argument("--indicf5", action="store_true", help="IndicF5 weights available")
    a = ap.parse_args()
    bona = pd.read_csv(W / "manifests/team_bona.csv")
    rnd = random.Random(7)
    jobs = {g: [] for g in ["f5", "f5hi", "xtts", "cosy", "chatterbox", "indicf5", "seedvc"]}
    api = {}
    for jf in glob.glob(str(W / "gen/api/jobs_*.jsonl")):
        for l in open(jf, encoding="utf-8"):
            j = json.loads(l)
            p = W / "gen/api" / j["engine"] / os.path.basename(j["out"].replace("\\", "/"))
            if p.exists() and j["line_id"][:1] in ("E", "H") and len(j["line_id"]) == 3:
                api.setdefault(j["line_id"], []).append(str(p))
    for spk in a.speakers:
        consent = glob.glob(str(W / "team_raw" / f"{spk}_consent*"))
        if not consent:
            print(f"!!! {spk}: NO CONSENT FILE in team_raw -> NOT cloned")
            continue
        b = bona[(bona.speaker == spk) & (bona.section.isin(["A", "B", "C"]))]
        rows = {r.line_id: r._asdict() for r in b.itertuples(index=False)}
        rd = OUT / "refs"
        rd.mkdir(parents=True, exist_ok=True)
        refs = {}
        refs["en"] = make_ref(rows, ["E14", "E15"], rd / f"{spk}_ref_en.wav")
        refs["hi"] = make_ref(rows, ["H14", "H15"], rd / f"{spk}_ref_hi.wav")
        mt = b[b.section == "C"]
        if len(mt):
            r = mt.sort_values("dur").iloc[-1]
            refs[r.lang] = (r.path, r.text)
            ref_mt_id = r.line_id
        else:
            ref_mt_id = None
        print(spk, {k: (v[0] is not None) for k, v in refs.items()})
        for r in b.itertuples(index=False):
            if r.line_id in ("E14", "E15", "H14", "H15") or r.line_id == ref_mt_id:
                continue
            lang = r.lang
            gens = EN_GENS if lang == "en" else (HI_GENS if lang == "hi" else IND_GENS)
            ref = refs.get(lang)
            if not ref or ref[0] is None:
                continue
            split = team_split(spk, r.line_id, r.section)
            for g in gens:
                if g == "indicf5" and not a.indicf5:
                    continue
                gname = {"cosy": "cosyvoice2"}.get(g, g)
                jid = f"{gname}__{spk}__{r.line_id}"
                jobs[g].append(dict(id=jid, text=r.text, lang=lang, ref_wav=ref[0], ref_text=ref[1], speaker_id=spk,
                                    line_id=r.line_id, split=split, gender=r.gender, seed=rnd.randint(0, 10 ** 6),
                                    out=str(OUT / gname / f"{jid}.wav")))
            # Seed-VC: stock-voice reading of the same line -> this speaker's voice
            if lang in ("en", "hi") and r.line_id in api:
                src = rnd.choice(api[r.line_id])
                jid = f"seedvc__{spk}__{r.line_id}__stock"
                jobs["seedvc"].append(dict(id=jid, text=r.text, lang=lang, src_wav=src, ref_wav=ref[0], speaker_id=spk,
                                           line_id=r.line_id, split=split, gender=r.gender, seed=rnd.randint(0, 10 ** 6),
                                           out=str(OUT / "seedvc" / f"{jid}.wav")))
            # Seed-VC: the OTHER consented speaker's real line -> this speaker's voice
            for other in a.speakers:
                if other == spk:
                    continue
                o = bona[(bona.speaker == other) & (bona.line_id == r.line_id)]
                if len(o) and glob.glob(str(W / "team_raw" / f"{other}_consent*")):
                    jid = f"seedvc__{spk}__{r.line_id}__from{other}"
                    jobs["seedvc"].append(dict(id=jid, text=r.text, lang=lang, src_wav=o.iloc[0].path, ref_wav=ref[0],
                                               speaker_id=spk, line_id=r.line_id, split=split, gender=r.gender,
                                               seed=rnd.randint(0, 10 ** 6), out=str(OUT / "seedvc" / f"{jid}.wav")))
    (W / "jobs").mkdir(exist_ok=True)
    for g, js in jobs.items():
        if not js:
            continue
        p = W / "jobs" / f"team_{g}.jsonl"
        with open(p, "w", encoding="utf-8") as f:
            for j in js:
                f.write(json.dumps(j, ensure_ascii=False) + "\n")
        print(g, len(js), "->", p)


if __name__ == "__main__":
    main()
