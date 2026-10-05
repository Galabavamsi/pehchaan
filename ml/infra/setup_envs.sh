#!/bin/bash
# One isolated uv venv per generator / tool so their pinned dependencies never collide.
# Usage on the GPU box:  bash setup_envs.sh <envname>   (or "all")
# Logs: ~/logs/env_<name>.log
set -uo pipefail
export PATH="$HOME/.local/bin:$PATH"
export UV_CACHE_DIR=/opt/dlami/nvme/uv-cache
export UV_LINK_MODE=copy
export HF_HOME=$HOME/hf
mkdir -p ~/envs ~/repos ~/logs
TORCH_CU124="--index-url https://download.pytorch.org/whl/cu124"

mk() {  # mk <name> <python>
  [ -d ~/envs/$1 ] || uv venv -q -p "$2" ~/envs/$1
  source ~/envs/$1/bin/activate
}

env_det() {   # detectors, training, eval, serving, data prep
  mk det 3.11
  uv pip install torch==2.6.0 torchaudio==2.6.0 $TORCH_CU124
  uv pip install "transformers==4.56.1" "huggingface_hub>=0.34" datasets soundfile librosa scipy numpy pandas \
     scikit-learn matplotlib tqdm pyyaml fastapi "uvicorn[standard]" python-multipart silero-vad \
     pyroomacoustics faster-whisper rapidfuzz resemble-perth audioseal requests safetensors einops
}

env_f5() {    # F5-TTS (en) and IndicF5 (hi/te/ta)
  mk f5 3.10
  uv pip install torch==2.6.0 torchaudio==2.6.0 $TORCH_CU124
  uv pip install f5-tts soundfile
  [ -d ~/repos/IndicF5 ] || git clone -q https://github.com/ai4bharat/IndicF5.git ~/repos/IndicF5
}

env_xtts() {  # Coqui XTTS-v2 (CPML, non-commercial) via the maintained idiap fork
  mk xtts 3.11
  uv pip install torch==2.6.0 torchaudio==2.6.0 $TORCH_CU124
  uv pip install coqui-tts soundfile "transformers>=4.55,<5"
}

env_chatterbox() {  # Resemble Chatterbox multilingual (MIT, Perth watermark)
  mk chatterbox 3.11
  uv pip install torch==2.6.0 torchaudio==2.6.0 $TORCH_CU124
  uv pip install chatterbox-tts soundfile "setuptools<80"
}

env_seedvc() {  # Seed-VC voice conversion (GPL-3.0)
  [ -d ~/repos/seed-vc ] || git clone -q https://github.com/Plachtaa/seed-vc.git ~/repos/seed-vc
  mk seedvc 3.10
  uv pip install torch==2.6.0 torchaudio==2.6.0 $TORCH_CU124
  grep -viE '^(torch|torchaudio|torchvision)([=<> ]|$)' ~/repos/seed-vc/requirements.txt > /tmp/seedvc_req.txt
  uv pip install -r /tmp/seedvc_req.txt
}

env_cosy() {  # CosyVoice2 (Apache-2.0)
  [ -d ~/repos/CosyVoice ] || git clone -q --recursive https://github.com/FunAudioLLM/CosyVoice.git ~/repos/CosyVoice
  mk cosy 3.10
  uv pip install torch==2.3.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cu121
  grep -viE '^(torch|torchaudio|tensorrt|deepspeed|onnxruntime-gpu|gradio|fastapi|uvicorn|fastapi-cli)' ~/repos/CosyVoice/requirements.txt \
     | sed 's/;.*//' > /tmp/cosy_req.txt
  uv pip install -r /tmp/cosy_req.txt
  uv pip install onnxruntime-gpu huggingface_hub modelscope
}

env_misc() {  # MMS-TTS / Indic Parler-TTS stock voices + commercial API clients
  mk misc 3.11
  uv pip install torch==2.6.0 torchaudio==2.6.0 $TORCH_CU124
  uv pip install "transformers==4.46.1" soundfile librosa requests openai google-genai sentencepiece \
     "git+https://github.com/huggingface/parler-tts.git"
}

target=${1:-all}
if [ "$target" = all ]; then
  for e in det f5 xtts chatterbox seedvc cosy misc; do (env_$e) > ~/logs/env_$e.log 2>&1 & done
  wait
else
  env_$target
fi
echo "done $target"
