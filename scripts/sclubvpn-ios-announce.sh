#!/usr/bin/env bash
# SCLUBvpn: iOS Happ description via SRR (JSON + plain announce header)
# Run on VPS as root: bash scripts/sclubvpn-ios-announce.sh

set -euo pipefail

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

log 'Applying Happ iOS SRR rule...'

docker exec -i remnawave-db psql -U postgres -d postgres -v ON_ERROR_STOP=1 <<'SQL'
DO $$
DECLARE
  rules jsonb;
  ios_rule jsonb;
  cleaned jsonb := '[]'::jsonb;
  elem jsonb;
  fallback jsonb;
BEGIN
  SELECT response_rules->'rules' INTO rules FROM subscription_settings
  WHERE uuid = '00000000-0000-0000-0000-000000000000';

  ios_rule := '{
    "name": "Happ iOS",
    "description": "iOS Happ: JSON + plain announce",
    "enabled": true,
    "operator": "AND",
    "conditions": [
      {"caseSensitive": false, "headerName": "user-agent", "operator": "CONTAINS", "value": "happ"},
      {"caseSensitive": false, "headerName": "user-agent", "operator": "CONTAINS", "value": "/ios/"}
    ],
    "responseType": "XRAY_JSON",
    "responseModifications": {
      "applyHeadersToEnd": true,
      "headers": [
        {"key": "announce", "value": "Ref. 25% SCLUBvpn - priglasi 4 druzej = besplatno! @SaleClubVpnBot"},
        {"key": "announce-url", "value": "https://t.me/SaleClubVpnBot"},
        {"key": "support-url", "value": "https://t.me/SaleClubVpnBot"},
        {"key": "profile-web-page-url", "value": "https://t.me/SaleClubVpnBot"}
      ]
    }
  }'::jsonb;

  FOR elem IN SELECT value FROM jsonb_array_elements(rules)
  LOOP
    IF elem->>'name' IN ('Happ iOS', 'Happ iOS Announce') THEN CONTINUE; END IF;
    IF elem->>'name' = 'Fallback Base64' THEN fallback := elem; CONTINUE; END IF;
    cleaned := cleaned || jsonb_build_array(elem);
  END LOOP;

  UPDATE subscription_settings SET
    serve_json_at_base_subscription = false,
    happ_announce = E'– Реферальная система SCLUBvpn –\n💸 Получай 25% с каждой продажи! Пригласи 4 человек и получи бесплатный доступ.',
    custom_response_headers = '{"support-url": "https://t.me/SaleClubVpnBot", "profile-web-page-url": "https://t.me/SaleClubVpnBot"}'::jsonb,
    response_rules = jsonb_set(response_rules, '{rules}',
      cleaned || jsonb_build_array(ios_rule) || jsonb_build_array(fallback)
    )
  WHERE uuid = '00000000-0000-0000-0000-000000000000';
END $$;

UPDATE hosts SET server_description = NULL
WHERE uuid IN (
  '373bec64-a450-4477-bae4-3e6510992768',
  '93c4b867-3568-4bf2-9870-73945ba49460'
);
SQL

docker exec remnawave-redis valkey-cli -s /var/run/valkey/valkey.sock FLUSHALL >/dev/null
cd /opt/remnawave
docker compose restart remnawave remnawave-subscription-page caddy 2>/dev/null || {
  docker restart remnawave remnawave-subscription-page caddy
}
sleep 18

log 'Done. iOS should get JSON + plain announce; Windows keeps base64.'
