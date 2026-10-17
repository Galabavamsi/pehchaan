"""Score the real-call manifest with the served detector and decide the shadow-mode gate.

  python -m serve.app  (or uvicorn serve.app:app --port 8500)   # the model under test, in another terminal
  python -m realcall.gate --url http://127.0.0.1:8500 [--split test]

Writes work/reports/gate_<model_version>.json and .md. Scores are cached per model version and file.
"""
import argparse
import json
import math
from collections import defaultdict

import numpy as np
import pandas as pd
import requests

from realcall import protocol
from realcall.settings import MANIFESTS, REPORTS, ensure_dirs


def wilson_upper(k: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 1.0
    p = k / n
    d = 1 + z * z / n
    return min(1.0, (p + z * z / (2 * n) + z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d)


def eer(bona: np.ndarray, spoof: np.ndarray) -> float:
    if not len(bona) or not len(spoof):
        return float("nan")
    ts = np.unique(np.concatenate([bona, spoof]))
    best = (2.0, 0.0)
    for t in ts:
        frr = np.mean(spoof < t)       # spoof missed
        far = np.mean(bona >= t)       # genuine flagged
        if abs(frr - far) < best[0]:
            best = (abs(frr - far), (frr + far) / 2)
    return float(best[1])


def score_all(df: pd.DataFrame, url: str) -> pd.DataFrame:
    hz = requests.get(url.rstrip("/") + "/healthz", timeout=10).json()
    ver = hz.get("model_version", "unknown")
    cache_p = REPORTS / f"scores_{ver.replace('/', '_').replace('+', '_')}.csv"
    cache = pd.read_csv(cache_p).set_index("path").to_dict("index") if cache_p.exists() else {}
    out = []
    todo = df[~df.path.isin(cache)]
    for i, r in enumerate(todo.itertuples(index=False)):
        with open(r.path, "rb") as f:
            j = requests.post(url.rstrip("/") + "/v1/voice/score", files={"file": ("a.wav", f, "audio/wav")}, timeout=60).json()
        cache[r.path] = {"p_synthetic": j["p_synthetic"], "band": j["band"], "quality_ok": j.get("quality", {}).get("ok")}
        if i % 50 == 0:
            print(f"  scored {i + 1}/{len(todo)}")
    pd.DataFrame([{"path": k, **v} for k, v in cache.items()]).to_csv(cache_p, index=False)
    for r in df.itertuples(index=False):
        out.append(cache[r.path])
    return pd.concat([df.reset_index(drop=True), pd.DataFrame(out)], axis=1), ver


def band_lrs(bona, spoof):
    res = {}
    for b in ("likely_synthetic", "inconclusive", "no_strong_evidence"):
        ps, pb = np.mean(spoof == b) if len(spoof) else np.nan, np.mean(bona == b) if len(bona) else np.nan
        res[b] = round(float(ps / pb), 3) if pb and pb > 0 else None
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8500")
    ap.add_argument("--split", default="test")
    a = ap.parse_args()
    ensure_dirs()
    df = pd.read_csv(MANIFESTS / "realcall.csv")
    df = df[(df.qc == "ok") & (df.split == a.split) & df.path.notna()]
    if df.empty:
        raise SystemExit(f"no qc-ok rows in split {a.split}")
    df, ver = score_all(df, a.url)
    flag = df.band == "likely_synthetic"

    live = df[df.kind == "live"]
    gw = live[live.gate_window.astype(str) == "True"]
    k, n = int((gw.band == "likely_synthetic").sum()), len(gw)
    by_spk = {s: {"calls": int(len(g)), "flagged": int((g.band == "likely_synthetic").sum())} for s, g in gw.groupby("speaker")}
    by_route = {s: {"calls": int(len(g)), "flagged": int((g.band == "likely_synthetic").sum())} for s, g in gw.groupby("route")}
    chunks = live[live.gate_window.astype(str) != "True"]

    tape = df[df.kind == "tape"]
    tb, ts = tape[tape.label == "bonafide"], tape[tape.label == "spoof"]
    real_bona = pd.concat([chunks, tb])
    per_gen = {g: {"n": int(len(x)), "detected": round(float((x.band == "likely_synthetic").mean()), 3)} for g, x in ts.groupby("generator")}
    per_cap = defaultdict(dict)
    for (cap, lab), x in tape.groupby(["capture", "label"]):
        per_cap[cap][lab] = {"n": int(len(x)), "likely_synthetic": round(float((x.band == "likely_synthetic").mean()), 3)}

    rep = {
        "model_version": ver, "split": a.split,
        "gate": {"live_calls": n, "flagged": k, "rate": round(k / n, 4) if n else None,
                 "wilson95_upper": round(wilson_upper(k, n), 4),
                 "inconclusive_share": round(float((gw.band == "inconclusive").mean()), 4) if n else None,
                 "min_calls": protocol.GATE_MIN_LIVE_CALLS, "max_rate": protocol.GATE_MAX_FLAG_RATE,
                 "pass": bool(n >= protocol.GATE_MIN_LIVE_CALLS and k / max(n, 1) <= protocol.GATE_MAX_FLAG_RATE),
                 "by_speaker": by_spk, "by_route": by_route},
        "live_chunks": {"n": int(len(chunks)), "flag_rate": round(float((chunks.band == "likely_synthetic").mean()), 4) if len(chunks) else None},
        "tape": {"n_bona": int(len(tb)), "n_spoof": int(len(ts)),
                 "bona_flag_rate": round(float((tb.band == "likely_synthetic").mean()), 4) if len(tb) else None,
                 "spoof_detect_rate": round(float((ts.band == "likely_synthetic").mean()), 4) if len(ts) else None,
                 "eer": round(eer(tb.p_synthetic.values, ts.p_synthetic.values), 4),
                 "per_generator": per_gen, "per_capture": per_cap},
        "real_call_band_LRs": band_lrs(real_bona.band.values, ts.band.values),
        "real_call_eer_all_bona": round(eer(real_bona.p_synthetic.values, ts.p_synthetic.values), 4),
    }
    tag = ver.replace("/", "_").replace("+", "_")
    (REPORTS / f"gate_{tag}.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    g = rep["gate"]
    md = [f"# Real-call gate: {ver} ({a.split})", "",
          f"**{'PASS' if g['pass'] else 'FAIL'}**: {g['flagged']}/{g['live_calls']} live genuine calls flagged "
          f"({(g['rate'] or 0) * 100:.1f} %, Wilson 95 % upper {g['wilson95_upper'] * 100:.1f} %). "
          f"Gate: >= {g['min_calls']} calls and <= {g['max_rate'] * 100:.0f} %.", "",
          f"- Live chunks flagged: {rep['live_chunks']['flag_rate']} of {rep['live_chunks']['n']}",
          f"- Tapes: genuine flagged {rep['tape']['bona_flag_rate']}, clones caught {rep['tape']['spoof_detect_rate']}, EER {rep['tape']['eer']}",
          f"- Real-call band LRs: {rep['real_call_band_LRs']}",
          f"- Per generator: {json.dumps(per_gen)}",
          f"- By speaker: {json.dumps(by_spk)}", f"- By route: {json.dumps(by_route)}"]
    (REPORTS / f"gate_{tag}.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
