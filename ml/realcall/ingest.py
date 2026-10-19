"""Turn finished calls into labelled 16 kHz segments and one manifest.

  python -m realcall.ingest              # rebuilds work/manifests/realcall.csv from the ledger and captures

Tape calls: find the start and end chirps in each capture of the call (laptop mic session, WhatsApp-tape
capture, dialer recordings copied to work/device_uploads/<device>/), correct clock drift between them, then
place every tape item by local cross-correlation. Items with no speech where the item should be (dropped
by the network or its noise suppression) are kept in the manifest as qc=fail, so drop rates are reportable.
Live calls: energy VAD into 4-10 s chunks, plus one 10 s "gate window" per call (what the product would score).
Uplink calls: the conductor's prompt windows, VAD-trimmed.
"""
import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf

from common.audio import load, load_any, save
from realcall import protocol
from realcall.dsp import SR, align_item, chunk_regions, find_chirps, frame_db, quality, vad_regions
from realcall.settings import CAPTURE, MANIFESTS, SEGMENTS, TAPES, UPLOADS, calls, ensure_dirs
from realcall.tape import load_tape

AUDIO_EXT = {".wav", ".m4a", ".mp3", ".amr", ".3gp", ".aac", ".ogg", ".opus", ".flac"}


def _sessions():
    out = []
    for js in sorted(CAPTURE.glob("session_*.json")):
        w = js.with_suffix(".wav")
        if not w.exists():
            continue
        m = json.loads(js.read_text(encoding="utf-8"))
        try:
            n = sf.info(str(w)).frames
        except Exception:
            continue
        out.append({**m, "path": w, "end_epoch": m["start_epoch"] + n / SR})
    return out


def _session_window(sessions, device, t0, t1):
    """Audio from the device's laptop-mic sessions between wall-clock t0 and t1 (may span a file roll)."""
    parts = []
    for s in sessions:
        if s.get("device") != device or s["end_epoch"] < t0 or s["start_epoch"] > t1:
            continue
        a = max(0, int((t0 - s["start_epoch"]) * SR))
        b = int((t1 - s["start_epoch"]) * SR)
        x, _ = sf.read(str(s["path"]), start=a, stop=b, dtype="float32", always_2d=True)
        parts.append(x[:, 0])
    return np.concatenate(parts) if parts else None


def _name_time(p: Path):
    """Call start time from a dialer recording's file name (local time), or None.
    Handles 20261017_201530 / 2026-10-17 20-15-30 and Samsung's yymmdd_HHMMSS (..._261017_201530.m4a)."""
    for pat, yy in ((r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})[-_ T]?(\d{2})[-_.:]?(\d{2})[-_.:]?(\d{2})", False),
                    (r"(?<!\d)(\d{2})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})(?!\d)", True)):
        m = re.search(pat, p.name)
        if m:
            g = list(map(int, m.groups()))
            if yy:
                g[0] += 2000
            try:
                return datetime(*g).timestamp()
            except ValueError:
                pass
    return None


def _uploads(device, t_answer, t_hangup, tol_s: float = 90.0):
    """The single dialer recording for this call: its name time closest to the answer time (or, if the name
    has no time, its modified time closest to the hangup), within tol_s. Never a neighbouring call's file."""
    d = UPLOADS / device
    if not d.exists():
        return []
    best = None
    for p in d.iterdir():
        if p.suffix.lower() not in AUDIO_EXT:
            continue
        nt = _name_time(p)
        err = abs(nt - t_answer) if nt is not None else abs(p.stat().st_mtime - t_hangup)
        if err <= tol_s and (best is None or err < best[0]):
            best = (err, p)
    return [best[1]] if best else []


def _pick_chirps(hits, expected_gap, cap_s=None):
    """(start_s, drift) from chirp hits: the pair whose spacing best matches the tape, else the strongest hit."""
    best = None
    for i in range(len(hits)):
        for j in range(i + 1, len(hits)):
            gap = hits[j][0] - hits[i][0]
            if abs(gap / expected_gap - 1) < 0.03:
                s = hits[i][1] + hits[j][1]
                if not best or s > best[0]:
                    best = (s, hits[i][0], gap / expected_gap)
    if best:
        return best[1], best[2], "two_chirps"
    if hits:
        # One chirp: the start one, or the end one if the start was missed (e.g. played before speaker came on).
        h = max(hits, key=lambda h: h[1])[0]
        if h >= 0.9 * expected_gap and (cap_s is None or h + 0.5 * expected_gap > cap_s):
            return h - expected_gap, 1.0, "end_chirp_only"
        return h, 1.0, "start_chirp_only"
    return None, None, "no_chirp"


