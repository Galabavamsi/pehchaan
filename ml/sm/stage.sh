#!/bin/bash
# Run on the GPU box: pack the corpus + manifests + init weights and code, upload to the ap-southeast-1 bucket.
#   bash sm/stage.sh v1
set -eu
V=${1:-v1}
B=s3://pehchaan-ml-301745146083-apse1/sm/$V
S=/opt/dlami/nvme/stage_$V
mkdir -p $S
cd ~
~/envs/det/bin/python - <<'EOF'
import pandas as pd
src = pd.read_csv("/home/ubuntu/work/manifests/corpus_src.csv")
ev = pd.read_csv("/home/ubuntu/work/manifests/corpus_eval.csv")
tr = src[src.split == "train"]
open("/tmp/stage_files.txt", "w").write("\n".join(p.replace("/home/ubuntu/", "") for p in tr.src16) + "\n")
e = ev[ev.split.isin(["dev", "test"])]
open("/tmp/stage_files.txt", "a").write("\n".join(p.replace("/home/ubuntu/", "") for p in e.path) + "\n")
e[["utt_id", "path"]].to_csv("/home/ubuntu/work/manifests/eval_paths.csv", index=False)
print(len(tr), len(e))
EOF
echo "work/manifests/corpus_src.csv
work/manifests/corpus_eval.csv
work/manifests/eval_paths.csv
weights/ssl_aasist/Pre_trained_SSL_anti-spoofing_models/LA_model.pth
weights/ssl_aasist/Pre_trained_SSL_anti-spoofing_models/Best_LA_model_for_DF.pth" >> /tmp/stage_files.txt
tar -cf $S/data.tar -T /tmp/stage_files.txt
cd ~/pehchaan/ml && tar --exclude='__pycache__' --exclude='./work' -czf $S/code.tar.gz .
ls -la $S
aws s3 cp $S/data.tar $B/data/data.tar --only-show-errors
aws s3 cp $S/code.tar.gz $B/code/code.tar.gz --only-show-errors
echo staged to $B
