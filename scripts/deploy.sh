#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test -f .env.production || { echo '.env.production is missing' >&2; exit 1; }
test -L .env || { echo 'Create .env symlink to .env.production first' >&2; exit 1; }
if git remote | grep -q .; then
  git pull --ff-only
else
  echo 'No Git remote configured; deploying current local checkout.'
fi
commit="$(git rev-parse HEAD)"
if grep -q '^BUILD_COMMIT=' .env.production; then
  sed -i "s/^BUILD_COMMIT=.*/BUILD_COMMIT=$commit/" .env.production
else
  printf '\nBUILD_COMMIT=%s\n' "$commit" >> .env.production
fi
docker compose -f docker-compose.production.yml build
docker compose -f docker-compose.production.yml up -d --wait
domain="$(sed -n 's/^DOMAIN=//p' .env.production | tail -1)"
for attempt in $(seq 1 30); do
  if curl --fail --silent --show-error "https://$domain/health" | grep -q '"status":"ok"'; then
    python3 scripts/smoke_production.py "https://$domain"
    echo "Deployment healthy: $commit"
    exit 0
  fi
  sleep 2
done
echo 'Deployment health check failed' >&2
exit 1
