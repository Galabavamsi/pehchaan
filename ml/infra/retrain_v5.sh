#!/bin/bash
# Generalisation run "v5" (2026-10-24; common/protocol.py note "v5"). IndicVoices Hindi speakers and their XTTS-v2 /
# F5-Hindi clones (data_prep/add_iv.py), and NII-initialised fine-tunes. Three candidates, model A untouched:
#   ours_n1  NII init + the ours_a2 data     ours_a3  LA init + a2 data + iv     ours_n3  NII init + a2 data + iv
# Sarvam IVC is never trained (--exclude_sources api2_ivc), so S01's and S02's Sarvam clones are both unseen cloners.
# Scores model A (ours_v3_rc), NII zero-shot (nii0) and the candidates on the fixed dev set, the real-call test, the
# clean/AMR bench (S01/S02 genuine vs every cloner, Sarvam IVC included), unseen IndicVoices speakers, the paid-API
# unseen voices and the simulated test sample; uploads as results land; stops the box.
#   nohup bash ~/pehchaan/ml/infra/retrain_v5.sh > ~/logs/retrain_v5.log 2>&1 &
# Needs on the box: an HF token with IndicVoices access in ~/hf (huggingface-cli login), never the laptop's .env.
#
# Same safety as retrain_v4.sh: a run counts as finished only with "best dev EER" in its log and a best.pt, which
# writes ~/runs/<name>/DONE; the last line says SUCCESS or FAILED; the box stops either way.
set -u
PY=~/envs/det/bin/python
ML=~/pehchaan/ml
W=~/work
RC=$W/realcall
OUT=$W/scores_v5
BUCKET=s3://pehchaan-ml-301745146083-use1
export REALCALL_WORK=$RC HF_HOME=~/hf
cd $ML
mkdir -p ~/logs $OUT
FAILED=()

echo "=== data ($(date -Is))"
aws s3 sync $BUCKET/work/realcall_test $W/realcall_test --only-show-errors || FAILED+=("sync:realcall_test")
aws s3 sync $BUCKET/work/bench_src $W/bench_src --only-show-errors || FAILED+=("sync:bench_src")
for f in dev_sim.csv dev_rc.csv api2_test.csv sim_test.csv devsim__ours_v3_rc.csv devrc__ours_v3_rc.csv \
         api2__ours_v3_rc.csv realtest__ours_v3_rc.csv; do
  aws s3 cp $BUCKET/work/scores_v4/$f $OUT/$f --only-show-errors || FAILED+=("sync:$f")
done
cp $W/realcall_test/realcall_test.csv $OUT/ 2>/dev/null || FAILED+=("realcall_test.csv")
if ! $PY - <<'EOF'
import os
from huggingface_hub import hf_hub_download
from common.protocol import IV_SHARDS
for k in IV_SHARDS:
    hf_hub_download("ai4bharat/IndicVoices", f"hindi/train-{k:05d}-of-00082.parquet", repo_type="dataset",
                    local_dir=os.path.expanduser("~/data/iv"))
print("IndicVoices shards", IV_SHARDS)
EOF
then FAILED+=("iv_download"); fi

# bench manifests: the consented clean files, and the same files through the AMR-NB channel seeded per file name
# (as eval/clone_vs_detect.py does)
if ! $PY - <<'EOF'
import os, zlib
from pathlib import Path
import numpy as np, pandas as pd
from channel import channels as CH
from common.audio import load, save
W = Path(os.path.expanduser("~/work")); B = W / "bench_src"; A = W / "bench_amr"; A.mkdir(exist_ok=True)
rows = []
for p in sorted(B.glob("genuine/*/*.wav")):
    rows.append(dict(utt_id=p.stem, path=str(p), label="bonafide", generator="genuine", speaker=p.parent.name))
for p in sorted(B.glob("clone/*/*.wav")):
    rows.append(dict(utt_id=p.stem, path=str(p), label="spoof", generator=p.parent.name, speaker=p.stem.split("__")[1]))
