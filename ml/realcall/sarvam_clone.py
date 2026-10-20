"""Sarvam instant voice cloning of the consented team speakers: a generator no model was ever trained on.

  python -m realcall.sarvam_clone                 # all consented speakers, every scripted line with text
  python -m realcall.sarvam_clone --delete-voices # remove the saved voices from the Sarvam workspace afterwards
  python -m realcall.sarvam_clone --speakers S02 --lang hi --say "..."   # one live-demo clip -> work/src/attack/

Writes work/src/clone/sarvam_ivc/sarvam_ivc__<SPK>__<LINE>.wav (16 kHz), content-matched to the genuine lines,
and work/src/sarvam_voices.json (voice IDs). Protocol: sarvam_ivc is test-only (realcall/protocol.py).
"""
import argparse
import base64
import io
import json
from pathlib import Path

import numpy as np
import soundfile as sf

from common.audio import load, normalize_rms, resample, save
from realcall.consent import Registry
from realcall.dsp import SR, trim
from realcall.settings import SRC, env
from realcall.tape import _texts

LANG = {"en": "en-IN", "hi": "hi-IN", "te": "te-IN", "ta": "ta-IN", "bn": "bn-IN", "kn": "kn-IN", "ml": "ml-IN",
        "mr": "mr-IN", "gu": "gu-IN", "pa": "pa-IN", "od": "od-IN"}
OUT = SRC / "clone" / "sarvam_ivc"
ATTACK_SRC = SRC / "attack"   # live-demo clips (--say); never part of a tape or a training/test split
VOICES = SRC / "sarvam_voices.json"


def reference_clip(spk: str, target_s: float = 13.0):
    """10-15 s of the speaker's own clean genuine lines (Sarvam's recommended reference length)."""
    parts, total = [], 0.0
    for p in sorted((SRC / "genuine" / spk).glob(f"team_{spk}_*.wav")):
        x = trim(load(p))
        parts += [x, np.zeros(int(0.3 * SR), np.float32)]
        total += len(x) / SR + 0.3
        if total >= target_s:
            break
    if total < 8:
        raise SystemExit(f"{spk}: only {total:.1f} s of genuine audio for a reference clip")
    y = normalize_rms(np.concatenate(parts)[: int(15 * SR)], -22)
    buf = io.BytesIO()
    sf.write(buf, y, SR, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def main():
    from sarvamai import SarvamAI
    ap = argparse.ArgumentParser()
    ap.add_argument("--speakers", nargs="*")
    ap.add_argument("--delete-voices", action="store_true")
    ap.add_argument("--say", help="live-demo clip: speak this one text in the (single) speaker's cloned voice")
    ap.add_argument("--lang", default="hi", help="language of --say (key of LANG)")
    ap.add_argument("--out", help="output wav for --say (default work/src/attack/<speaker>_<n>.wav)")
    a = ap.parse_args()
    reg = Registry()
    client = SarvamAI(api_subscription_key=env("SARVAM_API_KEY"))
    voices = json.loads(VOICES.read_text()) if VOICES.exists() else {}
    if a.delete_voices:
        for spk, vid in list(voices.items()):
            client.voice_cloning.delete_voice(vid)
            voices.pop(spk)
            print("deleted", spk, vid)
        VOICES.write_text(json.dumps(voices, indent=1))
        return
    def voice_id(spk):
        reg.require_clone(spk)
        if spk not in voices:
            r = client.voice_cloning.create_voice(file=("ref.wav", reference_clip(spk), "audio/wav"),
                                                  name=f"pehchaan-research-{spk}", language="en-IN")
            voices[spk] = r.data.voice_id
            VOICES.write_text(json.dumps(voices, indent=1))
            print(f"{spk}: created voice {voices[spk]}")
        return voices[spk]

    def speak(spk, text, lang, out):
        r = client.voice_cloning.convert(text=text[:1000], language_code=LANG[lang], voice_id=voice_id(spk),
                                         output_audio_codec="wav", speech_sample_rate=SR, enable_qc=True)
        x, sr = sf.read(io.BytesIO(base64.b64decode(r.audio_b64 or r.audio)), dtype="float32", always_2d=True)
        out.parent.mkdir(parents=True, exist_ok=True)
        save(out, resample(x.mean(1), sr, SR), SR)

    if a.say:
        if not a.speakers or len(a.speakers) != 1 or a.lang not in LANG:
            raise SystemExit("--say needs exactly one --speakers ID and a --lang from LANG")
        spk = a.speakers[0]
        out = Path(a.out) if a.out else ATTACK_SRC / f"{spk}_{len(list(ATTACK_SRC.glob(f'{spk}_*.wav'))) + 1}.wav"
        speak(spk, a.say, a.lang, out)
        print(f"{spk}: wrote {out}")
        return
    texts = _texts()
    speakers = a.speakers or sorted({s for s, _ in texts})
    OUT.mkdir(parents=True, exist_ok=True)
    for spk in speakers:
        voice_id(spk)
        n = 0
        for (s, line), (lang, text) in sorted(texts.items()):
            if s != spk or not text or text == "nan" or lang not in LANG:
                continue
            out = OUT / f"sarvam_ivc__{spk}__{line}.wav"
            if out.exists():
                continue
            speak(spk, text, lang, out)
            n += 1
        print(f"{spk}: {n} new clips in {OUT}")


if __name__ == "__main__":
    main()
