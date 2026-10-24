#!/bin/bash
# Paid-API retrain (2026-10-24; common/protocol.py notes of that date). Model A's recipe (ours_v3_rc: learned channel
# + real-call rows) plus the new stock-voice clips (Sarvam v3 / v4 Flash, OpenAI, Deepgram) and FLEURS speech for the
# languages that had no bona fide training audio. Two candidates, model A untouched:
#   ours_a2      stock voices only: Sarvam IVC stays a never-trained cloner for it
#   ours_a2_ivc  plus the S01 Sarvam clones (source api2_ivc): its Sarvam IVC result is "seen generator"
# Scores A and both candidates on one fixed dev set (the promotion check), the new candidates on real calls and the
# same simulated sample as A's results, and all three on the new engines' unseen voices; uploads; stops the box.
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

# One fixed dev set for every model: old corpus dev rows (seeded sample) + real-call dev rows. Built from the
# manifests that existed before today, so the comparison with model A is like-for-like.
if ! $PY - <<'EOF'
import os
import pandas as pd
from common.protocol import HELDOUT_GENERATORS, HELDOUT_SPEAKERS
W = os.path.expanduser("~/work")
ok = lambda d: d[(~d.generator.isin(HELDOUT_GENERATORS)) & (~d.speaker.astype(str).isin(HELDOUT_SPEAKERS))]
ev = pd.read_csv(f"{W}/manifests/corpus_eval.csv")
ev = ok(ev[(ev.split == "dev") & (ev.source != "asv19")]).sample(n=4000, random_state=0)
ev[["utt_id", "path", "label", "generator", "channel"]].to_csv(f"{W}/scores_v4/dev_sim.csv", index=False)
rc = pd.read_csv(f"{W}/realcall/realcall.csv")
rc = ok(rc[(rc.split == "dev") & (rc.qc == "ok") & rc.path.notna() & rc.label.isin(["bonafide", "spoof"])])
rc[[c for c in ("utt_id", "path", "label", "generator", "speaker", "device") if c in rc]].to_csv(f"{W}/scores_v4/dev_rc.csv", index=False)
print("dev_sim", len(ev), ev.label.value_counts().to_dict(), "| dev_rc", len(rc), rc.label.value_counts().to_dict())
EOF
then FAILED+=("dev_manifests"); fi

ARGS="--src_manifest $W/manifests/corpus_src_v4.csv --eval_manifest $W/manifests/corpus_eval_v4.csv --init la --epochs 6
      --steps_per_epoch 600 --bs 16 --dev_max 2500 --seed 0 --aug_set v3 --realcall_manifest $RC/realcall.csv
      --realcall_weight 0.25"

train() {  # name extra_args
  local name=$1 extra=$2
  echo "=== train $name ($(date -Is))"
  if [ -f ~/runs/$name/DONE ]; then echo "already finished, skipping"; return; fi
  rm -rf ~/runs/$name; rm -f $OUT/*__$name.csv    # scores of old weights must never survive a retrain
  $PY train/finetune.py $ARGS $extra --out ~/runs/${name}_dry --dry_run > ~/logs/dry_$name.log 2>&1 \
    && grep -E "^train |sampling mass" ~/logs/dry_$name.log
  if $PY train/finetune.py $ARGS $extra --out ~/runs/$name > ~/logs/tr_$name.log 2>&1 \
     && grep -q "best dev EER" ~/logs/tr_$name.log && [ -f ~/runs/$name/best.pt ]; then
    date -Is > ~/runs/$name/DONE; tail -2 ~/logs/tr_$name.log
  else
    echo "!!! training $name FAILED"; tail -5 ~/logs/tr_$name.log; FAILED+=("train:$name")
  fi
}

score() {  # name manifest out [root]
  local m=$1 man=$2 out=$3 root=${4:-}
  [ -f ~/runs/$m/best.pt ] || { echo "skip $m on $(basename $man)"; return; }
  rm -f $out
  $PY eval/score.py --manifest $man ${root:+--root $root} --detector ckpt:$HOME/runs/$m/best.pt --out $out \
      > ~/logs/score_$(basename $out .csv).log 2>&1 || FAILED+=("score:$(basename $out)")
}

score_all() {  # name: fixed dev set, new engines' unseen voices, and (new models only) real calls + simulated sample
  local m=$1
  score $m $OUT/dev_sim.csv $OUT/devsim__$m.csv
  score $m $OUT/dev_rc.csv $OUT/devrc__$m.csv $RC
  score $m $OUT/api2_test.csv $OUT/api2__$m.csv
  if [ "$m" != "ours_v3_rc" ] && [ -f ~/runs/$m/DONE ]; then   # model A's real-call and simulated scores are in scores_rc
    score $m $OUT/realcall_eval.csv $OUT/real__$m.csv $RC
    $PY eval/score.py --manifest $OUT/sim_test.csv --limit 6000 --detector ckpt:$HOME/runs/$m/best.pt \
        --out $OUT/sim__$m.csv > ~/logs/score_sim_$m.log 2>&1 || FAILED+=("score_sim:$m")
  fi
  aws s3 sync $OUT $BUCKET/work/scores_v4 --only-show-errors || FAILED+=("upload:scores")   # results land as they come
  if [ -f ~/runs/$m/DONE ]; then aws s3 sync ~/runs/$m $BUCKET/runs/$m --only-show-errors || FAILED+=("upload:$m"); fi
  echo "scored and uploaded $m ($(date -Is))"
}

cp $W/scores_rc/realcall_eval.csv $W/scores_rc/sim_test.csv $W/manifests/api2_test.csv $OUT/ 2>/dev/null || FAILED+=("score:manifests")
if [ ${#FAILED[@]} -eq 0 ]; then
  train ours_a2_ivc ""                               # Varun's choice first: + the S01 Sarvam clones
  score_all ours_a2_ivc
  score_all ours_v3_rc                               # model A on the same fixed dev set and new engines
  train ours_a2 "--exclude_sources api2_ivc"         # control: stock voices only, Sarvam IVC never trained
  score_all ours_a2
fi

echo "=== upload ($(date -Is))"
aws s3 cp ~/logs/ $BUCKET/logs/retrain_v4/ --recursive --exclude "*" --include "tr_ours_a2*" --include "dry_ours_a2*" \
    --include "score_*" --include "add_api2.log" --include "retrain_v4.log" --only-show-errors || FAILED+=("upload:logs")

if [ ${#FAILED[@]} -eq 0 ]; then STATUS="SUCCESS"; else STATUS="FAILED: ${FAILED[*]}"; fi
echo "$STATUS ($(date -Is))" | tee ~/logs/retrain_v4_status.txt
aws s3 cp ~/logs/retrain_v4_status.txt $BUCKET/logs/retrain_v4/status.txt --only-show-errors || true
echo "=== $STATUS; stopping instance in 2 min"
sudo shutdown -h +2
