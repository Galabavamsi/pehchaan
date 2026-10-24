"""Clone-vs-detect benchmark: how convincing each cloner is, and how often each detector catches it.

  python eval/clone_vs_detect.py                 (run from ml/; ~3 h on a laptop CPU, resumable)
  python eval/clone_vs_detect.py --tables        (markdown tables for FINDINGS.md from the JSON)

How convincing ("speaker similarity"), following ClonEval (arXiv:2504.20581): cosine similarity between WavLM
speaker embeddings (microsoft/wavlm-base-plus-sv, 16 kHz) of a clone and its real speaker. ClonEval compares each
clone with its own reference prompt; we compare with the mean over the speaker's genuine recordings, and report
genuine-vs-genuine similarity of the same speaker as the ceiling a real voice reaches against itself.

How detectable: every panel detector (serve/panel_config.json: ours v1, ours A, NII MMS-300M, off-the-shelf
XLS-R+AASIST LA) and the fused verdict (equal-weight z-mean of A, NII, v1), each at its own threshold (EER point on
the shared simulated test sample). Every clip is scored exactly as on the bench (serve/panel.py), by the rules in
common/scoring.py: the first 60 s of the clip, XLS-R+AASIST models as the mean logit over ~4 s windows with mostly
silent windows dropped (Silero VAD), NII as the mean over chunks of up to 16 s, CPU int8. v1 is the served export
(serve/model_config.json), as on the bench.
  clean    the consented corpus files (realcall/work/src: S01, S02 genuine lines and content-matched clones)
  amr      the same files through the repo's AMR-NB 8 kHz phone channel (channel/channels.py, seeded per file)
  realcall pre-registered real-call test clips (realcall/work/d2/scores/realcall_eval.csv, split == test), all four
           detectors scored here by the same rules: the benchmark's own scoring. The pre-registered numbers in
           realcall/FINDINGS.md come from each model's stored scores (training checkpoints at full precision, up to 8
           windows per clip, silence kept); those are under realcall.preregistered_stored_scores for v1 and A.
Never trained on: speaker S02 (held out by protocol), Chatterbox, Seed-VC and Sarvam instant voice cloning
(held-out generators). Every row says which. Output: ml/results/clone_vs_detect.json; per-clip scores in
realcall/work/bench_v2/ (speaker similarity, which no detector touches, is reused from realcall/work/bench/).
"""
import argparse
import gc
import json
import math
import shutil
import sys
import time
import zlib
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ML = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML))
from channel import channels as CH  # noqa: E402
from common.audio import load  # noqa: E402
from common.scoring import MAX_S, SR, aasist_score, clip, nii_chunks, plan_windows, speech_mask  # noqa: E402

W = ML / "realcall" / "work"
SRC, OUT_DIR, FIRST_RUN = W / "src", W / "bench_v2", W / "bench"
OUT = ML / "results" / "clone_vs_detect.json"
CFG = json.load(open(ML / "serve" / "panel_config.json"))
FUSE = ["A", "nii", "v1"]
HELDOUT_GENS = {"chatterbox", "seedvc", "sarvam_ivc"}
HELDOUT_SPK = {"S02"}
CKPT = {"A": ML / "runs/ours_v3_rc/best.pt", "la": ML / "runs/ssl_la/LA_model.pth"}
THREADS = 8


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


def _int8(model):
    return torch.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)


class Served:
    """Ours v1 as the bench runs it: the service's exported weights (serve/model_config.json), CPU int8."""

    def __init__(self):
        from serve.app import CFG_PATH, served_model
        self.model = _int8(served_model(json.load(open(CFG_PATH)), torch.device("cpu")))

    @torch.no_grad()
    def logits(self, segs):
        return self.model(torch.from_numpy(np.stack(segs))).float().numpy()


def detector(m):
    if m == "v1":
        return Served()
    if m == "nii":
        from models.nii_antideepfake import NIIAntiDeepfake
        d = NIIAntiDeepfake(device="cpu")
        d.net = _int8(d.net)
    else:
        from models.detectors import SSLAASIST
        d = SSLAASIST(str(CKPT[m]), device="cpu")
        d.model = _int8(d.model)
    return d


def plan(wavs):
    """The bench's view of each clip: its first MAX_S seconds, and the windows it scores (silent ones dropped)."""
    xs = [clip(x) for x in wavs]
    starts = [plan_windows(len(x), speech_mask(x)) for x in xs]
    torch.set_num_threads(THREADS)   # loading Silero VAD drops torch to one thread
    n = np.array([len(s) for s in starts])
    return xs, starts, {"clips": len(xs), "windows_mean": round(float(n.mean()), 2), "windows_max": int(n.max()),
                        "cut_at_max_s": int(sum(len(x) > len(c) for x, c in zip(wavs, xs)))}


