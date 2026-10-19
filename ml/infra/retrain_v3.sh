#!/bin/bash
# Real-call retraining (2026-10-19): three runs that isolate the learned channel and the real-call rows, then
# score them (and v1) on real calls and on a fixed sample of the simulated test set, upload, and stop the box.
#   nohup bash ~/pehchaan/ml/infra/retrain_v3.sh > ~/logs/retrain_v3.log 2>&1 &
#
# Every step is checked. A run counts as finished only when finetune.py exits 0 and logs "best dev EER", which
# writes ~/runs/<name>/DONE; a rerun skips only runs with that marker, never a half-written best.pt. The final line
# says SUCCESS or FAILED (with the failed steps), and the same status is uploaded as status.txt. The box stops
# either way, so a failure never leaves a GPU running.
set -u
PY=~/envs/det/bin/python
ML=~/pehchaan/ml
W=~/work
RC=$W/realcall
OUT=$W/scores_rc
BUCKET=s3://pehchaan-ml-301745146083-use1
export REALCALL_WORK=$RC
cd $ML
FAILED=()

train() {  # name aug_set use_realcall
  local name=$1 aug=$2 rc=$3
  local extra=""
  [ "$rc" = "yes" ] && extra="--realcall_manifest $RC/realcall.csv --realcall_weight 0.25"
  echo "=== train $name ($(date -Is))"
  if [ -f ~/runs/$name/DONE ]; then echo "already finished, skipping"; return; fi
  rm -rf ~/runs/$name
  rm -f $OUT/real__$name.csv $OUT/sim__$name.csv     # scores of the old weights must never survive a retrain
  if $PY train/finetune.py --src_manifest $W/manifests/corpus_src.csv --eval_manifest $W/manifests/corpus_eval.csv \
      --out ~/runs/$name --init la --epochs 6 --steps_per_epoch 600 --bs 16 --dev_max 2500 --seed 0 \
      --aug_set $aug $extra > ~/logs/tr_$name.log 2>&1 \
     && grep -q "best dev EER" ~/logs/tr_$name.log && [ -f ~/runs/$name/best.pt ]; then
    date -Is > ~/runs/$name/DONE
    tail -2 ~/logs/tr_$name.log
  else
    echo "!!! training $name FAILED (see ~/logs/tr_$name.log)"; tail -5 ~/logs/tr_$name.log
    FAILED+=("train:$name")
  fi
}

train ours_v3_rc v3 yes     # A: learned channel + real-call rows (candidate)
train ours_v1_rc v1 yes     # B: real-call rows only
train ours_v3    v3 no      # C: learned channel only

echo "=== score ($(date -Is))"
mkdir -p $OUT
# Labelled score manifests travel with the scores, so the folder synced from S3 is all compare_models.py needs.
if ! $PY - <<'EOF'
import os
import pandas as pd
W = os.path.expanduser("~/work")
rc = pd.read_csv(f"{W}/realcall/realcall.csv")
rc = rc[(rc.qc == "ok") & rc.path.notna()]
cols = [c for c in ("utt_id", "path", "label", "generator", "speaker", "split", "call_id", "kind", "device") if c in rc]
rc[cols].to_csv(f"{W}/scores_rc/realcall_eval.csv", index=False)
ev = pd.read_csv(f"{W}/manifests/corpus_eval.csv")
cols = [c for c in ("utt_id", "path", "label", "generator", "channel", "heldout") if c in ev]
ev[ev.split == "test"][cols].to_csv(f"{W}/scores_rc/sim_test.csv", index=False)
EOF
then FAILED+=("score:manifests"); fi
for m in ours_v1 ours_v3_rc ours_v1_rc ours_v3; do
  if [ "$m" != "ours_v1" ] && [ ! -f ~/runs/$m/DONE ]; then echo "skip scoring $m (not finished)"; continue; fi
  # Always score from scratch: eval/score.py resumes from an existing file, which would keep scores of older
  # weights next to new ones. A few minutes per model is cheaper than a mixed result.
  rm -f $OUT/real__$m.csv $OUT/sim__$m.csv
  $PY eval/score.py --manifest $OUT/realcall_eval.csv --root $RC --detector ckpt:$HOME/runs/$m/best.pt \
      --out $OUT/real__$m.csv > ~/logs/score_real_$m.log 2>&1 || FAILED+=("score_real:$m")
  $PY eval/score.py --manifest $OUT/sim_test.csv --limit 6000 --detector ckpt:$HOME/runs/$m/best.pt \
      --out $OUT/sim__$m.csv > ~/logs/score_sim_$m.log 2>&1 || FAILED+=("score_sim:$m")
  echo "scored $m"
done

echo "=== upload ($(date -Is))"
aws s3 sync $OUT $BUCKET/work/scores_rc --only-show-errors || FAILED+=("upload:scores")
for m in ours_v3_rc ours_v1_rc ours_v3; do
  [ -f ~/runs/$m/DONE ] || continue
  aws s3 sync ~/runs/$m $BUCKET/runs/$m --only-show-errors || FAILED+=("upload:$m")
done
aws s3 cp ~/logs/ $BUCKET/logs/retrain_v3/ --recursive --exclude "*" --include "tr_ours_v*" --include "score_*" \
    --include "retrain_v3.log" --only-show-errors || FAILED+=("upload:logs")

if [ ${#FAILED[@]} -eq 0 ]; then STATUS="SUCCESS"; else STATUS="FAILED: ${FAILED[*]}"; fi
echo "$STATUS ($(date -Is))" | tee ~/logs/retrain_v3_status.txt
aws s3 cp ~/logs/retrain_v3_status.txt $BUCKET/logs/retrain_v3/status.txt --only-show-errors || true
echo "=== $STATUS; stopping instance in 2 min"
sudo shutdown -h +2
