#!/usr/bin/env bash
# Ship the code + built web demo to the deploy box and (re)start it. Run from the repo root:
#   bash deploy/push.sh <host-or-ssh-alias>
#   SERVICES="api voice" bash deploy/push.sh <host>   # e.g. hold Caddy back until the DNS records exist
# Only git-tracked and non-ignored files are sent (git ls-files), so .env, participants.yaml, keys,
# data/raw and real-call audio can never reach the server.
set -euo pipefail
HOST=${1:?usage: deploy/push.sh <host>}
ENV_FILE=deploy/.env.deploy
[ -f "$ENV_FILE" ] || { echo "missing $ENV_FILE (copy deploy/env.deploy.example)"; exit 1; }
# shellcheck disable=SC1090
source "$ENV_FILE"

echo "== build web for https://$API_HOST"
(cd app/web && VITE_API="https://$API_HOST" npm run build --silent)

echo "== ship code"
git ls-files -co --exclude-standard -z | tar --null -T - -czf - | ssh "$HOST" "mkdir -p ~/pehchaan && tar -xzf - -C ~/pehchaan"
tar -C app/web/dist -czf - . | ssh "$HOST" "rm -rf ~/pehchaan/deploy/web && mkdir -p ~/pehchaan/deploy/web && tar -xzf - -C ~/pehchaan/deploy/web"
scp -q "$ENV_FILE" "$HOST:pehchaan/deploy/.env.deploy"

echo "== start"
ssh "$HOST" "cd ~/pehchaan/deploy && docker compose --env-file .env.deploy up -d --build ${SERVICES:-} && docker compose ps"
echo "check: curl https://$API_HOST/v1/health  and open https://$DEMO_HOST/#/demo"
