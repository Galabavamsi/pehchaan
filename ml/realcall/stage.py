"""Stage real-call training data for the GPU box: a self-contained folder, then S3.

  python -m realcall.stage                 # build work/stage/realcall/ (manifest with relative paths, segments, channel)
  python -m realcall.stage --upload        # ... and sync it to s3://<bucket>/work/realcall/

Only QC-ok segments of consented speakers go up; no phone numbers (the manifest never had them), no tapes,
no raw captures. The bucket is private and its lifecycle deletes everything on 2026-12-31 (consent promise).
On the box: aws s3 sync s3://<bucket>/work/realcall ~/work/realcall, then
  python train/finetune.py ... --aug_set v3 --realcall_manifest ~/work/realcall/realcall.csv
with REALCALL_WORK=~/work/realcall so learned_channel.npz is found.
"""
import argparse
import os
import shutil
import subprocess

import pandas as pd

from realcall.consent import Registry
from realcall.settings import MANIFESTS, SEGMENTS, WORK

BUCKET = "s3://pehchaan-ml-301745146083-use1/work/realcall"
STAGE = WORK / "stage" / "realcall"


def build():
    reg = Registry()
    m = pd.read_csv(MANIFESTS / "realcall.csv")
    m = m[(m.qc == "ok") & m.path.notna()].copy()
    m = m[m.speaker.astype(str).map(lambda s: _consented(reg, s))]
    if STAGE.exists():
        shutil.rmtree(STAGE)
    (STAGE / "segments").mkdir(parents=True)
    rel = []
    for p in m.path:
        r = os.path.relpath(p, SEGMENTS).replace("\\", "/")
        dst = STAGE / "segments" / r
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dst)
        rel.append("segments/" + r)
    m["path"] = rel
    drop = [c for c in ("device_hash",) if c in m]
    m.drop(columns=drop).to_csv(STAGE / "realcall.csv", index=False)
    shutil.copy2(WORK / "learned_channel.npz", STAGE / "learned_channel.npz")
    size = sum(f.stat().st_size for f in STAGE.rglob("*") if f.is_file()) / 1e6
    print(f"staged {len(m)} segments from {m.call_id.nunique()} calls ({size:.0f} MB) -> {STAGE}")
    print(m.groupby(["split", "label"]).size().to_string())
    return STAGE


def _consented(reg, spk):
    try:
        reg.require_record(spk)
        return True
    except PermissionError:
        return False


def upload():
    cmd = ["aws", "s3", "sync", str(STAGE), BUCKET, "--delete", "--only-show-errors", "--region", "us-east-1"]
    subprocess.run(cmd, check=True)
    out = subprocess.run(["aws", "s3", "ls", BUCKET + "/", "--region", "us-east-1"], capture_output=True, text=True).stdout
    print("uploaded ->", BUCKET, "\n" + out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upload", action="store_true")
    a = ap.parse_args()
    build()
    if a.upload:
        upload()


if __name__ == "__main__":
    main()
