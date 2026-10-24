"""Fine-tune XLS-R-300M + AASIST (initialised from the SSL_Anti-spoofing LA checkpoint) on our corpus.

  python train/finetune.py --src_manifest corpus_src.csv --eval_manifest corpus_eval.csv --out runs/ours_full
     [--init la|df|nii|<ckpt>] [--no_channel_aug] [--exclude_sources team,team_clone] [--epochs 6]

Training data = split=="train" rows whose generator is NOT held out and whose speaker is NOT held out.
Each training example: random ~5 s crop -> random channel (clean/pstn/amr/opus/replay; same code as the
evaluation channels but a fresh random draw every time) -> optional RawBoost (series LnL + ISD + SSI as in
Tak et al.) -> random gain -> 64600-sample window. Sampling is balanced: 50 % bona fide / 50 % spoof, and
within each class every (source, generator) group gets equal mass, so the few team clips are not drowned
by FLEURS/ASVspoof.
Model selection: mean EER over channels on the dev split (seen generators only) after every epoch.

Real-call data (v3, 2026-10-17): --realcall_manifest adds real phone-call captures (realcall/ingest.py). Train rows
are used as they are (no simulated channel or RawBoost on top: they already went through a real network) and get
a fixed share of each class's sampling mass (--realcall_weight). Dev rows are scored as an extra "realcall" channel
in model selection. --aug_set v3 adds the speakerphone channel learned from real calls (realcall/learned_channel.py).
Held-out speakers and generators stay out of training exactly as before.

--init nii (2026-10-24, common/protocol.py note "v5"): start from NII AntiDeepfake MMS-300M instead (its own network:
SSL -> mean pool -> linear, input layer-normed per clip; CC-BY-NC-SA-4.0, research only). Same data, sampling,
augmentation and model selection; the checkpoint loads with eval/score.py --detector niickpt:<best.pt>.
"""
import argparse
import json
import math
import os
import random
import sys
import time

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from common.audio import fix_length, load_any, normalize_rms, windows  # noqa: E402
from common.protocol import HELDOUT_GENERATORS, HELDOUT_SPEAKERS  # noqa: E402
from eval.metrics import eer  # noqa: E402

WIN = 64600
CH_P = {"clean": 0.2, "pstn": 0.2, "amr": 0.2, "opus": 0.2, "replay": 0.2}
# v2: adds training-only telephony variety (low AMR modes, codec tandems, handset NS/AGC, codec->speakerphone)
CH_P_V2 = {"clean": 0.12, "pstn": 0.10, "amr": 0.10, "opus": 0.12, "replay": 0.10, "amr_lowrate": 0.12,
           "tandem": 0.12, "narrowband_dsp": 0.12, "codec_replay": 0.10}
# v3: v2 scaled to 70 % plus 30 % of the speakerphone channel learned from real calls
CH_P_V3 = {**{k: v * 0.7 for k, v in CH_P_V2.items()}, "speakerphone_learned": 0.30}


def rawboost(x, rng):
    from train import RawBoost as RB
    fs = 16000
    algo = rng.choice([0, 1, 2, 3])  # 0 none
    if algo == 0:
        return x
    y = x.copy()
    if algo in (1, 3):  # LnL convolutive
        y = RB.LnL_convolutive_noise(y, 5, 5, 20, 8000, 100, 1000, 10, 100, 0, 0, 5, 20, fs)
    if algo in (2, 3):  # ISD impulsive + SSI stationary
        y = RB.ISD_additive_noise(y, 10, 2)
        y = RB.SSI_additive_noise(y, 10, 40, 5, 20, 8000, 100, 1000, 10, 100, 0, 0, fs)
    return y.astype(np.float32)


