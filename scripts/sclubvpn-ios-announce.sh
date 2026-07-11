#!/usr/bin/env bash
# SCLUBvpn: iOS Happ — русский текст через base64 в HTTP-заголовках (JSON-ответ)
# Plain кириллица/emoji в заголовках даёт ERR_INVALID_CHAR; base64: — работает.
# Run on VPS as root: bash scripts/sclubvpn-ios-announce.sh

set -euo pipefail

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

log 'Applying Happ iOS SRR rule (Russian base64 headers)...'

ANNOUNCE_B64=$(printf '%s' $'– Реферальная система SCLUBvpn –\n💸 Получай 25% с каждой продажи! Пригласи 4 человек и получи бесплатный доступ.' | base64 -w0)
SUB_INFO_B64=$(printf '%s' 'Реф. 25% SCLUBvpn — пригласи 4 друга = бесплатно!' | base64 -w0)
BTN_TEXT_B64=$(printf '%s' 'Подробнее' | base64 -w0)

docker exec -i remnawave-db psql -U postgres -d postgres -v ON_ERROR_STOP=1 <<SQL
DO \$\$
DECLARE
  rules jsonb;
  ios_rule jsonb;
  cleaned jsonb := '[]'::jsonb;
  elem jsonb;
  fallback jsonb;
BEGIN
  SELECT response_rules->'rules' INTO rules FROM subscription_settings
  WHERE uuid = '00000000-0000-0000-0000-000000000000';

  ios_rule := jsonb_build_object(
    'name', 'Happ iOS',
    'enabled', true,
    'operator', 'AND',
    'conditions', jsonb_build_array(
      jsonb_build_object('caseSensitive', false, 'headerName', 'user-agent', 'operator', 'CONTAINS', 'value', 'happ'),
      jsonb_build_object('caseSensitive', false, 'headerName', 'user-agent', 'operator', 'CONTAINS', 'value', '/ios/')
    ),
    'responseType', 'XRAY_JSON',
    'responseModifications', jsonb_build_object(
      'applyHeadersToEnd', true,
      'headers', jsonb_build_array(
        jsonb_build_object('key', 'announce', 'value', 'base64:${ANNOUNCE_B64}'),
        jsonb_build_object('key', 'sub-info-text', 'value', 'base64:${SUB_INFO_B64}'),
        jsonb_build_object('key', 'sub-info-button-text', 'value', 'base64:${BTN_TEXT_B64}'),
        jsonb_build_object('key', 'sub-info-button-link', 'value', 'https://t.me/SaleClubVpnBot'),
        jsonb_build_object('key', 'announce-url', 'value', 'https://t.me/SaleClubVpnBot'),
        jsonb_build_object('key', 'support-url', 'value', 'https://t.me/SaleClubVpnBot'),
        jsonb_build_object('key', 'profile-web-page-url', 'value', 'https://t.me/SaleClubVpnBot')
      )
    )
  );

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
END \$\$;

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

log 'Done. iOS: JSON + base64 Russian headers; Windows: base64 links without serverDescription.'
