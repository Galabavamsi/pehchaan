#!/bin/bash
# Real-call retraining (2026-10-19): three runs that isolate the learned channel and the real-call rows, then
# score them (and v1) on real calls and on a fixed sample of the simulated test set, upload, and stop the box.
#   nohup bash ~/pehchaan/ml/infra/retrain_v3.sh > ~/logs/retrain_v3.log 2>&1 &
set -u
PY=~/envs/det/bin/python
ML=~/pehchaan/ml
W=~/work
RC=$W/realcall
BUCKET=s3://pehchaan-ml-301745146083-use1
export REALCALL_WORK=$RC
cd $ML

train() {  # name aug_set use_realcall
  local name=$1 aug=$2 rc=$3
  local extra=""
  [ "$rc" = "yes" ] && extra="--realcall_manifest $RC/realcall.csv --realcall_weight 0.25"
  echo "=== train $name ($(date -Is))"
  [ -f ~/runs/$name/best.pt ] && { echo "exists, skipping"; return; }
  $PY train/finetune.py --src_manifest $W/manifests/corpus_src.csv --eval_manifest $W/manifests/corpus_eval.csv \
      --out ~/runs/$name --init la --epochs 6 --steps_per_epoch 600 --bs 16 --dev_max 2500 --seed 0 \
      --aug_set $aug $extra > ~/logs/tr_$name.log 2>&1
  tail -3 ~/logs/tr_$name.log
}

train ours_v3_rc v3 yes     # A: learned channel + real-call rows (candidate)
train ours_v1_rc v1 yes     # B: real-call rows only
train ours_v3    v3 no      # C: learned channel only

echo "=== score ($(date -Is))"
mkdir -p $W/scores_rc
$PY - <<'EOF'
import pandas as pd, os
W = os.path.expanduser("~/work")
rc = pd.read_csv(f"{W}/realcall/realcall.csv")
rc = rc[(rc.qc == "ok") & rc.path.notna()]
rc[["utt_id", "path"]].to_csv(f"{W}/scores_rc/realcall_eval.csv", index=False)
ev = pd.read_csv(f"{W}/manifests/corpus_eval.csv")
ev[ev.split == "test"][["utt_id", "path"]].to_csv(f"{W}/scores_rc/sim_test.csv", index=False)
EOF
for m in ours_v1 ours_v3_rc ours_v1_rc ours_v3; do
  [ -f ~/runs/$m/best.pt ] || continue
  $PY eval/score.py --manifest $W/scores_rc/realcall_eval.csv --root $RC --detector ckpt:$HOME/runs/$m/best.pt \
      --out $W/scores_rc/real__$m.csv > ~/logs/score_real_$m.log 2>&1
  $PY eval/score.py --manifest $W/scores_rc/sim_test.csv --limit 6000 --detector ckpt:$HOME/runs/$m/best.pt \
      --out $W/scores_rc/sim__$m.csv > ~/logs/score_sim_$m.log 2>&1
  echo "scored $m"
done

echo "=== upload ($(date -Is))"
aws s3 sync $W/scores_rc $BUCKET/work/scores_rc --only-show-errors
for m in ours_v3_rc ours_v1_rc ours_v3; do
  aws s3 sync ~/runs/$m $BUCKET/runs/$m --only-show-errors
done
aws s3 cp ~/logs/ $BUCKET/logs/retrain_v3/ --recursive --exclude "*" --include "tr_ours_v*" --include "score_*" --include "retrain_v3.log" --only-show-errors
echo "=== done ($(date -Is)); stopping instance in 2 min"
sudo shutdown -h +2
