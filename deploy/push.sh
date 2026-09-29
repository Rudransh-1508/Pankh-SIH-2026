#!/usr/bin/env bash
# Copy Pankh to the server and (re)start it. Usage, from the repository root:
#   bash deploy/push.sh ubuntu@<server-ip> [path/to/ssh-key]
set -euo pipefail
target=${1:?Usage: bash deploy/push.sh ubuntu@<server-ip> [ssh-key]}
key=${2:-}
ssh_opts=(-o StrictHostKeyChecking=accept-new)
[ -n "$key" ] && ssh_opts+=(-i "$key")

cd "$(dirname "$0")/.."
rsync -az --delete -e "ssh ${ssh_opts[*]}" \
  --exclude .git --exclude .venv --exclude '**/.venv' --exclude '**/__pycache__' \
  --exclude mobile --exclude 'dashboard/node_modules' --exclude 'dashboard/.next' \
  --exclude 'rules/.cache' --exclude 'backend/var' --exclude 'backend/.env' \
  --exclude 'deploy/.env' --exclude 'deploy/s3.json' \
  ./ "$target:pankh/"
ssh "${ssh_opts[@]}" "$target" "bash pankh/deploy/setup.sh"
