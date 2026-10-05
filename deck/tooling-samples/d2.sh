#!/usr/bin/env bash
# Render the D2 samples. $HOME contains a space on this machine, so always quote the binary path.
set -euo pipefail
cd "$(dirname "$0")/d2"
D2="${D2_BIN:-$HOME/go/bin/d2.exe}"
F=../fonts-ttf
ELK=(--elk-nodeNodeBetweenLayers=40 --elk-edgeNodeBetweenLayers=20 "--elk-padding=[top=40,left=20,bottom=20,right=20]" --pad=10)
"$D2" --font-regular=$F/Inter-400-latin.ttf --font-bold=$F/SpaceGrotesk-700-latin.ttf --font-semibold=$F/Inter-600-latin.ttf "${ELK[@]}" pipeline_tuned.d2 ../svg/d2_elk_tuned.svg
"$D2" --sketch --font-regular=$F/Inter-400-latin.ttf "${ELK[@]}" pipeline_tuned.d2 ../svg/d2_sketch_tuned.svg
"$D2" --font-regular=$F/Inter-400-latin.ttf --font-bold=$F/SpaceGrotesk-700-latin.ttf sequence.d2 ../svg/d2_sequence.svg
"$D2" --font-regular=$F/Inter-400-latin.ttf --font-bold=$F/SpaceGrotesk-700-latin.ttf aws.d2 ../svg/d2_aws.svg   # fetches icons over the network
