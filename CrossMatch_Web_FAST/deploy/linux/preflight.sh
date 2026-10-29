#!/bin/sh
# Read-only checks; no restart, mutation, secret printing or network exposure.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
[ -f .env ] || { echo 'FAIL: private .env is missing (copy .env.example locally; do NOT commit it)'; exit 1; }
[ -d database ] || { echo 'FAIL: database/ missing; create a private persistent directory or restore backup'; exit 1; }
[ -r certificates/server.crt ] || { echo 'FAIL: certificates/server.crt missing'; exit 1; }
[ -r certificates/server.key ] || { echo 'FAIL: certificates/server.key missing'; exit 1; }
if ! grep -Eq '^CROSSMATCH_COOKIE_SECURE=1[[:space:]]*$' .env; then
  echo 'FAIL: CROSSMATCH_COOKIE_SECURE=1 required for HTTPS server deployment'; exit 1
fi
if ! grep -Eq '^CROSSMATCH_HTTPS_BIND_IP=[^[:space:]]+' .env; then
  echo 'FAIL: provide an explicit approved CROSSMATCH_HTTPS_BIND_IP in private .env'; exit 1
fi
if ! command -v docker >/dev/null 2>&1; then
  echo 'FAIL: Docker CLI not installed'; exit 1
fi
docker compose -f docker-compose.server.yml config --quiet
printf '%s\n' 'PASS: private config and Compose syntax checks passed.'
printf '%s\n' 'NOTE: Not a security audit. Validate TLS chain, firewall, access permissions and live endpoints separately.'
