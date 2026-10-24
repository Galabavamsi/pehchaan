"""Closing demo (FINALE_PLAN 2b): clone a consenting person's voice live, call a team phone with it, delete it all.

  python -m realcall.live_clone consent J01 --form ~/Pictures/J01_form.jpg [--name "..."]
  python -m realcall.live_clone record  J01 --seconds 40          # they read the passage printed on screen
  python -m realcall.live_clone clone   J01 --lang hi --say "Mummy, accident ho gaya... abhi ₹50,000 bhejo."
  python -m realcall.dial attack --device A --speaker J01 --clip <the clip printed by clone>
  python -m realcall.live_clone purge   J01                       # on screen, right after the demo

Consent comes first: `consent` needs the photo of the signed form and registers the person for recording and
cloning until tomorrow only; consent.py refuses everything else. The call goes only to a registered team phone.
Nothing is kept: `purge` deletes the cloned voice at Sarvam, the recording and every clip, and withdraws the
consent. The signed form stays (work/live/forms/) as the record that consent was given.
"""
import argparse
import base64
import datetime as dt
import io
import json
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import yaml

from common.audio import load, normalize_rms, resample, save
from realcall.consent import Registry
from realcall.dsp import SR, quality, vad_regions
from realcall.sarvam_clone import ATTACK_SRC, LANG
from realcall.settings import WORK, env

LIVE = WORK / "live"
CONSENTS = LIVE / "participants.yaml"
FORMS = LIVE / "forms"
# Our own neutral passage (about 40 s read aloud): every common sound, nothing about money or family.
PASSAGE = ("On Sunday morning I took the early train to visit my aunt. The platform was crowded, so I bought a cup "
           "of tea and waited near the bookstall. When the train arrived, a family with three children helped an old "
           "man lift his heavy bag into the coach. We talked about cricket, the price of onions and the new metro "
           "line. By the time we reached the city, the sun was bright and the streets were full of people. My aunt "
           "was waiting at the gate with a big smile and a box of sweets.")


def _consents() -> dict:
    d = (yaml.safe_load(CONSENTS.read_text(encoding="utf-8")) if CONSENTS.exists() else None) or {}
    d.setdefault("participants", {})
    return d


def cmd_consent(a):
    form = Path(a.form).expanduser()
    if not form.is_file():
        raise SystemExit(f"{form} not found: photograph the signed consent form first")
    known = Registry().participants.get(a.id)
    if known and not known.get("live"):
        raise SystemExit(f"{a.id} is a registered team participant; use a new id such as J01 for the live demo")
    FORMS.mkdir(parents=True, exist_ok=True)
    kept = FORMS / f"{a.id}{form.suffix.lower()}"
    shutil.copy2(form, kept)
    d = _consents()
    d["participants"][a.id] = {
        "name": a.name or a.id, "live": True,
        "consent": {"record": True, "clone": True, "evidence": str(kept.resolve()),
                    "expires": str(dt.date.today() + dt.timedelta(days=1)),
                    "given_at": dt.datetime.now().isoformat(timespec="seconds")},
    }
    CONSENTS.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
    Registry().require_clone(a.id)   # the same check every dial and clone goes through
    print(f"{a.id}: consent registered for recording and cloning until {d['participants'][a.id]['consent']['expires']}"
          f" (form kept at {kept})")


