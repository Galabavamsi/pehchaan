#!/bin/bash
# Final evaluation on the box: every detector -> eval.json -> metrics.json (+ latency, watermark, corpus, runs) -> SUMMARY_auto.md
#   bash eval/final.sh
set -eu
cd "$(dirname "$0")/.."
source ~/envs/det/bin/activate
S=~/work/scores
R=~/work/results
SC=()
for pair in ssl_la=ssl_la ssl_df=ssl_df nii=nii_mms300m ours=ours_v1 ours_v2_telaug=ours_v2_telaug ours_v0_noteam=ours_v0_noteam; do
  n=${pair%%=*}; f=$S/${pair#*=}__eval.csv
  [ -f "$f" ] && SC+=("$n=$f")
done
python eval/run_eval.py --eval_manifest ~/work/manifests/corpus_eval.csv --scores "${SC[@]}" --out $R/eval.json --dump_scores $R/test_scores.csv
ASV=()
for pair in ssl_la=ssl_la ssl_df=ssl_df nii=nii_mms300m ours=ours_v1 ours_v2_telaug=ours_v2_telaug; do
  f=$R/asv19_${pair#*=}.json
  [ -f "$f" ] && ASV+=("${pair%%=*}=$f")
done
python eval/assemble_metrics.py --eval_json $R/eval.json --latency $R/latency_*.json --watermark $R/watermark.json \
  --corpus_src ~/work/manifests/corpus_src.csv --corpus_eval ~/work/manifests/corpus_eval.csv \
  --runs ~/runs/ours_v0_noteam ~/runs/ours_v1 ~/runs/ours_v2_telaug --asv19 "${ASV[@]}" --out $R/metrics.json
python eval/write_summary.py --metrics $R/metrics.json --out $R/SUMMARY_auto.md
echo done