clean = pd.DataFrame(rows)
amr = clean.copy()
amr["path"] = [str(A / f"{u}.wav") for u in clean.utt_id]
for src, dst in zip(clean.path, amr.path):
    if not os.path.exists(dst):
        save(dst, CH.amr(load(src), np.random.default_rng(zlib.crc32(Path(src).name.encode()))))
out = W / "scores_v5"
clean.to_csv(out / "bench_clean.csv", index=False); amr.to_csv(out / "bench_amr.csv", index=False)
print("bench", len(clean), clean.groupby(["generator", "speaker"]).size().to_dict())
EOF
then FAILED+=("bench_manifests"); fi

echo "=== IndicVoices selection and clones ($(date -Is))"
if $PY data_prep/add_iv.py select > ~/logs/iv_select.log 2>&1; then tail -12 ~/logs/iv_select.log
else FAILED+=("iv_select"); tail -20 ~/logs/iv_select.log; fi
for k in 0 1 2; do   # XTTS is slow and leaves the GPU mostly idle: three workers; F5-Hindi is faster: two
  COQUI_TOS_AGREED=1 ~/envs/xtts/bin/python gen/run_xtts.py --jobs $W/jobs/iv_xtts.jsonl --shard $k --nshards 3 \
      > ~/logs/iv_xtts_$k.log 2>&1 &
done
for k in 0 1; do
  ~/envs/f5/bin/python gen/run_f5.py --hindi --jobs $W/jobs/iv_f5hi.jsonl --shard $k --nshards 2 > ~/logs/iv_f5hi_$k.log 2>&1 &
done
wait
tail -n 1 ~/logs/iv_xtts_*.log ~/logs/iv_f5hi_*.log
for g in xtts f5hi; do   # a rerun skips finished clips, so count files rather than trusting the logs
  n_jobs=$(wc -l < $W/jobs/iv_$g.jsonl 2>/dev/null || echo 0)
  n_done=$(ls $W/gen/iv/$g 2>/dev/null | grep -c "\.wav$")
  echo "$g clones: $n_done of $n_jobs"
  [ "$n_jobs" -gt 0 ] && [ $((n_done * 10)) -ge $((n_jobs * 9)) ] || FAILED+=("iv_clones:$g")
done

COMMON="--init la --epochs 6 --steps_per_epoch 600 --bs 16 --dev_max 2500 --seed 0 --aug_set v3
        --realcall_manifest $RC/realcall.csv --realcall_weight 0.25 --exclude_sources api2_ivc"
V4="--src_manifest $W/manifests/corpus_src_v4.csv --eval_manifest $W/manifests/corpus_eval_v4.csv"
V5="--src_manifest $W/manifests/corpus_src_v5.csv --eval_manifest $W/manifests/corpus_eval_v5.csv"