def _record(out: Path, seconds: int):
    try:
        subprocess.run(["arecord", "-q", "-f", "S16_LE", "-r", str(SR), "-c", "1", "-d", str(seconds), str(out)],
                       check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        subprocess.run(["timeout", str(seconds), "parecord", "--channels=1", f"--rate={SR}", "--format=s16le",
                        "--file-format=wav", str(out)], check=False)


def cmd_record(a):
    Registry().require_record(a.id)
    out = LIVE / a.id / "ref.wav"
    out.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nPlease read this aloud, at your normal pace:\n\n  {PASSAGE}\n")
    for i in (3, 2, 1):
        print(f"  starting in {i}...", flush=True)
        time.sleep(1)
    print(f"  recording {a.seconds} s", flush=True)
    _record(out, a.seconds)
    q = quality(load(out))
    print(f"saved {out}: {q['speech_s']} s of speech, SNR {q['snr_db']} dB")
    if q["speech_s"] < 10:
        print("less than 10 s of speech: record again, closer to the microphone")


def reference(x: np.ndarray) -> bytes:
    """10-15 s of their speech, pauses shortened (Sarvam's recommended reference length)."""
    parts, total = [], 0.0
    for s, e in vad_regions(x):
        parts += [x[int(s * SR): int(e * SR)], np.zeros(int(0.25 * SR), np.float32)]
        total += e - s + 0.25
        if total >= 14:
            break
    if total < 8:
        raise SystemExit(f"only {total:.1f} s of speech in the recording: record again")
    buf = io.BytesIO()
    sf.write(buf, normalize_rms(np.concatenate(parts)[: int(15 * SR)], -22), SR, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def speaker_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """ClonEval's measure (arXiv:2504.20581): cosine similarity of WavLM speaker embeddings."""
    import torch
    from transformers import AutoFeatureExtractor, WavLMForXVector
    fe = AutoFeatureExtractor.from_pretrained("microsoft/wavlm-base-plus-sv")
    net = WavLMForXVector.from_pretrained("microsoft/wavlm-base-plus-sv").eval()
    with torch.no_grad():
        e = [torch.nn.functional.normalize(net(**fe(x, sampling_rate=SR, return_tensors="pt")).embeddings[0], dim=-1)
             for x in (a, b)]
    return float(e[0] @ e[1])


def cmd_clone(a):
    from sarvamai import SarvamAI
    Registry().require_clone(a.id)
    d = LIVE / a.id
    if not (d / "ref.wav").exists():
        raise SystemExit(f"no recording yet: python -m realcall.live_clone record {a.id}")
    if a.lang not in LANG:
        raise SystemExit(f"--lang must be one of {sorted(LANG)}")
    client = SarvamAI(api_subscription_key=env("SARVAM_API_KEY"))
    t0 = time.time()
    vf = d / "voice.json"
    if vf.exists():
        vid = json.loads(vf.read_text())["voice_id"]
    else:
        r = client.voice_cloning.create_voice(file=("ref.wav", reference(load(d / "ref.wav")), "audio/wav"),
                                              name=f"pehchaan-live-{a.id}", language="en-IN")
        vid = r.data.voice_id
        vf.write_text(json.dumps({"voice_id": vid}))
        print(f"voice created in {time.time() - t0:.1f} s")
    r = client.voice_cloning.convert(text=a.say[:1000], language_code=LANG[a.lang], voice_id=vid,
                                     output_audio_codec="wav", speech_sample_rate=SR, enable_qc=True)
    x, sr = sf.read(io.BytesIO(base64.b64decode(r.audio_b64 or r.audio)), dtype="float32", always_2d=True)
    out = d / f"clone_{1 + len(list(d.glob('clone_*.wav')))}.wav"
    save(out, resample(x.mean(1), sr, SR), SR)
    print(f"cloned and spoken in {time.time() - t0:.1f} s -> {out}")
    sim = speaker_similarity(load(d / "ref.wav"), load(out))
    print(f"speaker similarity to their real voice (WavLM, as in ClonEval): {sim:.3f}")
    print(f"next: python -m realcall.dial attack --device A --speaker {a.id} --clip {out}")
    print(f"      and drop {out.name} and ref.wav into the detector bench (#/bench) to see every detector's verdict")


def cmd_purge(a):
    d = LIVE / a.id
    vf = d / "voice.json"
    if vf.exists():
        from sarvamai import SarvamAI
        vid = json.loads(vf.read_text())["voice_id"]
        try:
            SarvamAI(api_subscription_key=env("SARVAM_API_KEY")).voice_cloning.delete_voice(vid)
            print(f"deleted the cloned voice {vid} at Sarvam")
            vf.unlink()
        except Exception as exc:  # keep voice.json so the delete can be retried; still remove the audio
            print(f"could NOT delete the voice at Sarvam ({exc}); run purge again")
    for p in sorted(d.glob("*.wav")) + sorted(ATTACK_SRC.glob(f"{a.id}_*.wav")):
        p.unlink()
        print(f"deleted {p}")
    if d.exists() and not any(d.iterdir()):
        d.rmdir()
    c = _consents()
    if a.id in c["participants"]:
        c["participants"][a.id]["consent"].update({"record": False, "clone": False})
        c["participants"][a.id]["purged_at"] = dt.datetime.now().isoformat(timespec="seconds")
        CONSENTS.write_text(yaml.safe_dump(c, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print(f"{a.id}: consent withdrawn; the signed form stays in {FORMS} as the record of consent")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("consent")
    c.add_argument("id")
    c.add_argument("--form", required=True, help="photo of the signed consent form")
    c.add_argument("--name")
    r = sub.add_parser("record")
    r.add_argument("id")
    r.add_argument("--seconds", type=int, default=40)
    k = sub.add_parser("clone")
    k.add_argument("id")
    k.add_argument("--say", required=True)
    k.add_argument("--lang", default="hi")
    p = sub.add_parser("purge")
    p.add_argument("id")
    a = ap.parse_args()
    {"consent": cmd_consent, "record": cmd_record, "clone": cmd_clone, "purge": cmd_purge}[a.cmd](a)


if __name__ == "__main__":
    main()
