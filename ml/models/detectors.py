"""Uniform wrapper around every detector we evaluate.

Each detector exposes  .score_batch(list[np.ndarray @16k]) -> np.ndarray of "spoof scores"
(higher = more likely synthetic, an uncalibrated logit-like value) and .name.
Utterance score = mean over sliding 4.04 s windows (64600 samples, hop 2 s, <= 8 windows), the
same for every detector, so the comparison is fair.
"""
import os
import sys
import time

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.audio import windows  # noqa: E402

WIN = 64600


def _device(dev=None):
    if dev:
        return torch.device(dev)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


class SSLAASIST:
    """XLS-R-300M + AASIST. kind='la' -> LA_model.pth, 'df' -> Best_LA_model_for_DF.pth,
    or a path to our fine-tuned checkpoint (state dict in HF naming, saved by train/finetune.py)."""

    def __init__(self, ckpt, device=None, name=None, fp16=True):
        from models.ssl_aasist import Model, convert_fairseq_state_dict
        self.device = _device(device)
        self.model = Model()
        sd = torch.load(ckpt, map_location="cpu", weights_only=False)
        if isinstance(sd, dict) and "state_dict" in sd:
            sd = sd["state_dict"]
        if any(k.startswith("ssl_model.model.encoder.pos_conv.0") or k.startswith("module.ssl_model.model.encoder.pos_conv.0")
               for k in sd):
            sd, rep = convert_fairseq_state_dict(sd, self.model)
            assert not rep["missing"] and not rep["bad_shape"], rep
            sd = {k: v for k, v in sd.items() if k not in rep["extra"]}
        missing, unexpected = self.model.load_state_dict(sd, strict=False)
        missing = [m for m in missing if "masked_spec_embed" not in m]
        assert not missing, f"missing keys: {missing[:5]}"
        self.model.to(self.device).eval()
        self.fp16 = fp16 and self.device.type == "cuda"
        self.name = name or os.path.basename(ckpt)

    @torch.no_grad()
    def logits(self, wavs_fixed):
        x = torch.from_numpy(np.stack(wavs_fixed)).float().to(self.device)
        with torch.autocast(device_type=self.device.type, dtype=torch.float16, enabled=self.fp16):
            out = self.model(x)
        return out.float().cpu().numpy()

    def score_batch(self, wavs, max_bs=16):
        segs, owner = [], []
        for i, w in enumerate(wavs):
            for s in windows(w, WIN):
                segs.append(s)
                owner.append(i)
        scores = np.zeros(len(segs), dtype=np.float32)
        for b in range(0, len(segs), max_bs):
            lg = self.logits(segs[b:b + max_bs])
            scores[b:b + max_bs] = lg[:, 0] - lg[:, 1]  # spoof - bonafide
        owner = np.array(owner)
        return np.array([scores[owner == i].mean() for i in range(len(wavs))], dtype=np.float32)


class HFAudioClassifier:
    """Any transformers AutoModelForAudioClassification detector. spoof_label: name/idx of the fake class."""

    def __init__(self, repo, spoof_labels=("fake", "spoof", "deepfake", "synthetic", "ai"), device=None, fp16=True):
        from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
        self.device = _device(device)
        self.fe = AutoFeatureExtractor.from_pretrained(repo)
        self.model = AutoModelForAudioClassification.from_pretrained(repo).to(self.device).eval()
        id2label = {int(k): str(v).lower() for k, v in self.model.config.id2label.items()}
        cand = [i for i, l in id2label.items() if any(s == l or s in l.split("_") or l.startswith(s) for s in spoof_labels)]
        assert len(cand) == 1, f"cannot identify spoof label in {id2label}"
        self.spoof_idx = cand[0]
        self.id2label = id2label
        self.fp16 = fp16 and self.device.type == "cuda"
        self.name = repo

    @torch.no_grad()
    def score_batch(self, wavs, max_bs=16):
        segs, owner = [], []
        for i, w in enumerate(wavs):
            for s in windows(w, WIN):
                segs.append(s)
                owner.append(i)
        scores = np.zeros(len(segs), dtype=np.float32)
        for b in range(0, len(segs), max_bs):
            inp = self.fe(segs[b:b + max_bs], sampling_rate=16000, return_tensors="pt", padding=True)
            inp = {k: v.to(self.device) for k, v in inp.items()}
            with torch.autocast(device_type=self.device.type, dtype=torch.float16, enabled=self.fp16):
                lg = self.model(**inp).logits.float()
            lp = torch.log_softmax(lg, -1).cpu().numpy()
            other = np.delete(lp, self.spoof_idx, axis=1)
            scores[b:b + max_bs] = lp[:, self.spoof_idx] - np.logaddexp.reduce(other, axis=1)
        owner = np.array(owner)
        return np.array([scores[owner == i].mean() for i in range(len(wavs))], dtype=np.float32)


def timed_latency(det, seconds=10.0, n=10, warmup=2):
    x = (np.random.default_rng(0).normal(size=int(seconds * 16000)) * 0.05).astype(np.float32)
    for _ in range(warmup):
        det.score_batch([x])
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    ts = []
    for _ in range(n):
        t = time.perf_counter()
        det.score_batch([x])
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        ts.append((time.perf_counter() - t) * 1000)
    return {"median_ms": float(np.median(ts)), "p95_ms": float(np.percentile(ts, 95)), "n": n, "clip_s": seconds}
