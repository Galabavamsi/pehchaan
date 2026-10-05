"""Build job files for the "SynRef" corpus: spoofs made BEFORE the team audio exists.

No real person is cloned here. Reference voices are stock synthetic voices (Kokoro, MMS-TTS, XTTS
studio speakers). Cloners imitate those synthetic voices while reading FLEURS sentences, so each spoof
has a content-matched FLEURS bona fide counterpart (a real speaker reading the same sentence).
The FLEURS split of the sentence decides the split of the spoof (train/dev/test).

  python gen/make_synref.py --stage refs    # reference clips for pseudo-speakers
  python gen/make_synref.py --stage stock   # stock-voice TTS on FLEURS sentences (MMS, Kokoro, XTTS studio)
  python gen/make_synref.py --stage clone   # cloners (F5, F5-Hindi, XTTS, Chatterbox, CosyVoice2, Seed-VC)
"""
import argparse
import json
import os
import random
from pathlib import Path

import pandas as pd

H = Path.home()
W = H / "work"
G = W / "gen/synref"
J = W / "jobs"
J.mkdir(parents=True, exist_ok=True)

KOKORO = {"hi": ["hf_alpha", "hf_beta", "hm_omega", "hm_psi"], "en": ["af_heart", "am_michael", "bf_emma", "bm_george"]}
XTTS_STUDIO = ["Ana Florence", "Claribel Dervla", "Damien Black", "Viktor Eka"]
MMS_LANGS = ["hi", "en", "te", "ta"]
N = {"train": 160, "dev": 40, "test": 60}


def sentences(lang, seed=0, max_chars=150, min_chars=40):
    m = pd.read_csv(W / "manifests/fleurs.csv")
    m = m[m.lang == lang]
    m = m.drop_duplicates("line_id")
    m = m[m.text.str.len().between(min_chars, max_chars)]
    out = {}
    for split in ("train", "dev", "test"):
        s = m[m.split == split]
        if split == "train" and len(s) == 0:  # langs without a downloaded train split
            continue
        out[split] = s.sample(frac=1, random_state=seed)[["line_id", "text"]].values.tolist()
    return out


def dump(name, jobs):
    p = J / f"synref_{name}.jsonl"
    with open(p, "w", encoding="utf-8") as f:
        for j in jobs:
            f.write(json.dumps(j, ensure_ascii=False) + "\n")
    print(name, len(jobs), "->", p)


def refs():
    """2 reference clips per pseudo-speaker, from FLEURS *dev* sentences (refs never read test text)."""
    jobs = {"kokoro": [], "mms": [], "xtts": []}
    voices = []
    for lang in ("hi", "en"):
        dev = sentences(lang, seed=11)["dev"]
        k = 0
        for v in KOKORO[lang]:
            for r in range(2):
                lid, text = dev[k]; k += 1
                jid = f"ref__kokoro_{v}__{r}"
                jobs["kokoro"].append(dict(id=jid, voice=v, text=text, lang=lang, out=str(G / "refs" / f"{jid}.wav")))
                voices.append(dict(voice=f"kokoro_{v}", lang=lang, ref_wav=str(G / "refs" / f"{jid}.wav"), ref_text=text, r=r))
        for v in XTTS_STUDIO:
            lid, text = dev[k]; k += 1
            vid = v.replace(" ", "_")
            jid = f"ref__xtts_{vid}__{lang}"
            jobs["xtts"].append(dict(id=jid, speaker=v, text=text, lang=lang, out=str(G / "refs" / f"{jid}.wav")))
            voices.append(dict(voice=f"xttsstudio_{vid}", lang=lang, ref_wav=str(G / "refs" / f"{jid}.wav"), ref_text=text, r=0))
    for lang in MMS_LANGS:
        dev = sentences(lang, seed=12)["dev"]
        for r in range(2):
            lid, text = dev[r]
            jid = f"ref__mms_{lang}__{r}"
            jobs["mms"].append(dict(id=jid, text=text, lang=lang, out=str(G / "refs" / f"{jid}.wav")))
            voices.append(dict(voice=f"mms_{lang}", lang=lang, ref_wav=str(G / "refs" / f"{jid}.wav"), ref_text=text, r=r))
    for k, v in jobs.items():
        dump(f"refs_{k}", v)
    pd.DataFrame(voices).to_csv(W / "manifests/synref_voices.csv", index=False)


