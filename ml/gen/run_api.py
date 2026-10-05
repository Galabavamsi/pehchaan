"""Commercial stock-voice TTS (no cloning; stock voices read our script text and FLEURS sentences).

Runs on the team laptop so API keys never leave it (keys are read from <repo>/.env, never printed).
  python ml/gen/run_api.py build --fleurs fleurs.csv --out_dir data/generated/api   # writes jobs
  python ml/gen/run_api.py run   --jobs data/generated/api/jobs_sarvam.jsonl --workers 4

Engines:
  sarvam    Sarvam Bulbul v3 (hi-IN, en-IN, te-IN, ta-IN), POST https://api.sarvam.ai/text-to-speech
  openai    OpenAI gpt-4o-mini-tts (hi, en), POST https://api.openai.com/v1/audio/speech
  deepgram  Deepgram Aura-2 (English only), POST https://api.deepgram.com/v1/speak
All of them are HELD-OUT generators in our protocol (test split only).
"""
import argparse
import base64
import concurrent.futures as cf
import json
import os
import random
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml"))
from common.lines import EN, HI_F, HI_M  # noqa: E402

SARVAM_VOICES = {"m": ["shubh", "rahul", "amit", "rohan"], "f": ["ritu", "priya", "kavya", "neha"]}
OPENAI_VOICES = ["marin", "cedar", "alloy", "ash", "coral", "nova", "onyx", "sage"]
DEEPGRAM_VOICES = ["aura-2-thalia-en", "aura-2-andromeda-en", "aura-2-helena-en", "aura-2-apollo-en",
                   "aura-2-arcas-en", "aura-2-aries-en"]
FEMALE_OPENAI = {"marin", "coral", "nova", "sage", "alloy"}


def keys():
    k = {}
    for line in open(ROOT / ".env", encoding="utf-8"):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            a, b = line.split("=", 1)
            k[a.strip()] = b.strip().strip('"').strip("'")
    return k


def build(a):
    import csv
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rnd = random.Random(5)
    fl = list(csv.DictReader(open(a.fleurs, encoding="utf-8")))
    fl = [r for r in fl if r["split"] == "test" and 40 <= len(r["text"]) <= 150]
    seen, by_lang = set(), {}
    for r in fl:
        if r["line_id"] in seen:
            continue
        seen.add(r["line_id"])
        by_lang.setdefault(r["lang"], []).append(r)
    for v in by_lang.values():
        rnd.shuffle(v)
    jobs = {"sarvam": [], "openai": [], "deepgram": []}

    def add(engine, voice, lang, line_id, text, gender, extra=None):
        jid = f"{engine}__{voice}__{line_id}"
        j = dict(id=jid, engine=engine, voice=voice, lang=lang, line_id=line_id, text=text, gender=gender,
                 split="test", out=str(out / engine / f"{jid}.wav"))
        j.update(extra or {})
        jobs[engine].append(j)

    for g, vs in SARVAM_VOICES.items():
        for v in vs:
            for lid, t in EN.items():
                add("sarvam", v, "en", lid, t, g)
            for lid, t in (HI_F if g == "f" else HI_M).items():
                add("sarvam", v, "hi", lid, t, g)
    sv = SARVAM_VOICES["m"] + SARVAM_VOICES["f"]
    for lang in ("hi", "te", "ta", "en"):
        for i, r in enumerate(by_lang.get(lang, [])[:40]):
            v = sv[i % len(sv)]
            add("sarvam", v, lang, r["line_id"], r["text"], "f" if v in SARVAM_VOICES["f"] else "m")
    for v in OPENAI_VOICES:
        g = "f" if v in FEMALE_OPENAI else "m"
        for lid, t in EN.items():
            add("openai", v, "en", lid, t, g)
        for lid, t in (HI_F if g == "f" else HI_M).items():
            add("openai", v, "hi", lid, t, g)
    for lang in ("hi", "en"):
        for i, r in enumerate(by_lang.get(lang, [])[40:80]):
            v = OPENAI_VOICES[i % len(OPENAI_VOICES)]
            add("openai", v, lang, r["line_id"], r["text"], "f" if v in FEMALE_OPENAI else "m")
    for v in DEEPGRAM_VOICES:
        g = "f" if any(n in v for n in ("thalia", "andromeda", "helena")) else "m"
        for lid, t in EN.items():
            add("deepgram", v, "en", lid, t, g)
    for i, r in enumerate(by_lang.get("en", [])[80:120]):
        v = DEEPGRAM_VOICES[i % len(DEEPGRAM_VOICES)]
        add("deepgram", v, "en", r["line_id"], r["text"], "")
    for e, js in jobs.items():
        with open(out / f"jobs_{e}.jsonl", "w", encoding="utf-8") as f:
            for j in js:
                f.write(json.dumps(j, ensure_ascii=False) + "\n")
        print(e, len(js))


