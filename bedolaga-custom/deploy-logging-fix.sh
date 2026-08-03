#!/bin/bash
# Deploy Bedolaga bot logging/network fix to production.
set -euo pipefail

REMOTE_HOST="${REMOTE_HOST:-13.143.130.10}"
REMOTE_USER="${REMOTE_USER:-root}"
REMOTE_PW="${REMOTE_PW:-}"
BEDOLAGA_DIR="/opt/bedolaga"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "$REMOTE_PW" ]; then
  echo "Set REMOTE_PW env var" >&2
  exit 1
fi

ssh_cmd() {
  sshpass -p "$REMOTE_PW" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=20 "${REMOTE_USER}@${REMOTE_HOST}" "$@"
}

scp_cmd() {
  sshpass -p "$REMOTE_PW" scp -o StrictHostKeyChecking=no -o ConnectTimeout=20 "$@"
}

echo ">>> Upload custom patches"
ssh_cmd "mkdir -p ${BEDOLAGA_DIR}/custom"
scp_cmd "${SCRIPT_DIR}/logging_handler.py" "${REMOTE_USER}@${REMOTE_HOST}:${BEDOLAGA_DIR}/custom/logging_handler.py"
scp_cmd "${SCRIPT_DIR}/channel_subscription_service.py" "${REMOTE_USER}@${REMOTE_HOST}:${BEDOLAGA_DIR}/custom/channel_subscription_service.py"

echo ">>> Patch docker-compose.yml"
ssh_cmd "python3" <<'PY'
from pathlib import Path

path = Path("/opt/bedolaga/docker-compose.yml")
text = path.read_text()

mount = "      - ./custom/logging_handler.py:/app/app/logging_handler.py:ro"
if mount not in text:
    needle = "      - ./custom/channel_checker.py:/app/app/middlewares/channel_checker.py:ro"
    if needle not in text:
        raise SystemExit("channel_checker mount not found")
    text = text.replace(needle, needle + "\n" + mount)

svc_mount = "      - ./custom/channel_subscription_service.py:/app/app/services/channel_subscription_service.py:ro"
if svc_mount not in text:
    needle = "      - ./custom/logging_handler.py:/app/app/logging_handler.py:ro"
    if needle not in text:
        raise SystemExit("logging_handler mount not found")
    text = text.replace(needle, needle + "\n" + svc_mount)

if "extra_hosts:" not in text:
    needle = "    env_file:\n      - .env"
    repl = (
        "    env_file:\n      - .env\n"
        "    dns:\n      - 1.1.1.1\n      - 8.8.8.8\n"
        "    extra_hosts:\n      - \"panel.satkaconnect.xyz:13.143.130.10\""
    )
    text = text.replace(needle, repl, 1)

if "remnawave-network" not in text:
    text = text.replace(
        "    networks:\n      - bot-network",
        "    networks:\n      - bot-network\n      - remnawave-network",
        1,
    )
    text = text.replace(
        "networks:\n  bot-network:\n    driver: bridge",
        "networks:\n  bot-network:\n    driver: bridge\n  remnawave-network:\n    external: true",
        1,
    )

path.write_text(text)
print("docker-compose.yml updated")
PY

echo ">>> Recreate bot container (without touching db/redis)"
ssh_cmd "cd ${BEDOLAGA_DIR} && docker compose up -d --no-deps --force-recreate bot"

echo ">>> Verify"
ssh_cmd "docker exec bedolaga_bot python3 -c \"
import socket
print('panel', socket.gethostbyname('panel.satkaconnect.xyz'))
print('telegram', socket.gethostbyname('api.telegram.org'))
from app.logging_handler import (
    _is_transient_db_error,
    _is_transient_telegram_transport_error,
)
sample={'logger':'aiogram.dispatcher','event':'Failed to fetch updates','e':Exception('Request timeout error')}
print('poll_filter', _is_transient_telegram_transport_error(sample))
bad_gw={'logger':'app.services.channel_subscription_service','event':'Unexpected error checking channel','error':'Telegram server says - Bad Gateway'}
print('gw_filter', _is_transient_telegram_transport_error(bad_gw))
db_err={'logger':'app.services.monitoring_service','event':'Error checking channel subscriptions','error':Exception('connection is closed')}
print('db_filter', _is_transient_db_error(db_err))
from app.services.channel_subscription_service import TelegramServerError
print('svc_import', TelegramServerError.__name__)
\""

echo "Done."
