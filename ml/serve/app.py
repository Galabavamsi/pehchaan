"""Pehchaan Voice Provenance Service: POST /v1/voice/score (SPEC section 7).

  uvicorn serve.app:app --host 0.0.0.0 --port 8090        (run from the ml/ directory)
  env: PEHCHAAN_DEVICE=cpu|cuda (default: cuda if available), PEHCHAAN_MODEL_CONFIG=serve/model_config.json

Request : multipart field `file` (any common format: wav, flac, ogg, mp3, m4a/aac, opus, webm; resampled to
          16 kHz mono) or a raw audio body. Only the first PEHCHAAN_MAX_SECONDS (default 60 s) are decoded and
          scored; the ffmpeg fallback is stopped after PEHCHAAN_DECODE_TIMEOUT seconds (default 20).
Response: {p_synthetic, band, quality{speech_sec, snr_db, ok}, watermark{detected, scheme}, model_version, latency_ms,
          audio_seconds, audio_seconds_at_least, seconds_scored, aggregate{raw_mean, raw_max, n_windows},
          windows[{t, raw, p, speech}]}. audio_seconds is the file's length; when the decoder can't tell it without
          decoding everything, it is how much was read and audio_seconds_at_least is true.
Rules   : G3 quality gate -> speech < 4 s or SNR < 10 dB gives band "inconclusive" (never "real").
          The clip is scored in ~4 s windows (2 s hop); windows that are mostly silence are skipped; the
          call-level score is the mean window logit (longer speech -> more reliable, see FINDINGS). The window plan
          is common/scoring.py, shared with the detector bench and the clone-vs-detect benchmark.
          Bands come from calibrated p_synthetic and the dev-chosen thresholds in model_config.json.
          A watermark hit is reported separately; it is positive-only evidence.
"""
import json
import os
import sys
import time

import numpy as np
import torch
from fastapi import FastAPI, File, HTTPException, Request, UploadFile

HERE = os.path.dirname(os.path.abspath(__file__))
ML = os.path.dirname(HERE)
sys.path.insert(0, ML)
from common.audio import decode_bytes  # noqa: E402
from common.scoring import MAX_S, SR, WIN, clip, plan_windows, speech_mask, window_segments  # noqa: E402,F401

CFG_PATH = os.environ.get("PEHCHAAN_MODEL_CONFIG", os.path.join(HERE, "model_config.json"))
DECODE_TIMEOUT_S = float(os.environ.get("PEHCHAAN_DECODE_TIMEOUT", "20"))


def served_model(cfg, device):
    """The served detector: models.ssl_aasist.Model with the exported weights (fp16 on disk), run in fp32."""
    from models.ssl_aasist import Model
    model = Model()
    wpath = cfg["weights"]
    if not os.path.isabs(wpath):
        wpath = os.path.join(HERE, wpath)
    if wpath.endswith(".safetensors"):
        from safetensors.torch import load_file
        sd = load_file(wpath)
    else:
        sd = torch.load(wpath, map_location="cpu", weights_only=False)
    sd = {k: v.float() for k, v in sd.items()}
    model.load_state_dict(sd, strict=False)
    return model.to(device).eval()


