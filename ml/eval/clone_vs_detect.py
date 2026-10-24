"""Clone-vs-detect benchmark: how convincing each cloner is, and how often each detector catches it.

  python eval/clone_vs_detect.py                 (run from ml/; ~40 min on a laptop CPU, resumable)

How convincing ("speaker similarity"), following ClonEval (arXiv:2504.20581): cosine similarity between WavLM
speaker embeddings (microsoft/wavlm-base-plus-sv, 16 kHz) of a clone and its real speaker. ClonEval compares each
clone with its own reference prompt; we compare with the mean over the speaker's genuine recordings, and report
genuine-vs-genuine similarity of the same speaker as the ceiling a real voice reaches against itself.

How detectable: every panel detector (serve/panel_config.json: ours v1, ours A, NII MMS-300M, off-the-shelf
XLS-R+AASIST LA) and the fused verdict (equal-weight z-mean of A, NII, v1), each at its own threshold (EER point on
the shared simulated test sample), scored as on the bench (CPU int8).
  clean    the consented corpus files (realcall/work/src: S01, S02 genuine lines and content-matched clones)
  amr      the same files through the repo's AMR-NB 8 kHz phone channel (channel/channels.py, seeded per file)
  realcall pre-registered real-call test clips (realcall/work/d2/scores/realcall_eval.csv, split == test): v1 and A
           use their stored scores (as in FINDINGS.md); NII and LA are scored here.
Never trained on: speaker S02 (held out by protocol), Chatterbox, Seed-VC and Sarvam instant voice cloning
(held-out generators). Every row says which. Output: ml/results/clone_vs_detect.json; per-clip scores in
realcall/work/bench/.
"""
import argparse
import gc
import json
import sys
import time
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ML = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML))
from channel import channels as CH  # noqa: E402
from common.audio import load  # noqa: E402

W = ML / "realcall" / "work"
SRC, OUT_DIR = W / "src", W / "bench"
OUT = ML / "results" / "clone_vs_detect.json"
CFG = json.load(open(ML / "serve" / "panel_config.json"))
FUSE = ["A", "nii", "v1"]
HELDOUT_GENS = {"chatterbox", "seedvc", "sarvam_ivc"}
HELDOUT_SPK = {"S02"}
CKPT = {"v1": ML / "runs/ours_v1/best.pt", "A": ML / "runs/ours_v3_rc/best.pt", "la": ML / "runs/ssl_la/LA_model.pth"}


def clips():
    rows = []
    for d in sorted((SRC / "genuine").iterdir()):
        for p in sorted(d.glob("*.wav")):
            rows.append({"file": str(p), "kind": "genuine", "generator": "genuine", "speaker": d.name})
    for d in sorted((SRC / "clone").iterdir()):
        for p in sorted(d.glob("*.wav")):
            parts = p.stem.split("__")
            rows.append({"file": str(p), "kind": "clone", "generator": d.name, "speaker": parts[1] if len(parts) > 1 else "?"})
    return pd.DataFrame(rows)


def detector(m):
    if m == "nii":
        from models.nii_antideepfake import NIIAntiDeepfake
        d = NIIAntiDeepfake(device="cpu")
        d.net = torch.quantization.quantize_dynamic(d.net, {torch.nn.Linear}, dtype=torch.qint8)
    else:
        from models.detectors import SSLAASIST
        d = SSLAASIST(str(CKPT[m]), device="cpu")
        d.model = torch.quantization.quantize_dynamic(d.model, {torch.nn.Linear}, dtype=torch.qint8)
    return d


def score_all(models, key, wavs, ids):
    """Score `wavs` with each model, caching to realcall/work/bench/{key}__{model}.csv (resumable)."""
    out = {}
    for m in models:
        f = OUT_DIR / f"{key}__{m}.csv"
        done = pd.read_csv(f) if f.exists() else pd.DataFrame(columns=["id", "score"])
        have = set(done.id.astype(str))
        todo = [i for i, x in enumerate(ids) if str(x) not in have]
        if todo:
            d = detector(m)
            t0 = time.time()
            for b in range(0, len(todo), 16):
                idx = todo[b:b + 16]
                s = d.score_batch([wavs[i] for i in idx])
                pd.DataFrame({"id": [ids[i] for i in idx], "score": s}).to_csv(f, mode="a", header=not f.exists(), index=False)
                print(f"  {key}/{m}: {min(b + 16, len(todo))}/{len(todo)} ({time.time() - t0:.0f} s)", flush=True)
            del d
            gc.collect()   # four 300M-parameter models in turn on a 16 GB laptop
        sc = pd.read_csv(f).drop_duplicates("id").set_index("id").score
        out[m] = np.array([sc[str(x)] if str(x) in sc.index else sc[x] for x in ids], dtype=np.float32)
    return out


