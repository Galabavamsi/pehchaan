"""Pehchaan Voice Provenance Service: POST /v1/voice/score (SPEC section 7).

  uvicorn serve.app:app --host 0.0.0.0 --port 8090        (run from the ml/ directory)
  env: PEHCHAAN_DEVICE=cpu|cuda (default: cuda if available), PEHCHAAN_MODEL_CONFIG=serve/model_config.json

Request : multipart field `file` (wav; any rate is resampled to 16 kHz mono; only the first 12 s are used)
          or a raw audio/wav body.
Response: {p_synthetic, band, quality{speech_sec, snr_db, ok}, watermark{detected, scheme}, model_version, latency_ms}
Rules   : G3 quality gate -> speech < 4 s or SNR < 10 dB gives band "inconclusive" (never "real").
          Bands come from calibrated p_synthetic and the dev-chosen thresholds in model_config.json.
          A watermark hit is reported separately; it is positive-only evidence.
"""
import io
import json
import os
import sys
import time

import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, File, HTTPException, Request, UploadFile

HERE = os.path.dirname(os.path.abspath(__file__))
ML = os.path.dirname(HERE)
sys.path.insert(0, ML)
from common.audio import resample, windows  # noqa: E402

CFG_PATH = os.environ.get("PEHCHAAN_MODEL_CONFIG", os.path.join(HERE, "model_config.json"))
MAX_S = 12.0
SR = 16000


