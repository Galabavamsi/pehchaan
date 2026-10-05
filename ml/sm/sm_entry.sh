#!/bin/bash
# SageMaker training-job entry point (ml.p4d.24xlarge, 8x A100): runs one training config per GPU in
# parallel, scores the dev/test channel corpus with each resulting model, and benchmarks latency on A100.
# Inputs  (channel "data"): ml.tar.gz-independent data tarballs + manifests + init weights (see sm/stage.sh)
# Outputs: /opt/ml/checkpoints/<run>/{best.pt,log.json,scores.csv}  (synced to S3 continuously)
set -x
export DEBIAN_FRONTEND=noninteractive
D=/opt/ml/input/data/data
CK=/opt/ml/checkpoints
LOCAL=/tmp/pw   # instance NVMe
mkdir -p $LOCAL $CK
(apt-get update -qq && apt-get install -y -qq libopus0 libopencore-amrnb0 ffmpeg > /dev/null) || true
pip install -q "transformers==4.56.1" soundfile librosa scipy pandas scikit-learn safetensors pyroomacoustics 2>&1 | tail -2
# paths in the manifests are /home/ubuntu/work/... and /home/ubuntu/weights/...
mkdir -p /home/ubuntu
for t in $D/*.tar; do tar -xf $t -C $LOCAL; done
ln -sfn $LOCAL/work /home/ubuntu/work
ln -sfn $LOCAL/weights /home/ubuntu/weights
export HOME=/home/ubuntu
cd /opt/ml/code
nvidia-smi -L
RUNS=$(python -c "import json;print(' '.join(json.load(open('/opt/ml/input/config/hyperparameters.json')).get('runs','main').strip('\"').split(',')))")
i=0
for r in $RUNS; do
  (
    export CUDA_VISIBLE_DEVICES=$i
    case $r in
      seed1)     A="--seed 1" ;;
      seed2)     A="--seed 2" ;;
      noaug)     A="--no_channel_aug" ;;
      norawboost) A="--rawboost_p 0" ;;
      initdf)    A="--init df" ;;
      noteam)    A="--exclude_sources team,team_clone" ;;
      lrhi)      A="--lr_ssl 1e-5 --lr_head 1e-4" ;;
      *)         A="" ;;
    esac
    python train/finetune.py --src_manifest /home/ubuntu/work/manifests/corpus_src.csv \
      --eval_manifest /home/ubuntu/work/manifests/corpus_eval.csv --out $CK/$r --epochs 6 --steps_per_epoch 600 \
      --bs 16 --workers 10 --dev_max 2500 $A > $CK/$r.train.log 2>&1
    python eval/score.py --manifest /home/ubuntu/work/manifests/eval_paths.csv --detector ckpt:$CK/$r/best.pt \
      --out $CK/$r/scores.csv --bs 32 > $CK/$r.score.log 2>&1
  ) &
  i=$((i+1))
done
wait
# A100 latency (10 s clip) for the first run's model
CUDA_VISIBLE_DEVICES=0 python eval/latency.py --ckpt $CK/$(echo $RUNS | cut -d' ' -f1)/best.pt --device cuda --out $CK/latency_a100.json
python eval/latency.py --ckpt $CK/$(echo $RUNS | cut -d' ' -f1)/best.pt --device cpu --threads 8 --out $CK/latency_cpu8_p4d.json
rm -f $CK/*/best.pt.tmp
echo ALL_DONE
