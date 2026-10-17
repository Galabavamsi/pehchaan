"""Build call tapes: a sync chirp, then genuine team lines and their clones (shuffled, content-matched), then a chirp.

  python -m realcall.tape --n 5                 # five new tapes from whatever sources exist
  python -m realcall.tape --list-sources        # what can go on a tape, per speaker and generator

Sources (see README setup):
  work/src/genuine/<SPK>/team_<SPK>_<LINE>.wav
  work/src/clone/<GEN>/<GEN>__<SPK>__<LINE>[...].wav
Only speakers whose consent covers cloning are used, for genuine and clone items alike, so a tape never
carries anyone's voice without consent.
"""
import argparse
import json
import random
import time
import uuid
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from common.audio import load, normalize_rms, resample, save
from realcall.consent import Registry
from realcall.dsp import SR, sync_chirp, trim
from realcall.settings import SRC, TAPES, ensure_dirs

GAP_S = 1.2
LEAD_S = 1.5
TAIL_S = 1.5
ITEM_S, ITEM_MIN_S, ITEM_MAX_S = 8.0, 7.0, 12.5   # target / minimum / maximum item length
JOIN_S = 0.3                                     # pause between lines inside one item


def _texts():
    p = SRC / "team_bona.csv"
    if not p.exists():
        return {}
    m = pd.read_csv(p)
    out = {}
    for r in m.itertuples(index=False):
        key = (str(getattr(r, "speaker", "")), str(getattr(r, "line_id", "")))
        out[key] = (str(getattr(r, "lang", "")), str(getattr(r, "text", "")))
    return out


def index_sources(reg: Registry):
    """{(speaker, line_id): {"genuine": [paths], "clone": [(gen, path)]}} for consented speakers only."""
    idx = defaultdict(lambda: {"genuine": [], "clone": []})
    for p in sorted((SRC / "genuine").glob("*/*.wav")):
        spk = p.parent.name
        line = p.stem.split(f"team_{spk}_", 1)[-1]
        if reg.can_clone(spk):
            idx[(spk, line)]["genuine"].append(p)
    for p in sorted((SRC / "clone").glob("*/*.wav")):
        parts = p.stem.split("__")
        if len(parts) < 3:
            continue
        gen, spk, line = parts[0], parts[1], parts[2]
        if reg.can_clone(spk):
            idx[(spk, line)]["clone"].append((gen, p))
    return idx


