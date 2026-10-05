"""Whisper (faster-whisper large-v3) transcription + character error rate, used to
(1) QC generated clones (a clone that does not say the line is not a realistic attack) and
(2) align team recordings to script lines.

  python data_prep/asr_qc.py --jobs gen_jobs.jsonl --out qc.csv          # QC generator outputs
  python data_prep/asr_qc.py --wavs a.wav b.wav --lang hi                 # print transcripts
"""
import argparse
import json
import os
import re
import sys
import unicodedata

import pandas as pd

_model = None


def model(size="large-v3"):
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(size, device="cuda", compute_type="float16")
    return _model


def norm(t):
    t = unicodedata.normalize("NFC", str(t).lower())
    t = re.sub(r"[।॥.,!?;:\"'()\[\]\-–—…]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def cer(ref, hyp):
    from rapidfuzz.distance import Levenshtein
    r, h = norm(ref).replace(" ", ""), norm(hyp).replace(" ", "")
    if not r:
        return 1.0
    return Levenshtein.distance(r, h) / len(r)


def transcribe(path, lang=None, word_ts=False):
    segs, info = model().transcribe(str(path), language=lang, beam_size=5, vad_filter=False,
                                    word_timestamps=word_ts, condition_on_previous_text=False)
    segs = list(segs)
    return segs, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs")
    ap.add_argument("--out")
    ap.add_argument("--wavs", nargs="*")
    ap.add_argument("--lang")
    a = ap.parse_args()
    if a.wavs:
        for w in a.wavs:
            segs, info = transcribe(w, a.lang)
            print(w, info.language, " ".join(s.text for s in segs))
        return
    jobs = [json.loads(l) for l in open(a.jobs, encoding="utf-8") if l.strip()]
    done = set()
    if a.out and os.path.exists(a.out):
        done = set(pd.read_csv(a.out)["id"])
    rows = []
    for j in jobs:
        if j["id"] in done or not os.path.exists(j["out"]):
            continue
        lang = j.get("lang") if j.get("lang") in ("hi", "en", "te", "ta", "mr", "bn", "kn", "ml", "gu") else None
        try:
            segs, info = transcribe(j["out"], lang)
            hyp = " ".join(s.text for s in segs)
        except Exception as e:  # noqa
            hyp = ""
        ref = j.get("text") or j.get("src_text", "")
        rows.append({"id": j["id"], "lang": j.get("lang"), "cer": round(cer(ref, hyp), 3) if ref else None, "hyp": hyp})
        if len(rows) % 50 == 0:
            pd.DataFrame(rows).to_csv(a.out, index=False, mode="a", header=not os.path.exists(a.out))
            rows = []
    if rows:
        pd.DataFrame(rows).to_csv(a.out, index=False, mode="a", header=not os.path.exists(a.out))


if __name__ == "__main__":
    main()