def stock():
    rnd = random.Random(1)
    jobs = {"mms": [], "kokoro": [], "xtts": []}
    for lang in MMS_LANGS:
        for split, ss in sentences(lang, seed=21).items():
            for lid, text in ss[: N[split]]:
                jid = f"mms__mms_{lang}__{lid}"
                jobs["mms"].append(dict(id=jid, text=text, lang=lang, split=split, line_id=lid, voice=f"mms_{lang}",
                                        out=str(G / "mms" / f"{jid}.wav")))
    for lang in ("hi", "en"):
        for split, ss in sentences(lang, seed=22).items():
            for lid, text in ss[: N[split]]:
                v = rnd.choice(KOKORO[lang])
                jid = f"kokoro__kokoro_{v}__{lid}"
                jobs["kokoro"].append(dict(id=jid, voice=v, text=text, lang=lang, split=split, line_id=lid,
                                           out=str(G / "kokoro" / f"{jid}.wav")))
            for lid, text in ss[N[split]: N[split] + N[split] // 2]:
                v = rnd.choice(XTTS_STUDIO)
                jid = f"xtts__xttsstudio_{v.replace(' ', '_')}__{lid}"
                jobs["xtts"].append(dict(id=jid, speaker=v, text=text, lang=lang, split=split, line_id=lid,
                                         out=str(G / "xtts" / f"{jid}.wav")))
    for k, v in jobs.items():
        dump(f"stock_{k}", v)


def clone():
    rnd = random.Random(2)
    voices = pd.read_csv(W / "manifests/synref_voices.csv")
    voices = voices[voices.ref_wav.map(os.path.exists)]
    by_lang = {l: g.to_dict("records") for l, g in voices.groupby("lang")}
    plan = {"f5": ["en"], "f5hi": ["hi"], "xtts": ["hi", "en"], "chatterbox": ["hi", "en"], "cosy": ["en"]}
    off = {"f5": 0, "f5hi": 0, "xtts": 400, "chatterbox": 200, "cosy": 600}
    for gen, langs in plan.items():
        jobs = []
        for lang in langs:
            per_lang = 1 if len(langs) == 1 else 0.5
            for split, ss in sentences(lang, seed=31).items():
                n = int(N[split] * per_lang)
                o = int(off[gen] * N[split] / 160) % max(1, len(ss) - n)
                for lid, text in ss[o:o + n]:
                    v = rnd.choice(by_lang[lang])
                    jid = f"{gen}__{v['voice']}__{lid}"
                    jobs.append(dict(id=jid, text=text, lang=lang, split=split, line_id=lid, voice=v["voice"],
                                     ref_wav=v["ref_wav"], ref_text=v["ref_text"], seed=rnd.randint(0, 10 ** 6),
                                     out=str(G / gen / f"{jid}.wav")))
        dump(f"clone_{gen}", jobs)
    # Seed-VC: source = stock MMS/Kokoro speech of a FLEURS sentence, target = a different pseudo-speaker
    src = [json.loads(l) for l in open(J / "synref_stock_mms.jsonl", encoding="utf-8")]
    src += [json.loads(l) for l in open(J / "synref_stock_kokoro.jsonl", encoding="utf-8")]
    src = [s for s in src if os.path.exists(s["out"])]
    rnd.shuffle(src)
    all_v = voices.to_dict("records")
    jobs, cnt = [], {}
    for s in src:
        key = (s["lang"], s["split"])
        lim = {"train": 60, "dev": 15, "test": 25}[s["split"]]
        if cnt.get(key, 0) >= lim:
            continue
        cands = [v for v in all_v if v["voice"] != s.get("voice") and not str(v["voice"]).endswith(str(s.get("voice")))]
        v = rnd.choice(cands)
        jid = f"seedvc__{v['voice']}__{s['line_id']}__{s['id'].split('__')[1]}"
        jobs.append(dict(id=jid, text=s["text"], lang=s["lang"], split=s["split"], line_id=s["line_id"], voice=v["voice"],
                         src_wav=s["out"], ref_wav=v["ref_wav"], seed=rnd.randint(0, 10 ** 6), out=str(G / "seedvc" / f"{jid}.wav")))
        cnt[key] = cnt.get(key, 0) + 1
    dump("clone_seedvc", jobs)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["refs", "stock", "clone"])
    a = ap.parse_args()
    {"refs": refs, "stock": stock, "clone": clone}[a.stage]()