def similarity(df):
    from transformers import AutoFeatureExtractor, WavLMForXVector
    fe = AutoFeatureExtractor.from_pretrained("microsoft/wavlm-base-plus-sv")
    net = WavLMForXVector.from_pretrained("microsoft/wavlm-base-plus-sv").eval()
    emb = []
    with torch.no_grad():
        for f in df.file:
            x = load(f)
            e = net(**fe(x, sampling_rate=16000, return_tensors="pt")).embeddings[0]
            emb.append(torch.nn.functional.normalize(e, dim=-1).numpy())
    emb = np.stack(emb)
    sim = np.zeros(len(df))
    for spk in df.speaker.unique():
        g = np.where((df.speaker == spk).values & (df.kind == "genuine").values)[0]
        for i in np.where((df.speaker == spk).values)[0]:
            ref = g[g != i]
            sim[i] = float((emb[ref] @ emb[i]).mean()) if len(ref) else np.nan
    return sim


def verdicts(scores):
    out = {m: scores[m] >= CFG["models"][m]["threshold"] for m in scores}
    if all(m in scores for m in FUSE):
        z = np.mean([(scores[m] - CFG["models"][m]["threshold"]) / CFG["models"][m]["std"] for m in FUSE], axis=0)
        out["fused"] = z >= CFG["fused"]["+".join(sorted(FUSE))]["threshold"]
    return out


def table(df, flags, mask=None):
    """Per generator: caught rate (clones) or flagged rate (genuine) for each detector."""
    mask = np.ones(len(df), bool) if mask is None else mask
    res = {}
    for gen in df.generator[mask].unique():
        sel = mask & (df.generator == gen).values
        res[gen] = {"n": int(sel.sum()), **{m: round(float(v[sel].mean()), 4) for m, v in flags.items()}}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="v1,A,nii,la")
    ap.add_argument("--skip-realcall", action="store_true")
    a = ap.parse_args()
    models = a.models.split(",")
    torch.set_num_threads(8)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = clips()
    print(f"{len(df)} clips: {df.groupby('generator').size().to_dict()}", flush=True)
    clean = [load(f) for f in df.file]
    amr = [CH.amr(x, np.random.default_rng(zlib.crc32(Path(f).name.encode()))) for x, f in zip(clean, df.file)]
    ids = [Path(f).name for f in df.file]
    sim_file = OUT_DIR / "similarity.csv"
    if sim_file.exists():
        df["similarity"] = pd.read_csv(sim_file).set_index("id").similarity.reindex(ids).values
    else:
        print("speaker similarity (WavLM x-vectors)...", flush=True)
        df["similarity"] = similarity(df)
        pd.DataFrame({"id": ids, "similarity": df.similarity}).to_csv(sim_file, index=False)
    result = {"method": __doc__.split("\n\n", 1)[1].strip(), "models": {m: CFG["models"][m]["name"] for m in models},
              "fused_members": FUSE, "conditions": {}}
    never = (df.speaker.isin(HELDOUT_SPK) | df.generator.isin(HELDOUT_GENS) | (df.kind == "genuine")).values
    for cond, wavs in (("clean", clean), ("amr", amr)):
        print(f"condition {cond}...", flush=True)
        flags = verdicts(score_all(models, f"{cond}", wavs, ids))
        result["conditions"][cond] = {"all_speakers": table(df, flags),
                                      "heldout_speaker_S02": table(df, flags, (df.speaker == "S02").values),
                                      "never_trained_rows": table(df, flags, never)}
    gens = {}
    for gen, g in df.groupby("generator"):
        gens[gen] = {"n": int(len(g)), "similarity_mean": round(float(g.similarity.mean()), 4),
                     "similarity_sd": round(float(g.similarity.std()), 4),
                     "heldout": gen in HELDOUT_GENS, "kind": g.kind.iloc[0]}
    result["generators"] = gens
    if not a.skip_realcall:
        rc = pd.read_csv(W / "d2/scores/realcall_eval.csv")
        rc = rc[rc.split == "test"].reset_index(drop=True)
        print(f"real-call test clips: {len(rc)}", flush=True)
        stored = {"v1": "real__ours_v1.csv", "A": "real__ours_v3_rc.csv"}
        scores = {}
        for m, f in stored.items():
            s = pd.read_csv(W / "d2/scores" / f).drop_duplicates("utt_id").set_index("utt_id").score
            scores[m] = s.reindex(rc.utt_id).values.astype(np.float32)
        new = [m for m in models if m not in stored]
        if new:
            wavs = [load(W / p) for p in rc.path]
            scores.update(score_all(new, "realcall", wavs, list(rc.utt_id)))
        ok = np.all([~np.isnan(v) for v in scores.values()], axis=0)
        rc2 = rc[ok].reset_index(drop=True)
        flags = verdicts({m: v[ok] for m, v in scores.items()})
        rc2["generator"] = np.where(rc2.label == "bonafide", "genuine", rc2.generator)
        result["conditions"]["realcall"] = {"all": table(rc2, flags),
                                            "by_device": {dv: table(rc2, flags, (rc2.device == dv).values) for dv in rc2.device.unique()}}
    OUT.write_text(json.dumps(result, indent=1))
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