LANG = {"hi": "hi-IN", "en": "en-IN", "te": "te-IN", "ta": "ta-IN"}


def call(j, K):
    e = j["engine"]
    if e == "sarvam":
        r = requests.post("https://api.sarvam.ai/text-to-speech", timeout=60,
                          headers={"api-subscription-key": K["SARVAM_API_KEY"], "Content-Type": "application/json"},
                          json={"text": j["text"], "target_language_code": LANG[j["lang"]], "model": "bulbul:v3",
                                "speaker": j["voice"], "pace": 1.0, "speech_sample_rate": 24000})
        r.raise_for_status()
        return base64.b64decode(r.json()["audios"][0])
    if e == "openai":
        instr = ("Speak naturally in Hindi, like a person on a phone call in India." if j["lang"] == "hi"
                 else "Speak naturally in English with an Indian accent, like a person on a phone call.")
        r = requests.post("https://api.openai.com/v1/audio/speech", timeout=90,
                          headers={"Authorization": f"Bearer {K['OPENAI_API_KEY']}"},
                          json={"model": "gpt-4o-mini-tts", "input": j["text"], "voice": j["voice"],
                                "instructions": instr, "response_format": "wav"})
        r.raise_for_status()
        return r.content
    if e == "deepgram":
        r = requests.post(f"https://api.deepgram.com/v1/speak?model={j['voice']}&encoding=linear16&container=wav&sample_rate=24000",
                          timeout=60, headers={"Authorization": f"Token {K['DEEPGRAM_API_KEY']}", "Content-Type": "application/json"},
                          json={"text": j["text"]})
        r.raise_for_status()
        return r.content
    raise ValueError(e)


def run(a):
    K = keys()
    jobs = [json.loads(l) for l in open(a.jobs, encoding="utf-8") if l.strip()]
    jobs = [j for j in jobs if not (os.path.exists(j["out"]) and os.path.getsize(j["out"]) > 2000)]
    if a.limit:
        jobs = jobs[: a.limit]
    print(f"{len(jobs)} jobs")
    fails = []

    def one(j):
        for attempt in range(4):
            try:
                b = call(j, K)
                os.makedirs(os.path.dirname(j["out"]), exist_ok=True)
                with open(j["out"], "wb") as f:
                    f.write(b)
                return None
            except requests.HTTPError as ex:
                code = ex.response.status_code if ex.response is not None else 0
                msg = (ex.response.text[:200] if ex.response is not None else str(ex))
                if code in (429, 500, 502, 503, 504):
                    time.sleep(2 ** attempt * 2)
                    continue
                return f"{j['id']}: HTTP {code} {msg}"
            except Exception as ex:  # noqa
                time.sleep(2)
                err = repr(ex)[:200]
        return f"{j['id']}: {err if 'err' in dir() else 'retries exhausted'}"

    with cf.ThreadPoolExecutor(a.workers) as ex:
        for i, r in enumerate(ex.map(one, jobs)):
            if r:
                fails.append(r)
            if (i + 1) % 25 == 0:
                print(f"{i + 1}/{len(jobs)} fails={len(fails)}", flush=True)
    print(f"done; fails={len(fails)}")
    for f in fails[:10]:
        print("  ", f)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["build", "run"])
    ap.add_argument("--fleurs")
    ap.add_argument("--out_dir", default=str(ROOT / "data/generated/api"))
    ap.add_argument("--jobs")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    build(a) if a.mode == "build" else run(a)