def _row_base(c, kind, capture):
    return dict(source="realcall", kind=kind, call_id=c["call_id"], capture=capture, device=c.get("device"),
                carrier=c.get("carrier"), network=c.get("network"), model=c.get("model"), route=c.get("route", "cellular"),
                caller=c.get("caller", ""), call_t=c.get("answered_t") or c.get("registered_t"),
                native_channel=f"realcall_{kind}_{c.get('route', 'cellular')}_{capture}")


def ingest_tape(c, sessions):
    meta = load_tape(c["tape_id"])
    ref = load(TAPES / f"{c['tape_id']}.ref.wav")
    t0 = (c.get("answered_t") or c["registered_t"]) - 5
    t1 = (c.get("hangup_t") or t0 + meta["total_s"] + 60) + 5
    caps = []
    if c.get("capture_file"):
        caps.append(("laptop_mic", load(c["capture_file"])))
    else:
        x = _session_window(sessions, c.get("device"), t0, t1)
        if x is not None:
            caps.append(("laptop_mic", x))
    for p in _uploads(c.get("device", ""), t0 + 5, t1 - 5):
        try:
            caps.append(("dialer_rec", load_any(p)))
        except subprocess.CalledProcessError:
            pass
    rows = []
    if str(c.get("duration_s") or "") in ("0", "0.0") or c.get("hangup_cause") in ("USER_BUSY", "NO_ANSWER", "CALL_REJECTED"):
        return [{**_row_base(c, "tape", "none"), "utt_id": f"rc_{c['call_id'][:8]}_unanswered", "qc": "not_answered"}]
    gap = meta["chirp_s"][1] - meta["chirp_s"][0]
    for cap, x in caps:
        c0, drift, how = _pick_chirps(find_chirps(x), gap, len(x) / SR)
        if c0 is None:
            rows.append({**_row_base(c, "tape", cap), "utt_id": f"rc_{c['call_id'][:8]}_{cap}_nochirp", "qc": "fail_no_chirp"})
            continue
        # noise floor from the silent gaps between tape items (where only the room and the line are heard)
        gaps = []
        for it in meta["items"]:
            g0 = c0 + (it["start_s"] + it["dur_s"] - meta["chirp_s"][0]) * drift + 0.25
            gaps.append(x[int(g0 * SR): int((g0 + 0.6) * SR)])
        gaps = [g for g in gaps if len(g)]
        gx = np.concatenate(gaps) if gaps else x
        floor_db = float(np.median(frame_db(gx))) if len(gx) else None
        for it in meta["items"]:
            exp = c0 + (it["start_s"] - meta["chirp_s"][0]) * drift
            seg_ref = ref[int(it["start_s"] * SR): int((it["start_s"] + it["dur_s"]) * SR)]
            pos, ncc = align_item(x, seg_ref, exp)
            if ncc < 0.5:            # weak match: trust the chirp-anchored, drift-corrected position
                pos = exp
            a, b = int(pos * SR), int((pos + it["dur_s"] * drift) * SR)
            y = x[max(0, a): max(0, b)]
            q = quality(y, floor_db=floor_db) if len(y) > SR // 4 else {"speech_s": 0, "snr_db": 0, "dur_s": 0, "clip_frac": 0, "rms_db": -120}
            ok = len(y) > 0.8 * it["dur_s"] * SR and q["speech_s"] >= 0.4 * it["dur_s"] and q["snr_db"] >= 8
            uid = f"rc_{c['call_id'][:8]}_{cap}_{it['idx']:02d}"
            path = SEGMENTS / c["call_id"] / cap / f"{it['idx']:02d}_{it['label']}.wav"
            if len(y):
                path.parent.mkdir(parents=True, exist_ok=True)
                save(path, y, SR)
            split = protocol.split_for("tape", c["call_id"], c.get("device", ""), it["speaker"], it["generator"])
            rows.append({**_row_base(c, "tape", cap), "utt_id": uid, "path": str(path), "label": it["label"],
                         "generator": it["generator"], "speaker": it["speaker"], "lang": it.get("lang", ""),
                         "line_id": it["line_id"], "text": it.get("text", ""), "split": split,
                         "heldout": protocol.heldout(it["speaker"], it["generator"]), "tape_utt": it["utt_id"],
                         "align": how, "drift": round(drift, 5), "floor_db": round(floor_db or 0, 1), "ncc": round(ncc, 3), "pos_s": round(pos, 3), "exp_s": round(exp, 3), **q, "qc": "ok" if ok else "fail"})
    return rows