def raw(m, d, x, starts):
    """One clip's score by the bench's rules (serve/panel.py Panel._raw)."""
    if m == "nii":
        return float(np.mean(d.score_batch(nii_chunks(x))))
    return aasist_score(d.logits, x, starts)


def score_all(models, key, xs, starts, ids):
    """Score each clip with each model, caching to realcall/work/bench_v2/{key}__{model}.csv (resumable)."""
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
                s = [raw(m, d, xs[i], starts[i]) for i in idx]
                pd.DataFrame({"id": [ids[i] for i in idx], "score": s}).to_csv(f, mode="a", header=not f.exists(), index=False)
                print(f"  {key}/{m}: {min(b + 16, len(todo))}/{len(todo)} ({time.time() - t0:.0f} s)", flush=True)
            del d
            gc.collect()   # four 300M-parameter models in turn on a 16 GB laptop
        sc = pd.read_csv(f).drop_duplicates("id").set_index("id").score
        sc.index = sc.index.astype(str)
        out[m] = np.array([sc[str(x)] for x in ids], dtype=np.float32)
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


def realcall(models):
    rc = pd.read_csv(W / "d2/scores/realcall_eval.csv")
    rc = rc[rc.split == "test"].reset_index(drop=True)
    rc["generator"] = np.where(rc.label == "bonafide", "genuine", rc.generator)
    print(f"real-call test clips: {len(rc)}", flush=True)
    xs, starts, info = plan([load(W / p) for p in rc.path])
    flags = verdicts(score_all(models, "realcall", xs, starts, list(rc.utt_id)))
    out = {"all": table(rc, flags), "by_device": {dv: table(rc, flags, (rc.device == dv).values) for dv in rc.device.unique()},
           "scoring": "the benchmark's own: every detector re-scored by the bench's rules (common/scoring.py)",
           "plan": info}
    stored = {}
    for m, f in {"v1": "real__ours_v1.csv", "A": "real__ours_v3_rc.csv"}.items():
        s = pd.read_csv(W / "d2/scores" / f).drop_duplicates("utt_id").set_index("utt_id").score
        stored[m] = s.reindex(rc.utt_id).values.astype(np.float32)
    ok = np.all([~np.isnan(v) for v in stored.values()], axis=0)
    rc2 = rc[ok].reset_index(drop=True)
    pre = verdicts({m: v[ok] for m, v in stored.items()})
    out["preregistered_stored_scores"] = {
        "note": "v1 and A from their stored scores, as in realcall/FINDINGS.md (training checkpoints at full precision, "
                "up to 8 windows per clip, silence kept); for comparison with the benchmark's own scoring above",
        "all": table(rc2, pre), "by_device": {dv: table(rc2, pre, (rc2.device == dv).values) for dv in rc2.device.unique()}}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="v1,A,nii,la")
    ap.add_argument("--skip-realcall", action="store_true")
    ap.add_argument("--tables", action="store_true", help="print the FINDINGS.md tables from the JSON and exit")
    a = ap.parse_args()
    if a.tables:
        print(tables(json.loads(OUT.read_text())))
        return
    models = a.models.split(",")
    torch.set_num_threads(THREADS)
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = clips()
    print(f"{len(df)} clips: {df.groupby('generator').size().to_dict()}", flush=True)
    clean = [load(f) for f in df.file]
    amr = [CH.amr(x, np.random.default_rng(zlib.crc32(Path(f).name.encode()))) for x, f in zip(clean, df.file)]
    ids = [Path(f).name for f in df.file]
    sim_file = OUT_DIR / "similarity.csv"
    if not sim_file.exists() and (FIRST_RUN / "similarity.csv").exists():
        shutil.copy(FIRST_RUN / "similarity.csv", sim_file)   # model-free: the window plan doesn't touch it
    if sim_file.exists():
        df["similarity"] = pd.read_csv(sim_file).set_index("id").similarity.reindex(ids).values
    else:
        print("speaker similarity (WavLM x-vectors)...", flush=True)
        df["similarity"] = similarity(df)
        pd.DataFrame({"id": ids, "similarity": df.similarity}).to_csv(sim_file, index=False)
    result = {"method": __doc__.split("\n\n", 1)[1].strip(), "models": {m: CFG["models"][m]["name"] for m in models},
              "fused_members": FUSE, "max_seconds": MAX_S, "sample_rate": SR, "conditions": {}}
    never = (df.speaker.isin(HELDOUT_SPK) | df.generator.isin(HELDOUT_GENS) | (df.kind == "genuine")).values
    for cond, wavs in (("clean", clean), ("amr", amr)):
        print(f"condition {cond}...", flush=True)
        xs, starts, info = plan(wavs)
        flags = verdicts(score_all(models, cond, xs, starts, ids))
        result["conditions"][cond] = {"all_speakers": table(df, flags),
                                      "heldout_speaker_S02": table(df, flags, (df.speaker == "S02").values),
                                      "never_trained_rows": table(df, flags, never), "plan": info}
    gens = {}
    for gen, g in df.groupby("generator"):
        gens[gen] = {"n": int(len(g)), "similarity_mean": round(float(g.similarity.mean()), 4),
                     "similarity_sd": round(float(g.similarity.std()), 4),
                     "heldout": gen in HELDOUT_GENS, "kind": g.kind.iloc[0]}
    result["generators"] = gens
    if not a.skip_realcall:
        result["conditions"]["realcall"] = realcall(models)
    result["run"] = {"started": started, "finished": datetime.now().astimezone().isoformat(timespec="seconds"),
                     "device": "cpu int8", "torch_threads": THREADS, "runs": 1}
    OUT.write_text(json.dumps(result, indent=1))
    print(f"wrote {OUT}", flush=True)


