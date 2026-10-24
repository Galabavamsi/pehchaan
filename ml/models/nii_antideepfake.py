"""NII AntiDeepfake (nii-yamagishilab/mms-300m-anti-deepfake; weights CC-BY-NC-SA-4.0, NON-COMMERCIAL).

The published checkpoint uses fairseq wav2vec2 naming; we rebuild the same network (MMS-300M SSL
front-end -> mean pool -> linear) on transformers.Wav2Vec2Model and convert the weights, so it runs
without fairseq. Pre-processing follows the model card: layer-norm over the whole waveform, 16 kHz,
whole-utterance input (its native protocol). Softmax index 0 = fake, 1 = real.
Score returned = logit_fake - logit_real (higher = more synthetic).

NIIFineTune wraps the same network for train/finetune.py --init nii (2026-10-24, protocol note "v5"); a checkpoint it
saves loads back here with NIIAntiDeepfake(ckpt=...). Fine-tuned weights inherit the CC-BY-NC-SA-4.0 licence.
"""
import os

import numpy as np
import torch
import torch.nn as nn
from transformers import Wav2Vec2Config, Wav2Vec2Model

from models.ssl_aasist import XLSR_300M_CONFIG, convert_fairseq_state_dict

REPO = "nii-yamagishilab/mms-300m-anti-deepfake"


class _Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.ssl = Wav2Vec2Model(Wav2Vec2Config(**XLSR_300M_CONFIG))
        self.proj_fc = nn.Linear(1024, 2)

    def forward(self, wav):
        emb = self.ssl(wav).last_hidden_state  # [B, T, D]
        return self.proj_fc(emb.mean(dim=1))


def _published_state_dict(net, repo=REPO):
    from huggingface_hub import hf_hub_download
    from safetensors.torch import load_file
    sd = load_file(hf_hub_download(repo, "model.safetensors"))
    sd, rep = convert_fairseq_state_dict(sd, net, src_prefix="m_ssl.model.", dst_prefix="ssl.")
    assert not rep["missing"] and not rep["bad_shape"], rep
    return {k: v for k, v in sd.items() if k not in rep["extra"]}


class NIIFineTune(nn.Module):
    """The NII network as a trainable module: same logit order as our XLS-R + AASIST (0 = spoof, 1 = bona fide), with
    the model card's layer norm over each input clip done inside forward."""

    def __init__(self):
        super().__init__()
        self.net = _Net()

    def forward(self, x):
        return self.net(nn.functional.layer_norm(x, x.shape[-1:]))

    @classmethod
    def pretrained(cls, repo=REPO):
        m = cls()
        m.net.load_state_dict(_published_state_dict(m.net, repo), strict=True)
        return m


class NIIAntiDeepfake:
    def __init__(self, repo=REPO, device=None, max_seconds=16.0, ckpt=None):
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.net = _Net()
        if ckpt:  # a NIIFineTune state dict from train/finetune.py (keys under "net.")
            sd = torch.load(ckpt, map_location="cpu", weights_only=True)
            sd = {k[len("net."):]: v for k, v in sd.items() if k.startswith("net.")}
        else:
            sd = _published_state_dict(self.net, repo)
        self.net.load_state_dict(sd, strict=True)
        self.net.to(self.device).eval()
        self.max_len = int(max_seconds * 16000)
        self.name = os.path.basename(os.path.dirname(ckpt)) if ckpt else repo.split("/")[-1]

    @torch.no_grad()
    def score_batch(self, wavs, max_bs=8):
        out = []
        for w in wavs:  # variable length: one at a time (clips are short)
            w = np.asarray(w, dtype=np.float32)[: self.max_len]
            x = torch.from_numpy(w).to(self.device)
            x = torch.nn.functional.layer_norm(x, x.shape).unsqueeze(0)
            with torch.autocast(device_type=self.device.type, dtype=torch.float16, enabled=self.device.type == "cuda"):
                lg = self.net(x).float()[0]
            out.append(float(lg[0] - lg[1]))
        return np.array(out, dtype=np.float32)