class TrainSet(Dataset):
    def __init__(self, df, channel_aug=True, rawboost_p=0.3, seed=0, ch_p=None):
        self.paths = df.src16.tolist()
        self.native = (df["native"].fillna(False).astype(bool) if "native" in df else pd.Series(False, index=df.index)).tolist()
        self.y = (df.label == "spoof").astype(int).tolist()
        self.channel_aug = channel_aug
        self.rawboost_p = rawboost_p
        self.seed = seed
        self.ch_p = ch_p or CH_P

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, i):
        wi = torch.utils.data.get_worker_info()
        rng = np.random.default_rng((self.seed * 1000003 + i * 7919 + int(time.time() * 1e6)) % (2 ** 32) + (wi.id if wi else 0))
        x = load_any(self.paths[i])
        n = int(16000 * 5.0)
        if len(x) > n:
            s = int(rng.integers(0, len(x) - n + 1))
            x = x[s:s + n]
        if self.channel_aug and not self.native[i]:
            from channel.channels import FUNCS, apply
            ch = rng.choice(list(self.ch_p), p=list(self.ch_p.values()))
            if ch == "speakerphone_learned" and ch not in FUNCS:
                # DataLoader workers started with "spawn" (Windows, macOS) import a fresh channels module, so the
                # registration done in the parent process isn't there: register in this worker too.
                from realcall.learned_channel import register
                register()
            try:
                x = apply(x, ch, rng)
            except Exception:
                pass
        if not self.native[i] and rng.random() < self.rawboost_p:
            try:
                x = rawboost(x, rng)
            except Exception:
                pass
        x = normalize_rms(x, float(rng.uniform(-32, -20)))
        x = fix_length(x, WIN, rng, random_crop=True)
        return torch.from_numpy(x.astype(np.float32)), self.y[i]


def balanced_weights(df, realcall_weight=None):
    g = df.label + "|" + df.source.astype(str) + "|" + df.generator.astype(str)
    counts = g.value_counts()
    w = np.array(g.map(lambda k: 1.0 / counts[k]).values, dtype=np.float64)
    # equal total mass per class; real-call rows (if any) get exactly realcall_weight of each class's mass
    rc = (df.source == "realcall").values
    for lab in ("bonafide", "spoof"):
        m = (df.label == lab).values
        if realcall_weight and (m & rc).any() and (m & ~rc).any():
            w[m & rc] = w[m & rc] / w[m & rc].sum() * 0.5 * realcall_weight
            w[m & ~rc] = w[m & ~rc] / w[m & ~rc].sum() * 0.5 * (1 - realcall_weight)
        else:
            w[m] = w[m] / w[m].sum() * 0.5
    return w


def load_realcall(path):
    """Real-call rows from realcall/ingest.py: QC-ok, paths made absolute relative to the manifest's folder."""
    rc = pd.read_csv(path)
    rc = rc[(rc.qc == "ok") & rc.path.notna() & rc.label.isin(["bonafide", "spoof"])]
    if "gate_window" in rc:
        rc = rc[rc.gate_window.astype(str) != "True"]       # gate windows duplicate live chunks
    base = os.path.dirname(os.path.abspath(path))
    rc = rc.copy()
    rc["path"] = [p if os.path.isabs(p) else os.path.join(base, p) for p in rc.path]
    rc["src16"] = rc["path"]
    rc["source"] = "realcall"
    rc["native"] = True
    rc["channel"] = "realcall"
    return rc


