#!/bin/bash
# Deploy local ping-health responder on every VPN node for Happ VIA PROXY GET tests.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PING_DIR="$SCRIPT_DIR/ping-health"

declare -A NODES=(
  [PL]="13.143.130.10|JKQSszuQnjNUJM5x"
  [DE]="81.90.25.134|4MpQ!zXcVbN?mKlJhGfD#wS"
  [NL]="2.26.96.26|T!v9^rS@uJ#mWz5*qL&xP"
  [FI]="31.76.120.174|8#kLp\$3v!QzW^5rN@mYc&2"
  [SE]="2.27.14.163|xR9%nV2*CqW#eF7(jLp\$z"
  [HEL]="87.58.204.151|7hN#mKpQvTz!2wXyR%c"
)

deploy_node() {
  local name="$1" host="$2" pw="$3"
  echo ">>> Deploying ping-health on $name ($host)"
  sshpass -p "$pw" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 "root@$host" \
    "mkdir -p /opt/satkavpn/ping-health"
  sshpass -p "$pw" scp -o StrictHostKeyChecking=no -o ConnectTimeout=15 \
    "$PING_DIR/nginx.conf" "$PING_DIR/docker-compose.yml" \
    "root@$host:/opt/satkavpn/ping-health/"
  sshpass -p "$pw" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 "root@$host" bash -s <<'REMOTE'
set -euo pipefail
cd /opt/satkavpn/ping-health
docker compose up -d --pull always
sleep 2
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:9180/generate_204 || true)
if [ "$code" != "204" ]; then
  echo "FAIL: expected 204, got $code" >&2
  docker compose logs --tail=20 || true
  exit 1
fi
echo "OK: ping-health returns 204"
REMOTE
}

for name in PL DE NL FI SE HEL; do
  IFS='|' read -r host pw <<< "${NODES[$name]}"
  deploy_node "$name" "$host" "$pw"
done

echo "All nodes deployed."