def ingest_live(c):
    x = load(c["file"])
    regs = vad_regions(x)
    split = protocol.split_for("live", c["call_id"], c.get("device", ""), c.get("speaker", ""), "bonafide", c.get("caller", ""))
    base = {**_row_base(c, "live", c.get("capture", "laptop_mic")), "label": "bonafide", "generator": "bonafide",
            "speaker": c.get("speaker"), "lang": c.get("lang", ""), "line_id": "", "text": "", "split": split,
            "heldout": protocol.heldout(c.get("speaker", ""), "bonafide")}
    rows = []
    for i, (a, b) in enumerate(chunk_regions(regs, protocol.CHUNK_MIN_S, protocol.CHUNK_MAX_S)):
        y = x[int(a * SR): int(b * SR)]
        path = SEGMENTS / c["call_id"] / "live" / f"{i:02d}.wav"
        path.parent.mkdir(parents=True, exist_ok=True)
        save(path, y, SR)
        q = quality(y)
        rows.append({**base, "utt_id": f"rc_{c['call_id'][:8]}_live_{i:02d}", "path": str(path), **q,
                     "qc": "ok" if q["snr_db"] >= 8 else "fail", "gate_window": False})
    if regs:   # the gate window: the first GATE_WINDOW_S of the call starting at the first speech
        a = regs[0][0]
        y = x[int(a * SR): int((a + protocol.GATE_WINDOW_S) * SR)]
        path = SEGMENTS / c["call_id"] / "live" / "gate.wav"
        path.parent.mkdir(parents=True, exist_ok=True)
        save(path, y, SR)
        q = quality(y)
        rows.append({**base, "utt_id": f"rc_{c['call_id'][:8]}_gate", "path": str(path), **q,
                     "qc": "ok" if q["speech_s"] >= 4 and q["snr_db"] >= 8 else "fail", "gate_window": True})
    return rows


def ingest_uplink(c):
    x = load(c["uplink_wav"])
    rows = []
    for w in c.get("windows", []):
        y = x[w["start_sample"]: w["end_sample"]]
        regs = vad_regions(y)
        if regs:
            y = y[max(0, int((regs[0][0] - 0.15) * SR)): int((regs[-1][1] + 0.15) * SR)]
        q = quality(y) if len(y) > SR // 4 else {"speech_s": 0, "snr_db": 0, "dur_s": 0, "clip_frac": 0, "rms_db": -120}
        lab = "bonafide" if w["type"] == "read" else "spoof"
        gen = "bonafide" if lab == "bonafide" else w.get("generator", "")
        path = SEGMENTS / c["call_id"] / "uplink" / f"{w['step']:02d}_{lab}.wav"
        path.parent.mkdir(parents=True, exist_ok=True)
        if len(y):
            save(path, y, SR)
        cap = "vobiz_stream" if lab == "bonafide" else "vobiz_stream_replay"
        rows.append({**_row_base(c, "uplink", cap), "utt_id": f"rc_{c['call_id'][:8]}_up_{w['step']:02d}", "path": str(path),
                     "label": lab, "generator": gen, "speaker": w.get("speaker"), "lang": w.get("lang", ""),
                     "line_id": w.get("line_id"), "text": w.get("text", ""),
                     "split": protocol.split_for("uplink", c["call_id"], c.get("device", ""), w.get("speaker", ""), gen),
                     "heldout": protocol.heldout(w.get("speaker", ""), gen), **q,
                     "qc": "ok" if q["speech_s"] >= 1.0 and q["snr_db"] >= 8 else "fail"})
    return rows


def main():
    ensure_dirs()
    sessions = _sessions()
    rows, skipped = [], []
    for c in calls().values():
        try:
            if c.get("kind") == "tape" and ("hangup_t" in c or "capture_file" in c):
                rows += ingest_tape(c, sessions)
            elif c.get("kind") == "live" and c.get("file"):
                rows += ingest_live(c)
            elif c.get("kind") == "uplink" and c.get("uplink_wav"):
                rows += ingest_uplink(c)
            else:
                skipped.append(c["call_id"][:8])
        except Exception as e:  # one broken call must not stop the rest
            print(f"! {c['call_id'][:8]} ({c.get('kind')}): {e!r}"[:200])
    df = pd.DataFrame(rows)
    out = MANIFESTS / "realcall.csv"
    df.to_csv(out, index=False)
    print(f"{len(df)} rows -> {out}" + (f"; {len(skipped)} calls not finished/ingestable" if skipped else ""))
    if len(df):
        print(df.groupby(["kind", "split", "label", "qc"], dropna=False).size().to_string())
    return df


if __name__ == "__main__":
    main()
