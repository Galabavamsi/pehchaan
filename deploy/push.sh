#!/usr/bin/env bash
# Ship the code + built web demo to the deploy box and (re)start it. Run from the repo root:
#   bash deploy/push.sh <host-or-ssh-alias>
#   SERVICES="api voice" bash deploy/push.sh <host>   # e.g. hold Caddy back until the DNS records exist
# The code shipped is exactly the committed HEAD (git archive): no .env, participants.yaml, keys, data/raw or
# real-call audio, and no uncommitted edits or untracked outputs from whoever else is working in this checkout.
set -euo pipefail
HOST=${1:?usage: deploy/push.sh <host>}
ENV_FILE=deploy/.env.deploy
[ -f "$ENV_FILE" ] || { echo "missing $ENV_FILE (copy deploy/env.deploy.example)"; exit 1; }
# shellcheck disable=SC1090
source "$ENV_FILE"

# the web bundle is built from the working tree, so it must match HEAD too
if [ -n "$(git status --porcelain -- app/web/src app/web/index.html app/web/public)" ]; then
  echo "app/web has uncommitted changes: commit them (or stash) so the live site matches HEAD"; exit 1
fi

echo "== build web for https://$API_HOST"
(cd app/web && VITE_API="https://$API_HOST" npm run build --silent)

echo "== ship code (HEAD $(git rev-parse --short HEAD))"
git archive --format=tar HEAD | gzip | ssh "$HOST" "mkdir -p ~/pehchaan && tar -xzf - -C ~/pehchaan"
# empty web/ in place: Caddy bind-mounts this folder, so a fresh folder would leave a running Caddy serving nothing
tar -C app/web/dist -czf - . | ssh "$HOST" "mkdir -p ~/pehchaan/deploy/web && find ~/pehchaan/deploy/web -mindepth 1 -delete && tar -xzf - -C ~/pehchaan/deploy/web"
scp -q "$ENV_FILE" "$HOST:pehchaan/deploy/.env.deploy"

echo "== start"
ssh "$HOST" "cd ~/pehchaan/deploy && docker compose --env-file .env.deploy up -d --build ${SERVICES:-} && docker compose ps"
echo "check: curl https://$API_HOST/v1/health  and open https://$DEMO_HOST/#/demo"
