"""Laptop-mic capture of the receiving phone on speakerphone (the product's 8-12 s speakerphone capture path).

  python -m realcall.capture devices                                       # list mics / outputs
  python -m realcall.capture session --device D2 [--mic 15]                # run during dial.py tape calls; Ctrl+C to stop
  python -m realcall.capture live --device D2 --caller V03 --route cellular --network jio
  python -m realcall.capture whatsapp-tape --device D2 --out "CABLE Input" # play a tape into a WhatsApp Desktop call

Files are 16 kHz mono WAV with a sidecar JSON holding the wall-clock start, so ingest.py can find calls in them.
"""
import argparse
import json
import queue
import threading
import time
import uuid

import numpy as np
import soundfile as sf

from realcall.consent import Registry
from realcall.settings import CAPTURE, TAPES, ensure_dirs, log_event

SR = 16000
CHUNK_S = 600


def _sd():
    import sounddevice as sd
    return sd


class Recorder:
    """Continuous mic recorder that rolls to a new file every CHUNK_S seconds."""

    def __init__(self, prefix: str, mic=None, meta=None, roll=True):
        self.prefix, self.mic, self.meta, self.roll = prefix, mic, meta or {}, roll
        self.q, self.stop_ev, self.files = queue.Queue(), threading.Event(), []

    def _open(self):
        t0 = time.time()
        path = CAPTURE / f"{self.prefix}_{int(t0)}.wav"
        self.f = sf.SoundFile(path, "w", samplerate=SR, channels=1, subtype="PCM_16")
        self.f_t0, self.f_n = t0, 0
        side = {"start_epoch": t0, "sr": SR, "mic": str(self.mic), **self.meta}
        path.with_suffix(".json").write_text(json.dumps(side, indent=1), encoding="utf-8")
        self.files.append(str(path))

    def _writer(self):
        self._open()
        while not (self.stop_ev.is_set() and self.q.empty()):
            try:
                x = self.q.get(timeout=0.2)
            except queue.Empty:
                continue
            self.f.write(x)
            self.f_n += len(x)
            if self.roll and self.f_n >= CHUNK_S * SR:
                self.f.close()
                self._open()
        self.f.close()

    def start(self):
        sd = _sd()
        ensure_dirs()
        self.w = threading.Thread(target=self._writer, daemon=True)
        self.w.start()
        self.s = sd.InputStream(samplerate=SR, channels=1, dtype="float32", device=self.mic,
                                callback=lambda d, n, t, st: self.q.put(d[:, 0].copy()))
        self.s.start()
        return self

    def stop(self):
        self.s.stop()
        self.s.close()
        self.stop_ev.set()
        self.w.join()
        return self.files


def _level_meter(rec_seconds=3, mic=None):
    sd = _sd()
    x = sd.rec(int(rec_seconds * SR), samplerate=SR, channels=1, dtype="float32", device=mic)
    sd.wait()
    db = 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)
    print(f"mic level over {rec_seconds} s: {db:.1f} dBFS (room noise should be below -50; speech peaks around -25)")


def cmd_session(a, reg):
    d = reg.device(a.device)
    _level_meter(mic=a.mic)
    rec = Recorder(f"session_{a.device}", a.mic, {"device": a.device, "carrier": d.get("carrier"), "capture": "laptop_mic"}).start()
    print("recording the speakerphone... leave this running while dial.py places calls. Ctrl+C to stop.", flush=True)
    t_end = time.time() + a.seconds if a.seconds else None
    try:
        while t_end is None or time.time() < t_end:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    print("saved:", *rec.stop(), sep="\n  ")


def cmd_live(a, reg):
    reg.require_record(a.caller)
    d = reg.device(a.device)
    if a.caller == d["owner"]:
        raise SystemExit("the caller must be someone other than the receiving phone's owner")
    print(f"Live genuine call: {a.caller} calls {a.device} over {a.route}. Consent on file for {a.caller}: yes.")
    print("Confirm the caller is a real person speaking live (no recordings, no TTS) [y/N] ", end="")
    if input().strip().lower() != "y":
        return
    call_id = uuid.uuid4().hex
    input("Answer on speakerphone, then press Enter when the caller starts talking... ")
    t0 = time.time()
    rec = Recorder(f"live_{call_id[:8]}", a.mic, {"device": a.device, "capture": "laptop_mic", "kind": "live"}, roll=False).start()
    input("recording. Press Enter when the call ends. ")
    files = rec.stop()
    log_event("live_call", call_id=call_id, kind="live", device=a.device, carrier=a.network or d.get("carrier"),
              network=d.get("network"), model=d.get("model"), route=a.route, caller=a.caller, speaker=a.caller,
              lang=a.lang, file=files[0], answered_t=t0, hangup_t=time.time(), capture="laptop_mic")
    print("saved", files[0])


def cmd_whatsapp_tape(a, reg):
    """Plays a tape into an output device (e.g. VB-Cable feeding WhatsApp Desktop's mic) while recording the phone."""
    from common.audio import load
    from realcall.tape import build
    sd = _sd()
    d = reg.device(a.device)
    meta = build(reg, a.pairs)
    x = load(TAPES / f"{meta['tape_id']}.ref.wav", 48000)
    call_id = uuid.uuid4().hex
    input(f"Start a WhatsApp call from the laptop to {a.device}, answer it on speakerphone, then press Enter... ")
    rec = Recorder(f"wa_{call_id[:8]}", a.mic, {"device": a.device, "capture": "laptop_mic", "kind": "tape"}, roll=False).start()
    log_event("call_registered", call_id=call_id, kind="tape", tape_id=meta["tape_id"], device=a.device,
              carrier=d.get("carrier"), network="whatsapp", model=d.get("model"), route="whatsapp")
    t0 = time.time()
    log_event("answered", call_id=call_id)
    sd.play(x, 48000, device=a.out)
    sd.wait()
    time.sleep(2)
    files = rec.stop()
    log_event("hangup", call_id=call_id, cause="local_end", duration_s=round(time.time() - t0, 1), capture_file=files[0])
    print("done; you can hang up. saved", files[0])


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("devices")
    s = sub.add_parser("session")
    s.add_argument("--device", required=True)
    s.add_argument("--mic", type=int)
    s.add_argument("--seconds", type=float, default=0, help="stop by itself after this long (0 = until Ctrl+C)")
    lv = sub.add_parser("live")
    lv.add_argument("--device", required=True)
    lv.add_argument("--caller", required=True)
    lv.add_argument("--route", choices=["cellular", "whatsapp", "other_voip"], default="cellular")
    lv.add_argument("--network", help="caller's carrier, e.g. jio/airtel/vi")
    lv.add_argument("--lang", default="")
    lv.add_argument("--mic", type=int)
    w = sub.add_parser("whatsapp-tape")
    w.add_argument("--device", required=True)
    w.add_argument("--out", required=True, help="output device name or index feeding WhatsApp Desktop")
    w.add_argument("--pairs", type=int, default=5)
    w.add_argument("--mic", type=int)
    a = ap.parse_args()
    if a.cmd == "devices":
        print(_sd().query_devices())
        return
    reg = Registry()
    {"session": cmd_session, "live": cmd_live, "whatsapp-tape": cmd_whatsapp_tape}[a.cmd](a, reg)


if __name__ == "__main__":
    main()