class Service:
    def __init__(self):
        self.cfg = json.load(open(CFG_PATH))
        dev = os.environ.get("PEHCHAAN_DEVICE") or ("cuda" if torch.cuda.is_available() else "cpu")
        self.device = torch.device(dev)
        from models.ssl_aasist import Model
        self.model = Model()
        wpath = self.cfg["weights"]
        if not os.path.isabs(wpath):
            wpath = os.path.join(HERE, wpath)
        if wpath.endswith(".safetensors"):
            from safetensors.torch import load_file
            sd = load_file(wpath)
        else:
            sd = torch.load(wpath, map_location="cpu", weights_only=False)
        sd = {k: v.float() for k, v in sd.items()}
        self.model.load_state_dict(sd, strict=False)
        self.model.to(self.device).eval()
        self.int8 = False
        if self.device.type == "cpu":
            self.threads = int(os.environ.get("PEHCHAAN_THREADS", min(8, os.cpu_count() or 1)))
            torch.set_num_threads(self.threads)
            if os.environ.get("PEHCHAAN_CPU_INT8", "1") == "1":
                # dynamic int8 Linear layers: ~2x faster on CPU; raw scores move by < 0.2 logits on our checks
                self.model = torch.quantization.quantize_dynamic(self.model, {torch.nn.Linear}, dtype=torch.qint8)
                self.int8 = True
        self.a, self.b = self.cfg["platt"]["a"], self.cfg["platt"]["b"]
        self.p_lo, self.p_hi = self.cfg["bands"]["p_lo"], self.cfg["bands"]["p_hi"]
        self.version = self.cfg["model_version"]
        self._vad = None
        self._perth = None
        self._perth_err = None
        # warm-up so latency_ms reflects steady state (VAD, watermark net and the model are loaded once)
        z = (np.random.default_rng(0).normal(size=SR * 5) * 0.01).astype(np.float32)
        self.quality(z)
        self.watermark(z)
        self.score(z)

    # ---------------------------------------------------------------- quality gate
    def vad(self):
        if self._vad is None:
            from silero_vad import load_silero_vad
            self._vad = load_silero_vad()
        return self._vad

    def quality(self, x):
        from silero_vad import get_speech_timestamps
        ts = get_speech_timestamps(torch.from_numpy(x), self.vad(), sampling_rate=SR, min_silence_duration_ms=200)
        mask = np.zeros(len(x), dtype=bool)
        for t in ts:
            mask[t["start"]:t["end"]] = True
        speech_sec = float(mask.sum() / SR)
        # SNR: speech-frame power vs non-speech power (or the 10th-percentile frame power if there is no pause)
        fr = 400
        n = len(x) // fr
        if n == 0:
            return speech_sec, 0.0
        e = (x[: n * fr].reshape(n, fr) ** 2).mean(1) + 1e-12
        m = mask[: n * fr].reshape(n, fr).mean(1) > 0.5
        sp = e[m].mean() if m.any() else e.mean()
        nz = e[~m].mean() if (~m).sum() >= 5 else np.percentile(e, 10)
        snr = float(10 * np.log10(sp / max(nz, 1e-12)))
        return speech_sec, max(-10.0, min(60.0, snr))

    # ---------------------------------------------------------------- watermark
    def watermark(self, x):
        if self._perth is None and self._perth_err is None:
            try:
                import perth
                self._perth = perth.PerthImplicitWatermarker()
            except Exception as e:  # noqa
                self._perth_err = repr(e)[:120]
        if self._perth is None:
            return {"detected": False, "scheme": None, "checked": [], "note": "perth unavailable"}
        try:
            conf = float(self._perth.get_watermark(x.astype(np.float32), sample_rate=SR))
        except Exception:
            conf = 0.0
        return {"detected": bool(conf >= 0.5), "scheme": "perth" if conf >= 0.5 else None, "checked": ["perth"],
                "confidence": round(conf, 3)}

    # ---------------------------------------------------------------- detector
    @torch.no_grad()
    def score(self, x):
        if self.device.type == "cpu":  # silero-vad sets torch threads to 1 when it loads; restore
            torch.set_num_threads(self.threads)
        segs = windows(x, 64600, hop=32000, max_windows=6)
        t = torch.from_numpy(np.stack(segs)).to(self.device)
        if self.device.type == "cuda":
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                lg = self.model(t).float()
        else:
            lg = self.model(t).float()
        s = float((lg[:, 0] - lg[:, 1]).mean())
        return s, float(1 / (1 + np.exp(-(self.a * s + self.b))))

    def run(self, wav_bytes, debug=False):
        t0 = time.perf_counter()
        try:
            x, sr = sf.read(io.BytesIO(wav_bytes), dtype="float32", always_2d=True)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"could not decode audio: {e}")
        x = resample(x.mean(1), sr, SR)[: int(MAX_S * SR)]
        if len(x) < SR // 2:
            raise HTTPException(status_code=400, detail="audio shorter than 0.5 s")
        speech_sec, snr = self.quality(x)
        ok = speech_sec >= 4.0 and snr >= 10.0
        raw, p = self.score(x)
        if not ok:
            band = "inconclusive"
        elif p >= self.p_hi:
            band = "likely_synthetic"
        elif p <= self.p_lo:
            band = "no_strong_evidence"
        else:
            band = "inconclusive"
        wm = self.watermark(x)
        out = {
            "p_synthetic": round(p, 4),
            "band": band,
            "quality": {"speech_sec": round(speech_sec, 2), "snr_db": round(snr, 1), "ok": bool(ok)},
            "watermark": {"detected": wm["detected"], "scheme": wm["scheme"]},
            "model_version": self.version,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
        if debug:  # not part of the SPEC contract; only with ?debug=1
            out["debug"] = {"raw_score": round(raw, 4), "device": self.device.type, "int8": self.int8, "watermark": wm}
        return out


app = FastAPI(title="Pehchaan Voice Provenance Service", version="0.1")
_svc = None


def svc():
    global _svc
    if _svc is None:
        _svc = Service()
    return _svc


@app.on_event("startup")
def _load():
    svc()


@app.get("/healthz")
def healthz():
    s = svc()
    return {"ok": True, "model_version": s.version, "device": s.device.type}


@app.post("/v1/voice/score")
async def voice_score(request: Request, file: UploadFile = File(None), debug: int = 0):
    data = await file.read() if file is not None else await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="send a wav file as multipart field 'file' or as the request body")
    return svc().run(data, debug=bool(debug))
