"""Segment the consented team recordings into utterances and align them to the script lines.

Input  ~/work/team_raw/<files from data/raw/recordings>  (S01_A_en.wav, S01_B_hi.wav, S01_C_te.wav,
       S01_D_free.wav, S01-S02_E_cellular.m4a, S01_E_whatsapp.m4a ...; any ffmpeg-readable format)
Output ~/work/team_seg/<speaker>/<utt_id>.wav  (16 kHz mono, silence-trimmed)
       ~/work/manifests/team_bona.csv          (one row per segment)

A/B (scripted): Silero-VAD speech regions -> split at pauses >= 0.7 s -> Whisper large-v3 -> each script
line takes its best-matching segment (or two adjacent segments merged if a pause split the line);
when a line was re-taken the later take wins on ties. Lines with CER > 0.6 are dropped.
C (mother tongue): segments with Whisper transcripts; the spoken "E-zero-one" prefix (if transcribed)
gives the line id, otherwise C<k>.
D (free) and E (calls): 3-10 s chunks at pauses; E chunks are genuine phone-channel bona fide audio.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.audio import load_any, save, trim_silence  # noqa: E402
from common.lines import EN, HI_F, HI_M  # noqa: E402
from data_prep.asr_qc import cer, transcribe  # noqa: E402

SR = 16000
H = Path.home()
NAME = re.compile(r"^(S\d\d)(?:-(S\d\d))?_([A-E])_([A-Za-z]+)\.(wav|m4a|mp3|flac|ogg|aac|opus|webm|mp4|3gp|amr)$", re.I)


def vad_regions(x, min_gap=0.7, min_len=0.6):
    from silero_vad import get_speech_timestamps, load_silero_vad
    import torch
    m = load_silero_vad()
    ts = get_speech_timestamps(torch.from_numpy(x), m, sampling_rate=SR, min_silence_duration_ms=int(min_gap * 1000),
                               speech_pad_ms=120, min_speech_duration_ms=int(min_len * 1000))
    return [(t["start"], t["end"]) for t in ts]


def chunk_regions(regs, max_len=10.0, min_len=3.0, x_len=None):
    """Merge VAD regions into 3-10 s chunks for unscripted speech."""
    out, cur = [], None
    for s, e in regs:
        if cur is None:
            cur = [s, e]
        elif (e - cur[0]) / SR <= max_len and (s - cur[1]) / SR < 1.5:
            cur[1] = e
        else:
            out.append(tuple(cur))
            cur = [s, e]
    if cur:
        out.append(tuple(cur))
    final = []
    for s, e in out:
        while (e - s) / SR > max_len:
            final.append((s, s + int(max_len * SR)))
            s += int(max_len * SR)
        if (e - s) / SR >= min_len:
            final.append((s, e))
    return final


def align_scripted(x, regs, lines, lang):
    segs = []
    for s, e in regs:
        r, _ = transcribe_arr(x[s:e], lang)
        segs.append(dict(s=s, e=e, text=r))
    cands = []
    for i in range(len(segs)):
        cands.append((i, i, segs[i]["text"]))
        if i + 1 < len(segs):
            cands.append((i, i + 1, segs[i]["text"] + " " + segs[i + 1]["text"]))
    chosen = {}
    for lid, ref in lines.items():
        best = None
        for (i, j, t) in cands:
            c = cer(ref, t)
            # ties (within 0.02) go to the later take
            if best is None or c < best[0] - 0.02 or (abs(c - best[0]) <= 0.02 and i > best[1]):
                best = (c, i, j, t)
        if best and best[0] <= 0.6:
            chosen[lid] = dict(start=segs[best[1]]["s"], end=segs[best[2]]["e"], cer=round(best[0], 3), asr=best[3])
    return chosen, segs


_tmp = str(H / "work/.seg_tmp.wav")


def transcribe_arr(y, lang):
    save(_tmp, y)
    segs, info = transcribe(_tmp, lang)
    return " ".join(s.text.strip() for s in segs).strip(), info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(H / "work/team_raw"))
    ap.add_argument("--out", default=str(H / "work/team_seg"))
    ap.add_argument("--meta", default=str(H / "work/team_raw/speakers.json"),
                    help='optional {"S01": {"gender": "m", "mother_tongue": "te"}}')
    a = ap.parse_args()
    meta = json.load(open(a.meta)) if os.path.exists(a.meta) else {}
    rows = []
    for f in sorted(Path(a.raw).iterdir()):
        m = NAME.match(f.name)
        if not m:
            continue
        spk, spk2, sec, tag = m.group(1).upper(), (m.group(2) or "").upper(), m.group(3).upper(), m.group(4).lower()
        gender = meta.get(spk, {}).get("gender", "unknown")
        x = load_any(f)
        regs = vad_regions(x)
        od = Path(a.out) / spk
        od.mkdir(parents=True, exist_ok=True)
        print(f.name, f"{len(x) / SR:.0f}s", len(regs), "regions", flush=True)
        if sec in ("A", "B"):
            lang = "en" if sec == "A" else "hi"
            if lang == "en":
                lines = EN
                chosen, _ = align_scripted(x, regs, lines, lang)
            elif str(gender).lower()[:1] in ("m", "f"):
                lines = HI_F if str(gender).lower().startswith("f") else HI_M
                chosen, _ = align_scripted(x, regs, lines, lang)
            else:  # gender not given: use whichever verb-form variant the speaker actually read
                cm, _ = align_scripted(x, regs, HI_M, lang)
                cf, _ = align_scripted(x, regs, HI_F, lang)
                sm = sum(c["cer"] for c in cm.values()) + 1.0 * (15 - len(cm))
                sf_ = sum(c["cer"] for c in cf.values()) + 1.0 * (15 - len(cf))
                lines, chosen = (HI_F, cf) if sf_ < sm else (HI_M, cm)
                meta.setdefault(spk, {})["hi_variant"] = "f" if sf_ < sm else "m"
                print(f"  Hindi verb-form variant read by {spk}: {'feminine' if sf_ < sm else 'masculine'}", flush=True)
            for lid, c in sorted(chosen.items()):
                y = trim_silence(x[c["start"]:c["end"]])
                uid = f"team_{spk}_{lid}"
                save(od / f"{uid}.wav", y)
                rows.append(dict(utt_id=uid, path=str(od / f"{uid}.wav"), label="bonafide", generator="bonafide", speaker=spk,
                                 lang=lang, line_id=lid, text=lines[lid], asr=c["asr"], align_cer=c["cer"], gender=gender,
                                 source="team", section=sec, native_channel="clean", dur=round(len(y) / SR, 2)))
            missing = sorted(set(lines) - set(chosen))
            print(f"  aligned {len(chosen)}/{len(lines)} lines; missing {missing}", flush=True)
        elif sec == "C":
            for k, (s, e) in enumerate(chunk_regions(regs, max_len=12.0, min_len=1.5)):
                y = trim_silence(x[s:e])
                t, _ = transcribe_arr(y, tag if tag in ("te", "ta", "kn", "ml", "mr", "bn", "gu", "pa", "ur", "hi") else None)
                mm = re.search(r"\b[eE]\s*-?\s*(?:zero|0)?\s*-?\s*(\d{1,2})\b", t)
                lid = f"C_E{int(mm.group(1)):02d}" if mm and 1 <= int(mm.group(1)) <= 11 else f"C{k:02d}"
                uid = f"team_{spk}_{tag}_{k:02d}"
                save(od / f"{uid}.wav", y)
                rows.append(dict(utt_id=uid, path=str(od / f"{uid}.wav"), label="bonafide", generator="bonafide", speaker=spk,
                                 lang=tag, line_id=lid, text=t, asr=t, align_cer=None, gender=gender, source="team",
                                 section=sec, native_channel="clean", dur=round(len(y) / SR, 2)))
        else:  # D free speech, E real calls
            ch = "clean" if sec == "D" else tag  # cellular / whatsapp
            for k, (s, e) in enumerate(chunk_regions(regs)):
                y = trim_silence(x[s:e])
                uid = f"team_{spk}{('-' + spk2) if spk2 else ''}_{sec}{tag}_{k:03d}"
                save(od / f"{uid}.wav", y)
                rows.append(dict(utt_id=uid, path=str(od / f"{uid}.wav"), label="bonafide", generator="bonafide",
                                 speaker=spk if not spk2 else f"{spk}-{spk2}", lang="mixed", line_id=f"{sec}{k:03d}", text="",
                                 asr="", align_cer=None, gender=gender if not spk2 else "mixed", source="team", section=sec,
                                 native_channel=ch, dur=round(len(y) / SR, 2)))
    json.dump(meta, open(H / "work/manifests/team_speakers.json", "w"), indent=1)
    df = pd.DataFrame(rows)
    out = H / "work/manifests/team_bona.csv"
    df.to_csv(out, index=False)
    print("wrote", out, len(df))
    if len(df):
        print(df.groupby(["speaker", "section"]).size())


if __name__ == "__main__":
    main()
