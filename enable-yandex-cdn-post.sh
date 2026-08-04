#!/bin/bash
# Yandex CDN: разрешить POST для xhttp-туннеля (/session/preview).
# Без POST edge CDN отвечает 405 — Happ не подключается.
#
# Вариант 1 — консоль Yandex Cloud:
#   Cloud CDN → ресурс cdn.satkaconnect.xyz (bc8rvy3fzggrd75utruf)
#   → вкладка «HTTP-заголовки и методы» → Изменить
#   → «Методы клиентских запросов» → добавить POST (и при необходимости PUT)
#   → Сохранить (применение до ~15 мин)
#
# Вариант 2 — CLI (нужен yc и авторизация):
#   yc cdn resource update bc8rvy3fzggrd75utruf \
#     --allowed-http-methods GET,HEAD,OPTIONS,POST
#
# Проверка после применения:
#   curl -sk -X POST -o /dev/null -w '%{http_code}\n' \
#     https://cdn.satkaconnect.xyz/session/preview
# Ожидается 404 (не 405) — запрос дошёл до origin/Caddy.

set -euo pipefail

RESOURCE_ID="${YANDEX_CDN_RESOURCE_ID:-bc8rvy3fzggrd75utruf}"

if command -v yc >/dev/null 2>&1; then
  echo "Updating allowed HTTP methods via yc..."
  yc cdn resource update "$RESOURCE_ID" \
    --allowed-http-methods GET,HEAD,OPTIONS,POST
  echo "Done. Wait ~15 min, then test POST to /session/preview."
else
  echo "yc CLI not found. Enable POST in Yandex Cloud console (see script header)."
  exit 1
fi
