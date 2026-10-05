#!/bin/bash
# Score the dev/test channel corpus with each detector given on the command line.
#   bash eval/score_all.sh ssl_la ssl_df nii_mms300m ckpt:/path/best.pt
# Scores -> ~/work/scores/<name>__eval.csv (resumable)
set -u
cd "$(dirname "$0")/.."
source ~/envs/det/bin/activate
export HF_HOME=~/hf
M=~/work/manifests/corpus_eval.csv
python - <<EOF
import pandas as pd
m = pd.read_csv("$M")
m = m[m.split.isin(["dev", "test"])]
m[["utt_id", "path"]].to_csv("/home/ubuntu/work/manifests/eval_paths.csv", index=False)
print("eval items", len(m))
EOF
for d in "$@"; do
  name=$(echo "$d" | sed 's#ckpt:.*/runs/##; s#/best.pt##; s#[:/]#_#g')
  echo "== $d -> $name"
  python eval/score.py --manifest ~/work/manifests/eval_paths.csv --detector "$d" --out ~/work/scores/${name}__eval.csv --bs 24
done