@torch.no_grad()
def evaluate(model, df, device, bs=24, max_items=None):
    model.eval()
    if max_items and len(df) > max_items:
        df = df.sample(n=max_items, random_state=0)
    scores = []
    for b in range(0, len(df), bs):
        chunk = df.iloc[b:b + bs]
        segs, owner = [], []
        for k, p in enumerate(chunk.path):
            for s in windows(load_any(p), WIN, max_windows=4):
                segs.append(s)
                owner.append(k)
        x = torch.from_numpy(np.stack(segs)).to(device)
        with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
            lg = model(x).float()
        s = (lg[:, 0] - lg[:, 1]).cpu().numpy()
        owner = np.array(owner)
        scores += [float(s[owner == k].mean()) for k in range(len(chunk))]
    df = df.copy()
    df["score"] = scores
    res = {}
    for ch, g in df.groupby("channel"):
        y = (g.label == "spoof").astype(int).values
        if y.min() != y.max():
            res[ch] = eer(y, g.score.values)[0]
    model.train()
    return res, df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src_manifest", required=True)
    ap.add_argument("--eval_manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--init", default="la")
    ap.add_argument("--weights_dir", default=os.path.expanduser("~/weights/ssl_aasist/Pre_trained_SSL_anti-spoofing_models"))
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--steps_per_epoch", type=int, default=600)
    ap.add_argument("--bs", type=int, default=16)
    ap.add_argument("--lr_ssl", type=float, default=3e-6)
    ap.add_argument("--lr_head", type=float, default=3e-5)
    ap.add_argument("--no_channel_aug", action="store_true")
    ap.add_argument("--rawboost_p", type=float, default=0.3)
    ap.add_argument("--aug_set", default="v1", choices=["v1", "v2", "v3"])
    ap.add_argument("--realcall_manifest", default="", help="realcall.csv from realcall/ingest.py (paths relative to it)")
    ap.add_argument("--realcall_weight", type=float, default=0.25, help="share of each class's sampling mass for real-call rows")
    ap.add_argument("--dry_run", action="store_true", help="build the data, draw a few samples, print composition, exit")
    ap.add_argument("--exclude_sources", default="")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--dev_max", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed)
    json.dump(vars(a), open(os.path.join(a.out, "args.json"), "w"), indent=1)

    src = pd.read_csv(a.src_manifest)
    tr = src[(src.split == "train") & (~src.generator.isin(HELDOUT_GENERATORS)) & (~src.speaker.astype(str).isin(HELDOUT_SPEAKERS))]
    if a.exclude_sources:
        tr = tr[~tr.source.isin(a.exclude_sources.split(","))]
    ev = pd.read_csv(a.eval_manifest)
    dev = ev[(ev.split == "dev") & (ev.source != "asv19") & (~ev.generator.isin(HELDOUT_GENERATORS)) & (~ev.speaker.astype(str).isin(HELDOUT_SPEAKERS))]
    rc_dev = pd.DataFrame()
    if a.realcall_manifest:
        rc = load_realcall(a.realcall_manifest)
        keep = lambda d: d[(~d.generator.isin(HELDOUT_GENERATORS)) & (~d.speaker.astype(str).isin(HELDOUT_SPEAKERS))]
        rc_tr, rc_dev = keep(rc[rc.split == "train"]), keep(rc[rc.split == "dev"])
        tr = pd.concat([tr.assign(native=False), rc_tr], ignore_index=True)
        print("realcall train", len(rc_tr), rc_tr.groupby("label").size().to_dict(), "| dev", len(rc_dev), flush=True)
    if a.aug_set == "v3":
        from realcall.learned_channel import _params, register
        register()
        _params()   # fail here, not inside a worker, if learned_channel.npz is missing
    print("train", len(tr), tr.groupby(["label", "source"]).size().to_dict(), flush=True)
    print("dev", len(dev), flush=True)
    ch_p = {"v1": CH_P, "v2": CH_P_V2, "v3": CH_P_V3}[a.aug_set]
    if a.dry_run:
        w = balanced_weights(tr, a.realcall_weight if a.realcall_manifest else None)
        mass = pd.Series(w).groupby((tr.label + "|" + tr.source.astype(str)).values).sum().round(3).to_dict()
        print("sampling mass by class|source:", mass, flush=True)
        ds = TrainSet(tr, channel_aug=not a.no_channel_aug, rawboost_p=a.rawboost_p, seed=a.seed, ch_p=ch_p)
        rng = np.random.default_rng(a.seed)
        for i in rng.choice(len(tr), size=min(12, len(tr)), replace=False, p=w / w.sum()):
            x, y = ds[int(i)]
            print(f"  sample {tr.source.iloc[i]:10s} {tr.label.iloc[i]:8s} native={ds.native[i]} len={len(x)} "
                  f"rms={float(x.pow(2).mean().sqrt()):.3f}", flush=True)
        print("dry run ok", flush=True)
        return

    device = torch.device("cuda")
    if a.init == "nii":
        from models.nii_antideepfake import NIIFineTune
        model = NIIFineTune.pretrained()
    else:
        from models.ssl_aasist import Model, convert_fairseq_state_dict
        model = Model()
        init = {"la": "LA_model.pth", "df": "Best_LA_model_for_DF.pth"}.get(a.init)
        ck = os.path.join(a.weights_dir, init) if init else a.init
        sd = torch.load(ck, map_location="cpu", weights_only=False)
        if any(k.startswith("ssl_model.model.encoder.pos_conv.0") for k in sd):
            sd, rep = convert_fairseq_state_dict(sd, model)
            sd = {k: v for k, v in sd.items() if k not in rep["extra"]}
        model.load_state_dict(sd, strict=False)
    model.to(device).train()

    ssl_prefix = ("ssl_model.", "net.ssl.")
    ssl_params = [p for n, p in model.named_parameters() if n.startswith(ssl_prefix)]
    head_params = [p for n, p in model.named_parameters() if not n.startswith(ssl_prefix)]
    opt = torch.optim.AdamW([{"params": ssl_params, "lr": a.lr_ssl}, {"params": head_params, "lr": a.lr_head}], weight_decay=1e-4)
    total = a.epochs * a.steps_per_epoch
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / 200) * 0.5 * (1 + math.cos(math.pi * min(1.0, s / total))))
    crit = nn.CrossEntropyLoss()

    w = balanced_weights(tr, a.realcall_weight if a.realcall_manifest else None)
    sampler = WeightedRandomSampler(torch.as_tensor(w, dtype=torch.double), num_samples=a.steps_per_epoch * a.bs, replacement=True)
    ds = TrainSet(tr, channel_aug=not a.no_channel_aug, rawboost_p=a.rawboost_p, seed=a.seed, ch_p=ch_p)
    dl = DataLoader(ds, batch_size=a.bs, sampler=sampler, num_workers=a.workers, drop_last=True, persistent_workers=True,
                    prefetch_factor=4)

    # epoch-0 reference (pretrained model on our dev set)
    def dev_eval():
        res, _ = evaluate(model, dev, device, max_items=a.dev_max)
        if len(rc_dev) and rc_dev.label.nunique() == 2:
            res.update(evaluate(model, rc_dev, device)[0])    # always all real-call dev rows, as channel "realcall"
        return res

    res0 = dev_eval()
    log = [{"epoch": 0, "dev_eer": res0, "dev_eer_mean": float(np.mean(list(res0.values())))}]
    print("epoch 0 dev EER", {k: round(v, 4) for k, v in res0.items()}, flush=True)
    best = float("inf")  # best fine-tuned epoch (epoch 0 = pretrained reference only)
    step = 0
    for ep in range(1, a.epochs + 1):
        t0 = time.time()
        tot_loss = 0.0
        for x, y in dl:
            x, y = x.to(device, non_blocking=True), torch.as_tensor(y, device=device)
            # bona fide = class 1, spoof = class 0 (original convention)
            target = 1 - y
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                out = model(x)
            loss = crit(out.float(), target)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            opt.step()
            sched.step()
            tot_loss += loss.item()
            step += 1
            if step % 100 == 0:
                print(f"ep {ep} step {step} loss {tot_loss / (step - (ep - 1) * a.steps_per_epoch):.4f} {time.time() - t0:.0f}s", flush=True)
        res = dev_eval()
        m = float(np.mean(list(res.values())))
        log.append({"epoch": ep, "loss": tot_loss / a.steps_per_epoch, "dev_eer": res, "dev_eer_mean": m, "time_s": time.time() - t0})
        print(f"epoch {ep} dev EER mean {m:.4f}", {k: round(v, 4) for k, v in res.items()}, flush=True)
        if m < best:
            best = m
            torch.save(model.state_dict(), os.path.join(a.out, "best.pt"))
            json.dump({"epoch": ep, "dev_eer_mean": m}, open(os.path.join(a.out, "best.json"), "w"))
        json.dump(log, open(os.path.join(a.out, "log.json"), "w"), indent=1)
    print("best dev EER", best, flush=True)


if __name__ == "__main__":
    main()
