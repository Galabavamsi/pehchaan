"""Clone-vs-detect benchmark: how convincing each cloner is, and how often each detector catches it.

  python eval/clone_vs_detect.py --service http://127.0.0.1:8510
        through a running voice service started with PEHCHAAN_PANEL=v1,A,nii,la (run from ml/; ~2.5 h on a laptop
        CPU, resumable). One POST /v1/voice/panel per clip: the bench itself, and the models stay loaded once.
  python eval/clone_vs_detect.py                 (no service: loads the four detectors here, one at a time)
  python eval/clone_vs_detect.py --tables [--compare OLD.json]   (markdown tables for FINDINGS.md from the JSON)

How convincing ("speaker similarity"), following ClonEval (arXiv:2504.20581): cosine similarity between WavLM
speaker embeddings (microsoft/wavlm-base-plus-sv, 16 kHz) of a clone and its real speaker. ClonEval compares each
clone with its own reference prompt; we compare with the mean over the speaker's genuine recordings, and report
genuine-vs-genuine similarity of the same speaker as the ceiling a real voice reaches against itself.

How detectable: every panel detector (serve/panel_config.json: ours v1, ours A, NII MMS-300M, off-the-shelf
XLS-R+AASIST LA) and the fused verdict (equal-weight z-mean of A, NII, v1), each at its own threshold (EER point on
the shared simulated test sample). Every clip is scored exactly as on the bench (serve/panel.py), by the rules in
common/scoring.py: the first 60 s of the clip, XLS-R+AASIST models as the mean logit over ~4 s windows with mostly
silent windows dropped (Silero VAD), NII as the mean over chunks of up to 16 s, CPU int8. v1 is the served export
(serve/model_config.json), as on the bench. Through a service, each clip is sent as its WAV file (the AMR condition
as a float32 WAV of the processed waveform, so the service decodes exactly those samples), and each verdict is the
service's own (its raw scores are rounded to 3 decimals; the verdicts use the unrounded scores).
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


def local_flags(models, key, wavs, ids):
    xs, starts, info = plan(wavs)
    return verdicts(score_all(models, key, xs, starts, ids)), info


class PanelService:
    """A running voice service with the full panel: POST /v1/voice/panel is the bench itself."""

    def __init__(self, url, models):
        import requests
        self.http, self.url, self.models = requests.Session(), url.rstrip("/"), models
        h = self.http.get(f"{self.url}/healthz", timeout=30).json()
        panel = h.get("panel") or {}
        if [m for m in models if m not in (panel.get("models") or [])] or set(panel.get("fused") or []) != set(FUSE):
            raise SystemExit(f"{url}: panel {panel}; this run needs models {models} and fused {FUSE}")
        if float(h.get("max_seconds", 0)) != MAX_S:
            raise SystemExit(f"{url} scores the first {h.get('max_seconds')} s of a clip, this script {MAX_S} s")
        self.info = {k: h.get(k) for k in ("model_version", "device", "max_seconds")} | {"url": self.url}

    def score(self, data, name):
        err = None
        for attempt in range(6):   # rides out a service restart (about 5 minutes of retries)
            try:
                r = self.http.post(f"{self.url}/v1/voice/panel", files={"file": (name, data, "audio/wav")}, timeout=600)
                if r.ok:
                    return r.json()
                err = f"HTTP {r.status_code}: {r.text[:200]}"
                if r.status_code < 500:
                    break
            except Exception as e:  # noqa: BLE001 - connection refused while the service restarts
                err = repr(e)[:200]
            time.sleep(15 * (attempt + 1))
        raise RuntimeError(f"voice service failed on {name}: {err}")


def wav_bytes(x):
    """A waveform as a float32 WAV, so the service decodes exactly these samples."""
    import io
    import soundfile as sf
    buf = io.BytesIO()
    sf.write(buf, x, SR, format="WAV", subtype="FLOAT")
    return buf.getvalue()


def panel_flags(svc, key, blob, ids):
    """Each clip scored once through the service; every model's raw score and verdict, the fused verdict and the
    window count are cached per clip in realcall/work/bench_v2/{key}__panel.csv (resumable)."""
    f = OUT_DIR / f"{key}__panel.csv"
    have = set(pd.read_csv(f).id.astype(str)) if f.exists() else set()
    todo = [i for i, x in enumerate(ids) if str(x) not in have]
    t0, rows = time.time(), []
    for j, i in enumerate(todo, 1):
        r = svc.score(blob(i), str(ids[i]))
        by = {m["id"]: m for m in r["models"]}
        row = {"id": ids[i]}
        for m in svc.models:
            row[f"{m}_raw"], row[f"{m}_verdict"] = by[m]["raw"], by[m]["verdict"]
        row.update({"fused_verdict": (r.get("fused") or {}).get("verdict"), "n_windows": r["n_windows"],
                    "seconds_scored": r["seconds_scored"], "audio_seconds": r["audio_seconds"]})
        rows.append(row)
        if len(rows) == 16 or j == len(todo):
            pd.DataFrame(rows).to_csv(f, mode="a", header=not f.exists(), index=False)
            rows = []
            print(f"  {key}: {j}/{len(todo)} ({time.time() - t0:.0f} s)", flush=True)
    c = pd.read_csv(f).drop_duplicates("id")
    c = c.set_index(c.id.astype(str)).loc[[str(x) for x in ids]]
    flags = {m: (c[f"{m}_verdict"] == "synthetic").values for m in svc.models}
    if set(FUSE) <= set(svc.models):
        flags["fused"] = (c["fused_verdict"] == "synthetic").values
    n = c.n_windows.values
    return flags, {"clips": len(c), "windows_mean": round(float(n.mean()), 2), "windows_max": int(n.max()),
                   "cut_at_max_s": int((c.audio_seconds > c.seconds_scored + 0.01).sum())}


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


def realcall(models, svc=None):
    rc = pd.read_csv(W / "d2/scores/realcall_eval.csv")
    rc = rc[rc.split == "test"].reset_index(drop=True)
    rc["generator"] = np.where(rc.label == "bonafide", "genuine", rc.generator)
    print(f"real-call test clips: {len(rc)}", flush=True)
    if svc:
        flags, info = panel_flags(svc, "realcall", lambda i: (W / rc.path[i]).read_bytes(), list(rc.utt_id))
    else:
        flags, info = local_flags(models, "realcall", [load(W / p) for p in rc.path], list(rc.utt_id))
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
    ap.add_argument("--service", help="voice service URL with the full panel, e.g. http://127.0.0.1:8510")
    ap.add_argument("--tables", action="store_true", help="print the FINDINGS.md tables from the JSON and exit")
    ap.add_argument("--compare", help="with --tables: an earlier run's JSON, for a side-by-side table")
    a = ap.parse_args()
    if a.tables:
        print(tables(json.loads(OUT.read_text()), json.loads(Path(a.compare).read_text()) if a.compare else None))
        return
    models = a.models.split(",")
    svc = PanelService(a.service, models) if a.service else None
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
    blobs = {"clean": lambda i: Path(df.file[i]).read_bytes(), "amr": lambda i: wav_bytes(amr[i])}
    for cond, wavs in (("clean", clean), ("amr", amr)):
        print(f"condition {cond}...", flush=True)
        flags, info = panel_flags(svc, cond, blobs[cond], ids) if svc else local_flags(models, cond, wavs, ids)
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
        result["conditions"]["realcall"] = realcall(models, svc)
    result["run"] = {"started": started, "finished": datetime.now().astimezone().isoformat(timespec="seconds"),
                     "device": "cpu int8", "runs": 1,
                     **({"voice_service": svc.info} if svc else {"torch_threads": THREADS})}
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


def _pooled(rows, d, gens, ci=True):
    """k/n over the given generators, with a 95 % Wilson interval rounded outwards."""
    k = sum(round(rows[g][d] * rows[g]["n"]) for g in gens if g in rows and d in rows[g])
    n = sum(rows[g]["n"] for g in gens if g in rows and d in rows[g])
    if not n:
        return "–"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * k / n:.1f} %" + (f" ({math.floor(100 * lo)}–{math.ceil(100 * hi)} %)" if ci else "")


def _comparison(new, old):
    head = ["Condition", "Detector", "Genuine flagged, first run", "Genuine flagged, bench scoring",
            "Clones caught, first run", "Clones caught, bench scoring"]
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for cond, key, title in (("clean", "all_speakers", "Clean"), ("amr", "all_speakers", "AMR-NB"),
                             ("realcall", "all", "Real calls")):
        o, n = (old["conditions"].get(cond) or {}).get(key), (new["conditions"].get(cond) or {}).get(key)
        if not (o and n):
            continue
        for d in DET:
            if any(d in r for r in n.values()):
                cells = [_pooled(r, d, g, ci=False) for r, g in ((o, ["genuine"]), (n, ["genuine"]),
                                                                 (o, [x for x in o if x != "genuine"]),
                                                                 (n, [x for x in n if x != "genuine"]))]
                out.append(f"| {title} | {DET[d]} | " + " | ".join(cells) + " |")
    return out


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


def tables(res, old=None):
    """Markdown for FINDINGS.md, generated from the JSON (and an earlier run's, for the side-by-side table) so no
    number is typed by hand."""
    md = []
    if old:
        md += ["**First run vs the bench's scoring** (same clips and thresholds; the first run scored at most 8 windows "
               "per clip with silence kept, NII on each clip's first 16 s only and v1 from its training checkpoint, and "
               "took real-call v1 and A from their stored scores):", ""] + _comparison(res, old) + [""]
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
        for dv, rows in sorted(pre["by_device"].items()):
            md += [f"Stored scores, handset {dv} only:", ""] + _table(rows, pd_, res, sim=False) + [""]
    return "\n".join(md)


if __name__ == "__main__":
    main()
