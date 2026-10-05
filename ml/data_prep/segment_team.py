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
                               speech_pad_ms=60 if min_gap < 0.5 else 120, min_speech_duration_ms=int(min_len * 1000))
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


def _sim(ref, hyp):
    return max(0.0, 1.0 - cer(ref, hyp))


_word_cache = {}


def words_of(x, lang):
    """Whisper on the whole file with word timestamps (cached per file+lang)."""
    key = (id(x), lang)
    if key not in _word_cache:
        save(_tmp, x)
        segs, _ = transcribe(_tmp, lang, word_ts=True)
        _word_cache[key] = [(int(w.start * SR), int(w.end * SR), w.word) for sg in segs for w in (sg.words or [])]
    return _word_cache[key]


def _region_words(x, s, e, lang):
    """Re-transcribe one VAD region (used when the long-form pass skipped words there)."""
    save(_tmp, x[s:e])
    sg, _ = transcribe(_tmp, lang, word_ts=True)
    return [(s + int(w.start * SR), s + int(w.end * SR), w.word) for g in sg for w in (g.words or [])]


def _units(x, regs, lang):
    """Monotonic DP alignment of the ordered script lines to sentence-like units.
    Units come from a long-form Whisper pass with word timestamps, split at sentence punctuation or at
    word gaps >= 0.35 s (the kit asks for pauses, but people read fast). VAD regions where Whisper
    produced almost no words are re-transcribed on their own. A line may span up to `max_merge`
    consecutive units; extra units (false starts, retakes) are skipped; a line may be missing.
    Keeping the kit's order lets number-heavy lines (ASR writes digits) still land correctly."""
    W = list(words_of(x, lang))
    for s, e in regs:
        n_w = sum(1 for w in W if s <= (w[0] + w[1]) // 2 < e)
        if (e - s) / SR > 2.0 and n_w / ((e - s) / SR) < 0.8:
            W = [w for w in W if not (s <= (w[0] + w[1]) // 2 < e)] + _region_words(x, s, e, lang)
    W.sort()
    units, cur = [], []
    for k, w in enumerate(W):
        cur.append(w)
        gap = (W[k + 1][0] - w[1]) / SR if k + 1 < len(W) else 9
        if w[2].strip()[-1:] in ".?!।" or gap >= 0.35:
            units.append(cur)
            cur = []
    if cur:
        units.append(cur)
    segs = []
    for k, u in enumerate(units):
        prev_end = units[k - 1][-1][1] if k else 0
        next_start = units[k + 1][0][0] if k + 1 < len(units) else len(x)
        a = max((prev_end + u[0][0]) // 2, u[0][0] - int(0.25 * SR))
        b = min((u[-1][1] + next_start) // 2, u[-1][1] + int(0.3 * SR))
        segs.append(dict(s=int(a), e=int(b), text="".join(w[2] for w in u).strip()))
    return segs


def _regions(x, regs, lang):
    W = words_of(x, lang)
    return [dict(s=s, e=e, text="".join(w[2] for w in W if s - 1600 <= (w[0] + w[1]) // 2 < e + 1600).strip()) for s, e in regs]


def align_scripted(x, regs, lines, lang, max_cer=0.75):
    """Run the DP on two segmentations (fine VAD regions, and sentence-like word units) and keep the
    one that aligns more of the script (sum of 1-CER over aligned lines)."""
    best = None
    for segs, mm in ((_regions(x, regs, lang), 6), (_units(x, regs, lang), 8)):
        ch, sg = _dp(segs, lines, max_cer, mm)
        sc = sum(1 - c["cer"] for c in ch.values())
        if best is None or sc > best[0]:
            best = (sc, ch, sg)
    return best[1], best[2]


def _dp(segs, lines, max_cer, max_merge):
    ids, refs = list(lines.keys()), list(lines.values())
    n, m = len(ids), len(segs)
    NEG = -1e9
    skip_line, skip_seg = -0.15, -0.02
    dp = np.full((n + 1, m + 1), NEG)
    bt = {}
    dp[0, 0] = 0.0
    for j in range(1, m + 1):
        dp[0, j] = dp[0, j - 1] + skip_seg
        bt[(0, j)] = ("skipS",)
    for i in range(1, n + 1):
        dp[i, 0] = dp[i - 1, 0] + skip_line
        bt[(i, 0)] = ("skipL",)
        for j in range(1, m + 1):
            best, arg = dp[i, j - 1] + skip_seg, ("skipS",)
            v = dp[i - 1, j] + skip_line
            if v > best:
                best, arg = v, ("skipL",)
            txt = ""
            for k in range(1, min(max_merge, j) + 1):
                txt = (segs[j - k]["text"] + " " + txt).strip()
                v = dp[i - 1, j - k] + _sim(refs[i - 1], txt)
                if v > best:
                    best, arg = v, ("take", k)
            dp[i, j], bt[(i, j)] = best, arg
    i, j, chosen = n, m, {}
    while i > 0 or j > 0:
        op = bt.get((i, j), ("skipL",) if i > 0 else ("skipS",))
        if op[0] == "skipS":
            j -= 1
        elif op[0] == "skipL":
            i -= 1
        else:
            k = op[1]
            t = " ".join(sg["text"] for sg in segs[j - k:j]).strip()
            c = cer(refs[i - 1], t)
            if c <= max_cer:
                chosen[ids[i - 1]] = dict(start=segs[j - k]["s"], end=segs[j - 1]["e"], cer=round(c, 3), asr=t)
            i, j = i - 1, j - k
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
    ap.add_argument("--manifest", default=str(H / "work/manifests/team_bona.csv"))
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
        regs = vad_regions(x, min_gap=0.25 if sec in ("A", "B") else 0.7, min_len=0.25 if sec in ("A", "B") else 0.6)
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
            # E: the dialer's own 8 kHz WAV is true network audio ("cellular"); another capture of the same
            # call (e.g. m4a) is kept as a separate channel so the two are never mixed up
            ext = f.suffix.lower().lstrip(".")
            ch = "clean" if sec == "D" else (tag if ext == "wav" else f"{tag}_{ext}")
            for k, (s, e) in enumerate(chunk_regions(regs)):
                y = trim_silence(x[s:e])
                uid = f"team_{spk}{('-' + spk2) if spk2 else ''}_{sec}{ch}_{k:03d}"
                save(od / f"{uid}.wav", y)
                rows.append(dict(utt_id=uid, path=str(od / f"{uid}.wav"), label="bonafide", generator="bonafide",
                                 speaker=spk if not spk2 else f"{spk}-{spk2}", lang="mixed", line_id=f"{sec}{k:03d}", text="",
                                 asr="", align_cer=None, gender=gender if not spk2 else "mixed", source="team", section=sec,
                                 native_channel=ch, dur=round(len(y) / SR, 2)))
    df = pd.DataFrame(rows)
    out = Path(a.manifest)
    json.dump(meta, open(out.with_name(out.stem + "_speakers.json"), "w"), indent=1)
    df.to_csv(out, index=False)
    print("wrote", out, len(df))
    if len(df):
        print(df.groupby(["speaker", "section"]).size())


if __name__ == "__main__":
    main()
