# Voice Provenance Service (ml/serve), CPU int8. Weights are mounted, not baked in:
#   docker build -f deploy/voice.Dockerfile -t pehchaan-voice .
#   -v ./weights:/srv/ml/serve/weights:ro   (pehchaan-xlsr-aasist-ft-v1.safetensors from S3)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    PEHCHAAN_DEVICE=cpu PEHCHAAN_CPU_INT8=1
WORKDIR /srv/ml

RUN apt-get update && apt-get install -y --no-install-recommends libsndfile1 ffmpeg \
 && rm -rf /var/lib/apt/lists/*
RUN pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
COPY ml/serve/requirements.txt serve/requirements.txt
RUN pip install -r serve/requirements.txt

COPY ml/common common
COPY ml/models models
COPY ml/serve serve

EXPOSE 8500
CMD ["uvicorn", "serve.app:app", "--host", "0.0.0.0", "--port", "8500"]
