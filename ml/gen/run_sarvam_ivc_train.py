"""Sarvam instant voice clones of S01 for TRAINING: generator sarvam_ivct (common/protocol.py note, 2026-10-24).

Consent: realcall.consent.Registry.require_clone() must pass, as for every clone, and a held-out speaker (S02) is
refused outright. Audio stays with the other team-voice audio, under ml/realcall/work/src/clone/sarvam_ivct/.
Text: FLEURS train sentences (CC-BY-4.0), cached by `run_api.py build2` in data/generated/api2/fleurs_text.
  cd ml && python -m gen.run_sarvam_ivc_train --n 200
"""
import argparse
import base64
import io
import json
import random
import time
from pathlib import Path

import soundfile as sf

from common.audio import resample, save
from common.protocol import HELDOUT_SPEAKERS
from realcall.consent import Registry
from realcall.dsp import SR
from realcall.sarvam_clone import LANG, VOICES, reference_clip
from realcall.settings import SRC, env

ROOT = Path(__file__).resolve().parents[2]
OUT = SRC / "clone" / "sarvam_ivct"


def main():
    from sarvamai import SarvamAI

    from gen.run_api import fleurs_text
    ap = argparse.ArgumentParser()
    ap.add_argument("--speaker", default="S01")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--langs", default="hi,en,te")
    a = ap.parse_args()
    if a.speaker in HELDOUT_SPEAKERS:
        raise SystemExit(f"{a.speaker} is a held-out speaker and is never cloned for training")
    Registry().require_clone(a.speaker)
    client = SarvamAI(api_subscription_key=env("SARVAM_API_KEY"))
    voices = json.loads(VOICES.read_text()) if VOICES.exists() else {}

    def usable(v):   # a voice saved under another Sarvam subscription answers "Voice not accessible"
        try:
            client.voice_cloning.convert(text="नमस्ते", language_code=LANG["hi"], voice_id=v, output_audio_codec="wav",
                                         speech_sample_rate=SR)
            return True
        except Exception as ex:  # noqa: BLE001
            return "not accessible" not in str(getattr(ex, "body", ex))

    if a.speaker not in voices or not usable(voices[a.speaker]):
        r = client.voice_cloning.create_voice(file=("ref.wav", reference_clip(a.speaker), "audio/wav"),
                                              name=f"pehchaan-research-{a.speaker}", language="en-IN")
        voices[a.speaker] = r.data.voice_id
        VOICES.write_text(json.dumps(voices, indent=1))
        print(f"{a.speaker}: created voice {voices[a.speaker]} under this subscription")
    vid = voices[a.speaker]
    text = fleurs_text(ROOT / "data/generated/api2/fleurs_text")
    langs = a.langs.split(",")
    rnd = random.Random(1024)
    pools = {lang: rnd.sample(text[(lang, "train")], len(text[(lang, "train")])) for lang in langs}
    OUT.mkdir(parents=True, exist_ok=True)
    made = skipped = failed = 0
    for i in range(a.n):
        lang = langs[i % len(langs)]
        sid, t = pools[lang][i // len(langs)]
        out = OUT / f"sarvam_ivct__{a.speaker}__{lang}__f{sid}.wav"
        if out.exists():
            skipped += 1
            continue
        for attempt in range(3):
            try:
                r = client.voice_cloning.convert(text=t, language_code=LANG[lang], voice_id=vid, output_audio_codec="wav",
                                                 speech_sample_rate=SR, enable_qc=True)
                x, sr = sf.read(io.BytesIO(base64.b64decode(r.audio_b64 or r.audio)), dtype="float32", always_2d=True)
                save(out, resample(x.mean(1), sr, SR), SR)
                made += 1
                break
            except Exception as ex:  # noqa: BLE001 - transient API errors: retry, then count and move on
                if attempt == 2:
                    failed += 1
                    print(f"failed {out.name}: {type(ex).__name__}: {str(ex)[:160]}", flush=True)
                time.sleep(3 * (attempt + 1))
        if made and made % 20 == 0:
            print(f"{made} made", flush=True)
    print(f"{a.speaker}: {made} new, {skipped} already there, {failed} failed, in {OUT}")


if __name__ == "__main__":
    main()
