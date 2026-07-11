#!/usr/bin/env bash
# SCLUBvpn: стабильная конфигурация Happ (iOS/Android/Windows)
# Русский текст ТОЛЬКО через happ_announce (Remnawave сам кодирует в base64).
# НЕ добавлять announce/sub-info в custom_response_headers — ломает импорт в Happ iOS!
# Run on VPS as root: bash scripts/sclubvpn-ios-announce.sh

set -euo pipefail

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

log 'Applying stable Happ config (base64 links + happ_announce)...'

docker exec -i remnawave-db psql -U postgres -d postgres -v ON_ERROR_STOP=1 <<'SQL'
UPDATE hosts SET server_description = NULL WHERE uuid IN (
  '373bec64-a450-4477-bae4-3e6510992768',
  '93c4b867-3568-4bf2-9870-73945ba49460'
);

UPDATE subscription_settings SET
  serve_json_at_base_subscription = false,
  happ_announce = E'– Реферальная система SCLUBvpn –\n💸 Получай 25% с каждой продажи! Пригласи 4 человек и получи бесплатный доступ.',
  custom_response_headers = '{"support-url": "https://t.me/SaleClubVpnBot", "profile-web-page-url": "https://t.me/SaleClubVpnBot"}'::jsonb
WHERE uuid = '00000000-0000-0000-0000-000000000000';

UPDATE subscription_settings
SET response_rules = jsonb_set(
  response_rules,
  '{rules}',
  COALESCE(
    (
      SELECT jsonb_agg(elem ORDER BY ord)
      FROM (
        SELECT elem, row_number() OVER () AS ord
        FROM jsonb_array_elements(response_rules->'rules') AS elem
        WHERE elem->>'name' NOT IN ('Happ iOS', 'Happ iOS Announce')
      ) q
    ),
    response_rules->'rules'
  )
)
WHERE uuid = '00000000-0000-0000-0000-000000000000';
SQL

docker exec remnawave-redis valkey-cli -s /var/run/valkey/valkey.sock FLUSHALL >/dev/null
cd /opt/remnawave
docker restart remnawave remnawave-subscription-page caddy 2>/dev/null || true
sleep 20

log 'Done. Base64 подписка + announce из happ_announce (русский, base64 в заголовке).'