# ------------------------------------------------------------------------------------------- FINDINGS tables
GEN = {"xtts": "XTTS-v2", "f5": "F5-TTS", "f5hi": "F5-TTS Hindi", "cosyvoice2": "CosyVoice2", "chatterbox": "Chatterbox",
       "seedvc": "Seed-VC", "sarvam_ivc": "Sarvam instant cloning", "genuine": "Genuine (flagged)"}
DET = {"v1": "v1", "A": "A", "nii": "NII", "la": "LA (off the shelf)", "fused": "Fused A+NII+v1"}


def wilson(k, n, z=1.96):
    if not n:
        return float("nan"), float("nan")
    p, d = k / n, 1 + z * z / n
    c, h = (p + z * z / (2 * n)) / d, z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def _cell(rate, n):
    k = round(rate * n)
    return f"{k}/{n} = {100 * k / n:.1f} %"


def _pooled(rows, d, gens):
    k = sum(round(rows[g][d] * rows[g]["n"]) for g in gens if d in rows[g])
    n = sum(rows[g]["n"] for g in gens if d in rows[g])
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * k / n:.1f} % ({100 * lo:.0f}–{100 * hi:.0f} %)"


def _table(rows, dets, res, sim=True):
    gens = sorted([g for g in rows if g != "genuine"],
                  key=lambda g: -(res["generators"].get(g, {}).get("similarity_mean") or 0))
    head = ["Cloner", *(["Similarity"] if sim else []), *(DET[d] for d in dets)]
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for g in gens:
        held = " (never trained on)" if g in HELDOUT_GENS else ""
        gi = res["generators"].get(g)
        s = [f"{gi['similarity_mean']:.3f}" if gi else "–"] if sim else []
        out.append(f"| {GEN.get(g, g)}{held} | " + " | ".join(s + [_cell(rows[g][d], rows[g]["n"]) for d in dets]) + " |")
    out.append("| **All clones** (95 % CI) | " + " | ".join((["–"] if sim else []) + [_pooled(rows, d, gens) for d in dets]) + " |")
    if "genuine" in rows:
        gi = res["generators"].get("genuine")
        s = [f"{gi['similarity_mean']:.3f} (ceiling)" if gi else "–"] if sim else []
        out.append("| **Genuine flagged** (95 % CI) | " + " | ".join(s + [_pooled(rows, d, ["genuine"]) for d in dets]) + " |")
    return out


def tables(res):
    """Markdown for FINDINGS.md, generated from the JSON so no number is typed by hand."""
    md = []
    for cond, title in (("clean", "Clean audio"), ("amr", "AMR-NB phone codec (simulated)")):
        c = res["conditions"].get(cond)
        if not c:
            continue
        dets = [d for d in DET if any(d in r for r in c["all_speakers"].values())]
        md += [f"**{title}**, all speakers ({c['plan']['clips']} clips, {c['plan']['windows_mean']} windows per clip "
               f"on average):", ""] + _table(c["all_speakers"], dets, res) + [""]
        md += [f"{title}, held-out speaker S02 only:", ""] + _table(c["heldout_speaker_S02"], dets, res) + [""]
    rc = res["conditions"].get("realcall")
    if rc:
        dets = [d for d in DET if any(d in r for r in rc["all"].values())]
        md += [f"**Real phone calls**, pre-registered test clips, the benchmark's own scoring ({rc['plan']['clips']} clips, "
               f"{rc['plan']['windows_mean']} windows per clip on average):", ""] + _table(rc["all"], dets, res, sim=False) + [""]
        for dv, rows in sorted(rc["by_device"].items()):
            md += [f"Real calls, handset {dv} only:", ""] + _table(rows, dets, res, sim=False) + [""]
        pre = rc["preregistered_stored_scores"]
        pd_ = [d for d in DET if any(d in r for r in pre["all"].values())]
        md += ["Same clips, v1 and A from their **stored scores** (the pre-registered numbers' source; "
               "full precision, up to 8 windows, silence kept):", ""] + _table(pre["all"], pd_, res, sim=False) + [""]
    return "\n".join(md)


if __name__ == "__main__":
    main()