train() {  # name extra_args (a later --init overrides the one in COMMON)
  local name=$1 extra=$2
  echo "=== train $name ($(date -Is))"
  if [ -f ~/runs/$name/DONE ]; then echo "already finished, skipping"; return; fi
  rm -rf ~/runs/$name; rm -f $OUT/*__$name.csv    # scores of old weights must never survive a retrain
  $PY train/finetune.py $COMMON $extra --out ~/runs/${name}_dry --dry_run > ~/logs/dry_$name.log 2>&1 \
    && grep -E "^train |sampling mass" ~/logs/dry_$name.log
  if $PY train/finetune.py $COMMON $extra --out ~/runs/$name > ~/logs/tr_$name.log 2>&1 \
     && grep -q "best dev EER" ~/logs/tr_$name.log && [ -f ~/runs/$name/best.pt ]; then
    date -Is > ~/runs/$name/DONE; grep -E "^epoch|best dev" ~/logs/tr_$name.log | tail -3
  else
    echo "!!! training $name FAILED"; tail -5 ~/logs/tr_$name.log; FAILED+=("train:$name")
  fi
}

det() {  # model name -> eval/score.py detector
  case $1 in
    nii0) echo "nii_mms300m" ;;
    ours_n*) echo "niickpt:$HOME/runs/$1/best.pt" ;;
    *) echo "ckpt:$HOME/runs/$1/best.pt" ;;
  esac
}

score() {  # model manifest out [root|limit=N]
  local m=$1 man=$2 out=$3 opt=${4:-} extra=""
  [ -f $out ] && { echo "have $(basename $out)"; return; }
  case $opt in limit=*) extra="--limit ${opt#limit=}" ;; "") ;; *) extra="--root $opt" ;; esac
  $PY eval/score.py --manifest $man $extra --detector $(det $m) --out $out \
      > ~/logs/score_$(basename $out .csv).log 2>&1 || FAILED+=("score:$(basename $out)")
}

score_all() {  # model: every set (model A's dev, real-call, paid-API and simulated scores are copied from v4)
  local m=$1
  if [ "$m" != nii0 ] && [ ! -f ~/runs/$m/DONE ]; then echo "skip scoring $m"; return; fi
  score $m $OUT/dev_sim.csv $OUT/devsim__$m.csv
  score $m $OUT/dev_rc.csv $OUT/devrc__$m.csv $RC
  score $m $OUT/realcall_test.csv $OUT/realtest__$m.csv $W/realcall_test
  score $m $OUT/bench_clean.csv $OUT/benchclean__$m.csv
  score $m $OUT/bench_amr.csv $OUT/benchamr__$m.csv
  [ -f $W/manifests/iv_test.csv ] && score $m $W/manifests/iv_test.csv $OUT/ivtest__$m.csv
  score $m $OUT/api2_test.csv $OUT/api2__$m.csv
  [ "$m" != ours_v3_rc ] && score $m $OUT/sim_test.csv $OUT/sim__$m.csv limit=6000
  aws s3 sync $OUT $BUCKET/work/scores_v5 --only-show-errors || FAILED+=("upload:scores")   # results land as they come
  if [ -f ~/runs/$m/DONE ]; then aws s3 sync ~/runs/$m $BUCKET/runs/$m --only-show-errors || FAILED+=("upload:$m"); fi
  echo "scored and uploaded $m ($(date -Is))"
}

echo "=== corpus v5 and the NII backbone run ($(date -Is))"
$PY data_prep/add_iv.py build > ~/logs/iv_build.log 2>&1 &   # CPU, while ours_n1 (old data) trains on the GPU
BUILD=$!
train ours_n1 "$V4 --init nii"
if wait $BUILD; then tail -14 ~/logs/iv_build.log; else FAILED+=("iv_build"); tail -20 ~/logs/iv_build.log; fi
score_all ours_n1
score_all ours_v3_rc
score_all nii0
if [ -f $W/manifests/corpus_src_v5.csv ]; then
  train ours_a3 "$V5 --init la"
  score_all ours_a3
  train ours_n3 "$V5 --init nii"
  score_all ours_n3
else
  FAILED+=("no corpus_src_v5: a3/n3 not trained")
fi

echo "=== upload ($(date -Is))"
aws s3 sync $W/iv_src $BUCKET/work/iv_src --only-show-errors || FAILED+=("upload:iv_src")
aws s3 sync $W/gen/iv $BUCKET/work/gen/iv --only-show-errors || FAILED+=("upload:iv_clones")
aws s3 cp $W/manifests/iv_test.csv $BUCKET/work/manifests/iv_test.csv --only-show-errors || true
aws s3 cp ~/logs/ $BUCKET/logs/retrain_v5/ --recursive --exclude "*" --include "tr_ours_*" --include "dry_ours_*" \
    --include "score_*" --include "iv_*.log" --include "retrain_v5.log" --only-show-errors || FAILED+=("upload:logs")

if [ ${#FAILED[@]} -eq 0 ]; then STATUS="SUCCESS"; else STATUS="FAILED: ${FAILED[*]}"; fi
echo "$STATUS ($(date -Is))" | tee ~/logs/retrain_v5_status.txt
aws s3 cp ~/logs/retrain_v5_status.txt $BUCKET/logs/retrain_v5/status.txt --only-show-errors || true
echo "=== $STATUS; stopping instance in 2 min"
sudo shutdown -h +2
