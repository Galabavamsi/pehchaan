#!/bin/bash
# Score new real-call clips with v1 and model A on the laptop CPU, then compare (e.g. the D2 held-out handset).
# Run from ml/ after `python -m realcall.ingest`:
#   bash infra/score_realcall_local.sh [D2]
#
# Works in a copy (realcall/work/d2/scores) seeded with the published scores, so eval/score.py only scores clips
# it hasn't seen and the retrain_v3 folder that FINDINGS.md quotes is never modified. Needs the two training
# checkpoints from S3 in runs/ours_v1/best.pt and runs/ours_v3_rc/best.pt (gitignored).
set -euo pipefail
DEVICE=${1:-D2}
PY=${PY:-../.venv/bin/python}
SRC=realcall/work/retrain_v3/scores
OUT=realcall/work/d2/scores
mkdir -p "$OUT"
for m in ours_v1 ours_v3_rc; do
  [ -f "runs/$m/best.pt" ] || { echo "missing runs/$m/best.pt (aws s3 cp --recursive s3://pehchaan-ml-301745146083-use1/runs/$m/ runs/$m/)"; exit 1; }
  for f in "sim__$m.csv" "real__$m.csv"; do [ -f "$OUT/$f" ] || cp "$SRC/$f" "$OUT/$f"; done
done
[ -f "$OUT/sim_test.csv" ] || cp "$SRC/sim_test.csv" "$OUT/sim_test.csv"
# simulated-test labels: the published sim_test.csv carries none, compare_models falls back to corpus_eval.csv
[ -f "$OUT/corpus_eval.csv" ] || cp "$SRC/../corpus_eval.csv" "$OUT/corpus_eval.csv"

# labelled manifest of every QC-ok clip (paths relative to realcall/work), device column included
$PY - "$OUT" <<'EOF'
import sys
import pandas as pd
from realcall.settings import MANIFESTS, WORK
rc = pd.read_csv(MANIFESTS / "realcall.csv")
rc = rc[(rc.qc == "ok") & rc.path.notna()].copy()
rc["path"] = [str(p).replace(str(WORK) + "/", "") for p in rc.path]
cols = [c for c in ("utt_id", "path", "label", "generator", "speaker", "split", "call_id", "kind", "device") if c in rc]
rc[cols].to_csv(f"{sys.argv[1]}/realcall_eval.csv", index=False)
print(f"{len(rc)} QC-ok clips by device and split:")
print(rc.groupby(["device", "split"]).size().to_string())
EOF

for m in ours_v1 ours_v3_rc; do
  echo "== scoring new clips with $m (CPU)"
  $PY eval/score.py --manifest "$OUT/realcall_eval.csv" --root realcall/work --detector "ckpt:runs/$m/best.pt" \
      --device cpu --out "$OUT/real__$m.csv"
done
$PY -m realcall.compare_models --dir "$OUT" --device "$DEVICE"
