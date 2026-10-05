#!/bin/bash
# Push local ml/ code to the GPU box (~/pehchaan/ml). Excludes keys, data and weights.
cd "$(dirname "$0")/.."
python infra/fix_eol.py > /dev/null 2>&1 || true
tar --exclude='./infra/pehchaan-ml' --exclude='./infra/known_hosts' --exclude='./serve/weights' --exclude='./serve/.venv' --exclude='./work' \
    --exclude='*.wav' --exclude='*.pt' --exclude='*.pth' --exclude='__pycache__' --exclude='./results/*.png' -czf - . \
  | ssh -F infra/ssh_config pehchaan 'mkdir -p ~/pehchaan/ml && tar -xzf - -C ~/pehchaan/ml'
