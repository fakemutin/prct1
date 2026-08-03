#!/usr/bin/env bash
# Purge Beeline CDN cache for a resource (full cache clear).
# Requires BEELINE_CDN_EMAIL and BEELINE_CDN_PASSWORD in env or candelix.env.
set -euo pipefail

ENV_FILE="${ENV_FILE:-/opt/satkavpn/candelix.env}"
if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  set -a; source "$ENV_FILE"; set +a
fi

EMAIL="${BEELINE_CDN_EMAIL:-}"
PASS="${BEELINE_CDN_PASSWORD:-}"
RESOURCE_ID="${BEELINE_CDN_RESOURCE_ID:-}"

if [ -z "$EMAIL" ] || [ -z "$PASS" ]; then
  echo "Set BEELINE_CDN_EMAIL and BEELINE_CDN_PASSWORD" >&2
  exit 1
fi

TOKEN="$(curl -sS "https://api.cdn.beeline.ru/app/oauth/v1/token/" \
  --data-urlencode "username=$EMAIL" \
  --data-urlencode "password=$PASS" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("token",""))')"

if [ -z "$TOKEN" ]; then
  echo "Failed to obtain CDN API token" >&2
  exit 1
fi

if [ -z "$RESOURCE_ID" ]; then
  echo "Listing HTTP resources..."
  curl -sS -H "cdn-auth-token: $TOKEN" \
    "https://api.cdn.beeline.ru/app/http/v1/resources/" | python3 -m json.tool
  echo "Set BEELINE_CDN_RESOURCE_ID and re-run to purge cache." >&2
  exit 0
fi

echo "Purging full cache for resource $RESOURCE_ID ..."
curl -sS -X POST -H "cdn-auth-token: $TOKEN" -H "Content-Type: application/json" \
  "https://api.cdn.beeline.ru/app/cache/v1/resources/$RESOURCE_ID/purge/" \
  -d '{"purge_all": true}' | python3 -m json.tool