class Service:
    def __init__(self):
        self.cfg = json.load(open(CFG_PATH))
        dev = os.environ.get("PEHCHAAN_DEVICE") or ("cuda" if torch.cuda.is_available() else "cpu")
        self.device = torch.device(dev)
        self.model = served_model(self.cfg, self.device)
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
        self._perth = None
        self._perth_err = None
        # warm-up so latency_ms reflects steady state (VAD, watermark net and the model are loaded once)
        z = (np.random.default_rng(0).normal(size=SR * 5) * 0.01).astype(np.float32)
        self.quality(z)
        self.watermark(z)
        self.score(z)

    # ---------------------------------------------------------------- quality gate
    def speech_mask(self, x):
        return speech_mask(x)

    def quality(self, x, mask=None):
        mask = self.speech_mask(x) if mask is None else mask
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
    def calibrate(self, raw):
        return float(1 / (1 + np.exp(-(self.a * raw + self.b))))

    @torch.no_grad()
    def window_scores(self, x, starts, batch=8):
        """Raw spoof-minus-bona-fide logit per window (higher = more likely synthetic)."""
        if self.device.type == "cpu":  # silero-vad sets torch threads to 1 when it loads; restore
            torch.set_num_threads(self.threads)
        segs = window_segments(x, starts)
        out = []
        for b in range(0, len(segs), batch):
            t = torch.from_numpy(np.stack(segs[b:b + batch])).to(self.device)
            if self.device.type == "cuda":
                with torch.autocast(device_type="cuda", dtype=torch.float16):
                    lg = self.model(t).float()
            else:
                lg = self.model(t).float()
            out.extend((lg[:, 0] - lg[:, 1]).cpu().numpy().tolist())
        return np.array(out, dtype=np.float32)

    def score(self, x, mask=None):
        starts = plan_windows(len(x), mask)
        w = self.window_scores(x, starts)
        s = float(w.mean())
        return s, self.calibrate(s), starts, w

    def decode(self, data):
        """Any common audio format -> (16 kHz mono clip of at most MAX_S, the file's duration in s, whether that
        duration is exact). Only the first MAX_S seconds are decoded, so a long upload costs no more than that."""
        try:
            x, seconds, exact = decode_bytes(data, SR, max_s=MAX_S, timeout=DECODE_TIMEOUT_S)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"could not decode audio: {str(e)[:200]}")
        if len(x) < SR // 2:
            raise HTTPException(status_code=400, detail="audio shorter than 0.5 s")
        return clip(x), seconds, exact

    def run(self, wav_bytes, debug=False):
        t0 = time.perf_counter()
        x, audio_seconds, exact = self.decode(wav_bytes)
        mask = self.speech_mask(x)
        speech_sec, snr = self.quality(x, mask)
        ok = speech_sec >= 4.0 and snr >= 10.0
        raw, p, starts, w = self.score(x, mask)
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
            "audio_seconds": round(audio_seconds, 2),
            "audio_seconds_at_least": not exact,
            "seconds_scored": round(len(x) / SR, 2),
            "aggregate": {"raw_mean": round(raw, 4), "raw_max": round(float(w.max()), 4), "n_windows": len(starts)},
            "windows": [{"t": round(s / SR, 2), "raw": round(float(v), 3), "p": round(self.calibrate(float(v)), 4),
                         "speech": round(float(mask[s:s + WIN].mean()), 2)} for s, v in zip(starts, w)],
        }
        if debug:  # not part of the SPEC contract; only with ?debug=1
            out["debug"] = {"raw_score": round(raw, 4), "device": self.device.type, "int8": self.int8, "watermark": wm}
        return out


app = FastAPI(title="Pehchaan Voice Provenance Service", version="0.1")
_svc = None
_panel = None
# default: a panel of just the served model (no extra memory), so #/bench works on a small server too;
# the laptop runs the full panel with PEHCHAAN_PANEL=v1,A,nii,la
PANEL_IDS = [m.strip() for m in os.environ.get("PEHCHAAN_PANEL", "v1").split(",") if m.strip()]
FUSE_IDS = [m.strip() for m in os.environ.get("PEHCHAAN_FUSE", "A,nii,v1").split(",") if m.strip()]


def svc():
    global _svc
    if _svc is None:
        _svc = Service()
    return _svc


def panel():
    global _panel
    if not PANEL_IDS:
        raise HTTPException(status_code=404, detail="the detector panel is off (set PEHCHAAN_PANEL, e.g. v1,A,nii,la)")
    if _panel is None:
        from serve.panel import Panel
        _panel = Panel(svc(), PANEL_IDS, FUSE_IDS)
    return _panel


@app.on_event("startup")
def _load():
    svc()
    if PANEL_IDS:
        panel()


@app.get("/healthz")
def healthz():
    s = svc()
    out = {"ok": True, "model_version": s.version, "device": s.device.type, "max_seconds": MAX_S}
    if _panel is not None:
        out["panel"] = {"models": list(_panel.models), "fused": _panel.fuse, "skipped": _panel.skipped}
    return out


@app.post("/v1/voice/score")
async def voice_score(request: Request, file: UploadFile = File(None), debug: int = 0):
    data = await file.read() if file is not None else await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="send an audio file as multipart field 'file' or as the request body")
    return svc().run(data, debug=bool(debug))


@app.post("/v1/voice/panel")
async def voice_panel(request: Request, file: UploadFile = File(None)):
    """Every panel detector on the same clip, side by side, plus the fused verdict (evidence only, never decides)."""
    data = await file.read() if file is not None else await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="send an audio file as multipart field 'file' or as the request body")
    p, s = panel(), svc()
    t0 = time.perf_counter()
    x, audio_seconds, exact = s.decode(data)
    mask = s.speech_mask(x)
    speech_sec, snr = s.quality(x, mask)
    starts = plan_windows(len(x), mask)
    out = p.run(x, mask, starts)
    out.update({"quality": {"speech_sec": round(speech_sec, 2), "snr_db": round(snr, 1),
                            "ok": bool(speech_sec >= 4.0 and snr >= 10.0)},
                "audio_seconds": round(audio_seconds, 2), "audio_seconds_at_least": not exact,
                "seconds_scored": round(len(x) / SR, 2),
                "n_windows": len(starts), "latency_ms": round((time.perf_counter() - t0) * 1000, 1)})
    return out
