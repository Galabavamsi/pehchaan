"""Laptop side of the 2026-10-24 paid-API retrain: 16 kHz FLAC copies of the generated clips -> private S3 bucket.
  python ml/infra/upload_api2.py            # then on the GPU box: infra/retrain_v4.sh syncs them to ~/work/api2_src

Stock-voice clips (no person's voice) are staged in data/generated/api2_flac/; the Sarvam clones of S01 are team
audio, so they are staged under ml/realcall/work/ like every other team-voice file (CLAUDE.md), and only go to the
team's private bucket (consent form, point 6). The box resamples and normalises again, so FLAC at 16 kHz loses nothing.
"""
import csv
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import soundfile as sf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml"))
from common.audio import load_any  # noqa: E402

BUCKET = "s3://pehchaan-ml-301745146083-use1/work/api2_src"
GEN = ROOT / "data/generated/api2"
STAGE = ROOT / "data/generated/api2_flac"
IVC_SRC = ROOT / "ml/realcall/work/src/clone/sarvam_ivct"
IVC_STAGE = ROOT / "ml/realcall/work/upload/sarvam_ivct"


def flac(src: Path, dst: Path) -> bool:
    if dst.exists() and dst.stat().st_size > 1000:
        return True
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        sf.write(dst, load_any(str(src)), 16000, format="FLAC")
        return True
    except Exception as ex:  # noqa: BLE001
        print("skip", src.name, type(ex).__name__)
        return False


def main():
    rows = list(csv.DictReader(open(GEN / "manifest.csv", encoding="utf-8")))
    jobs = [(Path(r["out"]), STAGE / r["engine"] / f"{r['id']}.flac") for r in rows if Path(r["out"]).exists()]
    jobs += [(p, IVC_STAGE / f"{p.stem}.flac") for p in sorted(IVC_SRC.glob("*.wav"))]
    with ThreadPoolExecutor(8) as ex:
        ok = sum(ex.map(lambda j: flac(*j), jobs))
    print(f"{ok}/{len(jobs)} clips as 16 kHz FLAC ({len(rows)} jobs in the manifest)")
    (STAGE / "manifest.csv").write_bytes((GEN / "manifest.csv").read_bytes())
    for src, dst in ((STAGE, BUCKET), (IVC_STAGE, f"{BUCKET}/sarvam_ivct")):
        subprocess.run(["aws", "s3", "sync", str(src), dst, "--only-show-errors"], check=True)
    print("uploaded to", BUCKET)


if __name__ == "__main__":
    main()
