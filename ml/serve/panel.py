"""Side-by-side detector panel: every detector scores the same clip, plus an equal-weight fused verdict.

Enabled with PEHCHAAN_PANEL (comma list of ids from serve/panel_config.json, e.g. "v1,A,nii,la") and
PEHCHAAN_FUSE (the ids fused into Pehchaan's verdict, default "A,nii,v1": the lowest simulated EER, 4.1%).
Each detector keeps its own threshold (its EER point on the shared simulated test sample) and is scored by the
shared rules in common/scoring.py (also used by eval/clone_vs_detect.py): XLS-R+AASIST models as the mean over the
planned ~4 s windows, NII on whole chunks of up to 16 s of the same clip.
Panel results are evidence for analysts and judges; they never change a payment decision (SPEC G2, shadow mode).
"""
import json
import os
import time

import numpy as np
import torch

from common.scoring import aasist_score, nii_chunks

HERE = os.path.dirname(os.path.abspath(__file__))
ML = os.path.dirname(HERE)
CONFIG = os.path.join(HERE, "panel_config.json")
CKPTS = {"A": os.path.join(ML, "runs", "ours_v3_rc", "best.pt"),
         "la": os.path.join(ML, "runs", "ssl_la", "LA_model.pth")}


def _int8(model):
    return torch.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)


class Panel:
    def __init__(self, svc, ids, fuse):
        self.svc = svc
        self.cfg = json.load(open(CONFIG))
        self.models, self.skipped = {}, {}
        for m in ids:
            try:
                self.models[m] = self._load(m)
            except Exception as e:  # a missing download must not take the service down
                self.skipped[m] = repr(e)[:160]
        self.fuse = [m for m in fuse if m in self.models]
        self.fuse_key = "+".join(sorted(self.fuse))

    def _load(self, m):
        if m not in self.cfg["models"]:
            raise KeyError(f"{m} is not in panel_config.json")
        if m == "v1":
            return ("svc", None)                       # the served model, already loaded
        if m == "nii":
            from models.nii_antideepfake import NIIAntiDeepfake
            d = NIIAntiDeepfake(device=str(self.svc.device))
            if self.svc.device.type == "cpu":
                d.net = _int8(d.net)
            return ("nii", d)
        from models.detectors import SSLAASIST
        if not os.path.exists(CKPTS[m]):
            raise FileNotFoundError(CKPTS[m])
        d = SSLAASIST(CKPTS[m], device=str(self.svc.device))
        if self.svc.device.type == "cpu":
            d.model = _int8(d.model)
        return ("aasist", d)

    @torch.no_grad()
    def _raw(self, m, x, starts):
        kind, d = self.models[m]
        if kind == "svc":
            return float(self.svc.window_scores(x, starts).mean())
        if kind == "aasist":
            return aasist_score(d.logits, x, starts)
        return float(np.mean(d.score_batch(nii_chunks(x))))

    def run(self, x, mask, starts):
        if self.svc.device.type == "cpu":
            torch.set_num_threads(self.svc.threads)
        out, zs = [], {}
        for m in self.models:
            t0 = time.perf_counter()
            raw = self._raw(m, x, starts)
            c = self.cfg["models"][m]
            z = (raw - c["threshold"]) / c["std"]
            zs[m] = z
            out.append({"id": m, "name": c["name"], "trained_on": c["trained_on"], "licence": c.get("licence"),
                        "raw": round(raw, 3), "threshold": c["threshold"], "z": round(z, 3),
                        "verdict": "synthetic" if raw >= c["threshold"] else "genuine",
                        "sim_eer": c["sim_eer"], "in_fusion": m in self.fuse,
                        "latency_ms": round((time.perf_counter() - t0) * 1000, 1)})
        fused = None
        f = (self.cfg["fused"].get(self.fuse_key) if len(self.fuse) > 1 else
             {"threshold": 0.0, "sim_eer": self.cfg["models"][self.fuse[0]]["sim_eer"]} if self.fuse else None)
        if f:   # a combination without a computed threshold (make_panel_config.py) gets no fused verdict
            z = float(np.mean([zs[m] for m in self.fuse]))
            fused = {"members": self.fuse, "z": round(z, 3), "threshold": f["threshold"], "sim_eer": f["sim_eer"],
                     "verdict": "synthetic" if z >= f["threshold"] else "genuine"}
        return {"models": out, "fused": fused, "skipped": self.skipped}
