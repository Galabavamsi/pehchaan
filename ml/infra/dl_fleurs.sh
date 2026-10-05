#!/bin/bash
# FLEURS (google/fleurs, CC-BY-4.0) bona fide speech: audio tarballs + TSVs.
set -u
B=https://huggingface.co/datasets/google/fleurs/resolve/main/data
D=~/data/fleurs; mkdir -p $D; cd $D
L=""
for lang in hi_in te_in ta_in en_us; do for s in train dev test; do L="$L $lang/$s"; done; done
for lang in mr_in bn_in kn_in ml_in gu_in; do for s in dev test; do L="$L $lang/$s"; done; done
: > urls.txt
for x in $L; do lang=${x%/*}; s=${x#*/}
  echo "$B/$lang/audio/$s.tar.gz" >> urls.txt; echo "  out=$lang/audio/$s.tar.gz" >> urls.txt
  echo "$B/$lang/$s.tsv" >> urls.txt; echo "  out=$lang/$s.tsv" >> urls.txt
done
aria2c -q -x 8 -j 6 -c -i urls.txt
for f in */audio/*.tar.gz; do d=${f%.tar.gz}; mkdir -p $d && tar -xzf $f -C $d && rm -f $f; done
echo FLEURS_DONE; du -sh $D
