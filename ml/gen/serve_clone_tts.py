"""Serve one offline neural voice-clone engine as a tiny localhost TTS backend for the live attack agent.

Runs ON THE GPU BOX, inside the engine's own uv venv (~/envs/<env>, see infra/setup_envs.sh). Loads the engine once,
clones a consented speaker from a reference wav, and answers:

  GET  /healthz         -> {"ok": true, "engine": "...", "ready": true, "sr": 24000, "device": "cuda"}
  POST /tts {text,lang} -> 16-bit WAV bytes (the clone speaking `text`, at the engine's native sample rate)

Bind 127.0.0.1 only; no public port, no keys (the box runs a LOCAL model, so nothing from .env is needed here).
Reach it from the laptop over an SSH tunnel:  ssh -L 8700:127.0.0.1:8700 pehchaan

  ~/envs/xtts/bin/python serve_clone_tts.py --engine xtts --ref ref_S02.wav --port 8700

Engines and the venv each needs (run this with that venv's python):
  xtts        ~/envs/xtts        coqui-tts, hi/en zero-shot clone from the reference wav
  f5 / f5hi   ~/envs/f5          F5-TTS v1 Base (en) / SPRINGLab F5-Hindi (hi); --ref-text helps quality
  cosyvoice2  ~/envs/cosy        ~/repos/CosyVoice on sys.path; English only
  chatterbox  ~/envs/chatterbox  hi/en and 21 more; every output carries a Perth watermark

This mirrors the batch runners in gen/run_xtts.py / run_f5.py / run_cosy.py / run_chatterbox.py, but keeps one model
warm and synthesises arbitrary LLM reply text on demand instead of rendering a fixed job file.
"""
import argparse
import io
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))


def load_engine(name: str, ref_wav: str, ref_text: str = ""):
    """Return synth(text, lang) -> (float32 mono, sr). Loads the model once; mirrors the gen/run_*.py loaders."""
    if name == "xtts":
        os.environ.setdefault("COQUI_TOS_AGREED", "1")
        import torch
        from TTS.api import TTS
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cuda")
        sr = tts.synthesizer.output_sample_rate
        xlang = {"en": "en", "hi": "hi"}

        def synth(text, lang):
            torch.manual_seed(0)
            wav = tts.tts(text=text, speaker_wav=ref_wav, language=xlang.get(lang, lang))
            return np.asarray(wav, dtype=np.float32), sr
        return synth, sr

    if name in ("f5", "f5hi"):
        from f5_tts.api import F5TTS
        if name == "f5hi":
            from huggingface_hub import hf_hub_download
            ck = hf_hub_download("SPRINGLab/F5-Hindi-24KHz", "model_2500000.safetensors")
            vo = hf_hub_download("SPRINGLab/F5-Hindi-24KHz", "vocab.txt")
            tts = F5TTS(model="F5TTS_Small", ckpt_file=ck, vocab_file=vo)
        else:
            tts = F5TTS(model="F5TTS_v1_Base")

        def synth(text, lang):
            wav, sr, _ = tts.infer(ref_file=ref_wav, ref_text=ref_text, gen_text=text, seed=0,
                                   show_info=lambda *x: None, progress=None, remove_silence=False, nfe_step=32)
            return np.asarray(wav, dtype=np.float32), sr
        return synth, None

    if name == "cosyvoice2":
        repo = os.path.expanduser("~/repos/CosyVoice")
        sys.path.insert(0, repo)
        sys.path.insert(0, os.path.join(repo, "third_party/Matcha-TTS"))
        import torch
        from cosyvoice.cli.cosyvoice import AutoModel
        cv = AutoModel(model_dir=os.path.expanduser("~/weights/CosyVoice2-0.5B"))

        def synth(text, lang):
            torch.manual_seed(0)
            outs = [o["tts_speech"] for o in cv.inference_zero_shot(text, ref_text, ref_wav, stream=False)]
            return torch.cat(outs, dim=-1).squeeze(0).cpu().numpy(), cv.sample_rate
        return synth, cv.sample_rate

    if name == "chatterbox":
        import torch
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        model = ChatterboxMultilingualTTS.from_pretrained(device="cuda")

        def synth(text, lang):
            torch.manual_seed(0)
            wav = model.generate(text, language_id=lang, audio_prompt_path=ref_wav)
            return wav.squeeze(0).cpu().numpy(), model.sr
        return synth, model.sr

    raise SystemExit(f"unknown engine {name!r}")


class State:
    engine = ""
    synth = None
    sr = None
    ready = False
    lock = threading.Lock()


def _wav_bytes(wav: np.ndarray, sr: int) -> bytes:
    wav = np.asarray(wav, dtype=np.float32).reshape(-1)
    peak = float(np.max(np.abs(wav))) + 1e-9
    if peak > 0.99:
        wav = wav / peak * 0.99
    buf = io.BytesIO()
    sf.write(buf, wav, int(sr), format="WAV", subtype="PCM_16")
    return buf.getvalue()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):   # quieter: we print our own timing lines
        pass

    def _json(self, code: int, obj: dict):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.split("?")[0] == "/healthz":
            self._json(200, {"ok": True, "engine": State.engine, "ready": State.ready, "sr": State.sr,
                             "device": "cuda"})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path.split("?")[0] != "/tts":
            return self._json(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n) or b"{}")
            text = (req.get("text") or "").strip()
            lang = req.get("lang") or "hi"
            if not text:
                return self._json(400, {"error": "empty text"})
            t0 = time.perf_counter()
            with State.lock:                         # serialise GPU access across request threads
                wav, sr = State.synth(text[:500], lang)
            data = _wav_bytes(wav, sr)
            ms = round((time.perf_counter() - t0) * 1000)
            print(f"[tts] {ms} ms  {len(wav) / sr:.1f}s  {lang}  {text[:60]!r}", flush=True)
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("X-Synth-Ms", str(ms))
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:                       # one bad line never kills the server
            import traceback
            traceback.print_exc()
            self._json(500, {"error": repr(e)[:300]})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", required=True, choices=["xtts", "f5", "f5hi", "cosyvoice2", "chatterbox"])
    ap.add_argument("--ref", required=True, help="reference wav of the consented speaker (10-15 s)")
    ap.add_argument("--ref-text", default="", help="transcript of --ref (f5/cosyvoice2 use it; xtts/chatterbox ignore)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8700)
    ap.add_argument("--lang", default="hi", help="language used for the warm-up line")
    ap.add_argument("--warm", default="Haan maa, main theek hoon.", help="warm-up line synthesised at startup")
    a = ap.parse_args()
    if not os.path.exists(a.ref):
        raise SystemExit(f"reference wav not found: {a.ref}")

    print(f"[load] {a.engine} from {a.ref} ...", flush=True)
    t0 = time.perf_counter()
    State.engine = a.engine
    State.synth, State.sr = load_engine(a.engine, os.path.abspath(a.ref), a.ref_text)
    print(f"[load] model ready in {time.perf_counter() - t0:.1f} s; warming up ...", flush=True)
    t1 = time.perf_counter()
    wav, sr = State.synth(a.warm, a.lang)
    State.sr = int(sr)
    State.ready = True
    print(f"[load] warm-up {time.perf_counter() - t1:.1f} s  (sr={State.sr}, {len(wav) / sr:.1f}s audio)", flush=True)

    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"[serve] {a.engine} on http://{a.host}:{a.port}  (POST /tts, GET /healthz) — Ctrl-C to stop", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