def build(reg: Registry, n_pairs: int = 5, seed: int | None = None, speakers=None, generators=None):
    """One tape with up to n_pairs genuine and n_pairs clone items (~10 s each). Returns its json dict."""
    ensure_dirs()
    seed = seed if seed is not None else random.randrange(1 << 30)
    rng = random.Random(seed)
    idx = index_sources(reg)
    texts = _texts()
    # Group lines by (speaker, generator): a pair is one ~10 s genuine item and one ~10 s clone item made of
    # the SAME lines in the same order, so the two differ only in being synthetic. 10 s matches the product's
    # 8-12 s capture and clears the service's 4 s-of-speech quality gate after a real phone line.
    groups = defaultdict(list)
    for (spk, line), v in idx.items():
        if not v["genuine"] or (speakers and spk not in speakers):
            continue
        for gen in sorted({g for g, _ in v["clone"] if not generators or g in generators}):
            groups[(spk, gen)].append(line)
    if not groups:
        raise SystemExit("no (speaker, line) has both a genuine and a clone source: run the S3 sync in README")
    for k in groups:
        rng.shuffle(groups[k])
    clip = {}

    def seg(path):
        if path not in clip:
            clip[path] = normalize_rms(trim(load(path)), -24)
        return clip[path]

    picks, keys, used_lines = [], list(groups), defaultdict(set)
    spk_cycle = sorted({k[0] for k in keys})
    rng.shuffle(spk_cycle)
    turn = 0
    while len(picks) < 2 * n_pairs and keys:
        live = [sp for sp in spk_cycle if any(k[0] == sp for k in keys)]
        sp = live[turn % len(live)]                       # alternate speakers so every tape has both
        turn += 1
        k = rng.choice([k for k in keys if k[0] == sp])
        spk, gen = k
        groups[k].sort(key=lambda l: l not in used_lines[spk])   # fresh lines at the end, popped first
        lines, gx, cx, used = [], [], [], 0.0
        while groups[k] and used < ITEM_S:
            line = groups[k].pop()
            used_lines[spk].add(line)
            v = idx[(spk, line)]
            g = seg(str(rng.choice(v["genuine"])))
            c = seg(str(rng.choice([p for gg, p in v["clone"] if gg == gen])))
            lines.append(line)
            gx += [g, np.zeros(int(JOIN_S * SR), np.float32)]
            cx += [c, np.zeros(int(JOIN_S * SR), np.float32)]
            used += len(g) / SR + JOIN_S
            if used > ITEM_MAX_S:
                break
        if not groups[k]:
            keys.remove(k)
        if used < ITEM_MIN_S:
            continue
        txt = [texts.get((spk, l), ("", "")) for l in lines]
        meta_common = dict(speaker=spk, line_id="+".join(lines), lang=txt[0][0], text=" | ".join(t for _, t in txt))
        picks.append(dict(label="bonafide", generator="bonafide", audio=np.concatenate(gx[:-1]), **meta_common))
        picks.append(dict(label="spoof", generator=gen, audio=np.concatenate(cx[:-1]), **meta_common))
    rng.shuffle(picks)

    tape_id = time.strftime("T%m%d") + "-" + uuid.uuid4().hex[:6]
    ch = sync_chirp(SR)
    parts, items = [np.zeros(int(LEAD_S * SR), np.float32), ch, np.zeros(int(1.0 * SR), np.float32)], []
    t = LEAD_S + len(ch) / SR + 1.0
    chirp_start = LEAD_S
    for i, it in enumerate(picks):
        x = it.pop("audio")
        items.append({**it, "idx": i, "utt_id": f"{tape_id}_{i:02d}", "start_s": round(t, 4), "dur_s": round(len(x) / SR, 4)})
        parts += [x, np.zeros(int(GAP_S * SR), np.float32)]
        t += len(x) / SR + GAP_S
    chirp_end = t
    parts += [ch, np.zeros(int(TAIL_S * SR), np.float32)]
    ref = np.concatenate(parts)

    save(TAPES / f"{tape_id}.ref.wav", ref, SR)                        # 16 kHz reference for alignment
    save(TAPES / f"{tape_id}.wav", resample(ref, SR, 8000), 8000)     # what Vobiz plays (8 kHz mono, per its docs)
    meta = {"tape_id": tape_id, "seed": seed, "sr_ref": SR, "chirp_s": [chirp_start, chirp_end],
            "total_s": round(len(ref) / SR, 3), "items": items, "created": time.time()}
    (TAPES / f"{tape_id}.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    return meta


def load_tape(tape_id: str) -> dict:
    return json.loads((TAPES / f"{tape_id}.json").read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--pairs", type=int, default=5)
    ap.add_argument("--speakers", nargs="*")
    ap.add_argument("--generators", nargs="*")
    ap.add_argument("--list-sources", action="store_true")
    a = ap.parse_args()
    reg = Registry()
    if a.list_sources:
        idx = index_sources(reg)
        g = defaultdict(int)
        for (spk, _), v in idx.items():
            g[(spk, "genuine")] += len(v["genuine"])
            for gen, _ in v["clone"]:
                g[(spk, gen)] += 1
        for k in sorted(g):
            print(f"{k[0]:5s} {k[1]:12s} {g[k]}")
        return
    for _ in range(a.n):
        m = build(reg, a.pairs, speakers=a.speakers, generators=a.generators)
        print(m["tape_id"], f"{len(m['items'])} items, {m['total_s']:.0f} s")


if __name__ == "__main__":
    main()
