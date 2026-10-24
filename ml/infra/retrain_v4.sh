#!/bin/bash
# Paid-API retrain (2026-10-24; common/protocol.py note of that date): model A's recipe (ours_v3_rc: learned channel
# + real-call rows) plus the new Sarvam v3 / v4 Flash, OpenAI, Deepgram and S01 Sarvam-clone clips, and FLEURS speech
# for the languages that had no bona fide training audio. Then score the new model on real calls and the same fixed
# simulated sample as model A, score both on the new engines' unseen voices, upload, and stop the box.
#   nohup bash ~/pehchaan/ml/infra/retrain_v4.sh > ~/logs/retrain_v4.log 2>&1 &
#
# Same safety as retrain_v3.sh: a run counts as finished only with "best dev EER" in its log and a best.pt, which
# writes ~/runs/<name>/DONE; the last line says SUCCESS or FAILED; the box stops either way.
set -u
PY=~/envs/det/bin/python
ML=~/pehchaan/ml
W=~/work
RC=$W/realcall
OUT=$W/scores_v4
BUCKET=s3://pehchaan-ml-301745146083-use1
NAME=ours_v4_api
export REALCALL_WORK=$RC
cd $ML
mkdir -p ~/logs $OUT
FAILED=()

echo "=== data ($(date -Is))"
aws s3 sync $BUCKET/work/api2_src $W/api2_src --only-show-errors || FAILED+=("sync:api2")
D=~/data/fleurs; mkdir -p $D; : > $D/urls_v4.txt
for lang in bn_in gu_in kn_in ml_in mr_in pa_in or_in; do
  [ -d $D/$lang/audio/train/train ] && continue
  echo "https://huggingface.co/datasets/google/fleurs/resolve/main/data/$lang/audio/train.tar.gz" >> $D/urls_v4.txt
  echo "  out=$lang/audio/train.tar.gz" >> $D/urls_v4.txt
  echo "https://huggingface.co/datasets/google/fleurs/resolve/main/data/$lang/train.tsv" >> $D/urls_v4.txt
  echo "  out=$lang/train.tsv" >> $D/urls_v4.txt
done
if [ -s $D/urls_v4.txt ]; then
  (cd $D && aria2c -q -x 8 -j 6 -c -i urls_v4.txt \
     && for f in */audio/train.tar.gz; do d=${f%.tar.gz}; mkdir -p $d && tar -xzf $f -C $d && rm -f $f; done) \
    || FAILED+=("fleurs")
fi
if $PY data_prep/add_api2.py > ~/logs/add_api2.log 2>&1; then tail -4 ~/logs/add_api2.log; else FAILED+=("add_api2"); tail -20 ~/logs/add_api2.log; fi

ARGS="--src_manifest $W/manifests/corpus_src_v4.csv --eval_manifest $W/manifests/corpus_eval_v4.csv --init la --epochs 6
      --steps_per_epoch 600 --bs 16 --dev_max 2500 --seed 0 --aug_set v3 --realcall_manifest $RC/realcall.csv
      --realcall_weight 0.25"
if [ ${#FAILED[@]} -eq 0 ]; then
  echo "=== composition ($(date -Is))"
  $PY train/finetune.py $ARGS --out ~/runs/${NAME}_dry --dry_run > ~/logs/dry_v4.log 2>&1 || FAILED+=("dry_run")
  grep -E "^train |sampling mass" ~/logs/dry_v4.log
fi
if [ ${#FAILED[@]} -eq 0 ]; then
  echo "=== train $NAME ($(date -Is))"
  if [ -f ~/runs/$NAME/DONE ]; then echo "already finished, skipping"
  else
    rm -rf ~/runs/$NAME; rm -f $OUT/*__$NAME.csv    # scores of old weights must never survive a retrain
    if $PY train/finetune.py $ARGS --out ~/runs/$NAME > ~/logs/tr_$NAME.log 2>&1 \
       && grep -q "best dev EER" ~/logs/tr_$NAME.log && [ -f ~/runs/$NAME/best.pt ]; then
      date -Is > ~/runs/$NAME/DONE; tail -2 ~/logs/tr_$NAME.log
    else
      echo "!!! training $NAME FAILED"; tail -5 ~/logs/tr_$NAME.log; FAILED+=("train:$NAME")
    fi
  fi
fi

echo "=== score ($(date -Is))"
# model A's real-call and simulated scores are in scores_rc; the same two manifests make the comparison like-for-like
cp $W/scores_rc/realcall_eval.csv $W/scores_rc/sim_test.csv $OUT/ 2>/dev/null || FAILED+=("score:manifests")
cp $W/manifests/api2_test.csv $OUT/ 2>/dev/null || FAILED+=("score:api2_manifest")
if [ -f ~/runs/$NAME/DONE ]; then
  $PY eval/score.py --manifest $OUT/realcall_eval.csv --root $RC --detector ckpt:$HOME/runs/$NAME/best.pt \
      --out $OUT/real__$NAME.csv > ~/logs/score_real_$NAME.log 2>&1 || FAILED+=("score_real:$NAME")
  $PY eval/score.py --manifest $OUT/sim_test.csv --limit 6000 --detector ckpt:$HOME/runs/$NAME/best.pt \
      --out $OUT/sim__$NAME.csv > ~/logs/score_sim_$NAME.log 2>&1 || FAILED+=("score_sim:$NAME")
fi
for m in $NAME ours_v3_rc; do
  [ -f ~/runs/$m/best.pt ] || { echo "skip api2 scoring for $m"; continue; }
  rm -f $OUT/api2__$m.csv
  $PY eval/score.py --manifest $OUT/api2_test.csv --detector ckpt:$HOME/runs/$m/best.pt \
      --out $OUT/api2__$m.csv > ~/logs/score_api2_$m.log 2>&1 || FAILED+=("score_api2:$m")
done

echo "=== upload ($(date -Is))"
aws s3 sync $OUT $BUCKET/work/scores_v4 --only-show-errors || FAILED+=("upload:scores")
if [ -f ~/runs/$NAME/DONE ]; then aws s3 sync ~/runs/$NAME $BUCKET/runs/$NAME --only-show-errors || FAILED+=("upload:$NAME"); fi
aws s3 cp ~/logs/ $BUCKET/logs/retrain_v4/ --recursive --exclude "*" --include "tr_${NAME}*" --include "score_*" \
    --include "add_api2.log" --include "dry_v4.log" --include "retrain_v4.log" --only-show-errors || FAILED+=("upload:logs")

if [ ${#FAILED[@]} -eq 0 ]; then STATUS="SUCCESS"; else STATUS="FAILED: ${FAILED[*]}"; fi
echo "$STATUS ($(date -Is))" | tee ~/logs/retrain_v4_status.txt
aws s3 cp ~/logs/retrain_v4_status.txt $BUCKET/logs/retrain_v4/status.txt --only-show-errors || true
echo "=== $STATUS; stopping instance in 2 min"
sudo shutdown -h +2
