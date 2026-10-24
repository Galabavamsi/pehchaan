# Risk API (app/server) + fusion engine. Build from the repo root:
#   docker build -f deploy/api.Dockerfile -t pehchaan-api .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    PEHCHAAN_DATA=/data
WORKDIR /srv

COPY app/server/requirements.txt app/server/requirements.txt
RUN pip install -r app/server/requirements.txt \
 && python -m playwright install --with-deps chromium   # evidence-pack PDF

COPY engine engine
RUN pip install ./engine
# engine config.yaml reads measured voice LRs (and their provenance for the console) from here;
# clone_vs_detect.json feeds the #/benchmark page
COPY ml/results/*.json ml/results/
COPY app/server app/server

WORKDIR /srv/app/server
EXPOSE 8400
# SQLite and the evidence signing key live on the /data volume, so they survive redeploys
VOLUME /data
CMD ["uvicorn", "pehchaan_api.main:app", "--host", "0.0.0.0", "--port", "8400", "--proxy-headers", "--forwarded-allow-ips", "*"]
