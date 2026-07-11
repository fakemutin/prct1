#!/usr/bin/env bash
# SCLUBvpn: rollback 502 + enable Happ iOS announce (JSON + plain announce header)
# Run on VPS as root: bash scripts/sclubvpn-fix-ios-announce.sh

set -euo pipefail

ANNOUNCE=$'– Реферальная система SCLUBvpn –\n💸 Получай 25% с каждой продажи! Пригласи 4 человек и получи бесплатный доступ.'
SUPPORT_URL='https://t.me/SaleClubVpnBot'
TEST_UUID='KsBo-X23wXaVktZM'
IOS_UA='Happ/4.12.0/ios/2606121423635'

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

psql() {
  docker exec remnawave-db psql -U postgres -d postgres -v ON_ERROR_STOP=1 "$@"
}

flush_cache() {
  log 'Flushing Redis cache...'
  docker exec remnawave-redis valkey-cli -s /var/run/valkey/valkey.sock FLUSHALL >/dev/null
}

rollback_broken_state() {
  log 'Rolling back broken config (502)...'

  psql -c "UPDATE hosts SET server_description = NULL WHERE uuid IN (
    '373bec64-a450-4477-bae4-3e6510992768',
    '93c4b867-3568-4bf2-9870-73945ba49460'
  );"

  psql -c "UPDATE subscription_settings SET
    serve_json_at_base_subscription = false,
    happ_announce = \$ann\$${ANNOUNCE}\$ann\$,
    custom_response_headers = '{\"support-url\": \"${SUPPORT_URL}\", \"profile-web-page-url\": \"${SUPPORT_URL}\"}'::jsonb
  WHERE uuid = '00000000-0000-0000-0000-000000000000';"
}

apply_ios_srr_rule() {
  log 'Inserting Happ iOS SRR rule before Fallback Base64...'

  docker exec -i remnawave-db psql -U postgres -d postgres -v ON_ERROR_STOP=1 <<'SQL'
CREATE TEMP TABLE sclub_rules_patch(rules jsonb);

INSERT INTO sclub_rules_patch(rules)
SELECT response_rules->'rules'
FROM subscription_settings
WHERE uuid = '00000000-0000-0000-0000-000000000000';

DO $$
DECLARE
  rules jsonb;
  ios_rule jsonb;
  cleaned jsonb := '[]'::jsonb;
  elem jsonb;
  fallback jsonb;
BEGIN
  SELECT rules INTO rules FROM sclub_rules_patch LIMIT 1;

  ios_rule := jsonb_build_object(
    'name', 'Happ iOS',
    'description', 'JSON subscription + plain announce for Happ on iOS',
    'enabled', true,
    'operator', 'AND',
    'conditions', jsonb_build_array(
      jsonb_build_object(
        'caseSensitive', false,
        'headerName', 'user-agent',
        'operator', 'REGEX',
        'value', '(?i)happ.*ios'
      )
    ),
    'responseType', 'XRAY_JSON',
    'responseModifications', jsonb_build_object(
      'applyHeadersToEnd', true,
      'headers', jsonb_build_array(
        jsonb_build_object(
          'key', 'announce',
          'value', E'– Реферальная система SCLUBvpn –\n💸 Получай 25% с каждой продажи! Пригласи 4 человек и получи бесплатный доступ.'
        ),
        jsonb_build_object('key', 'support-url', 'value', 'https://t.me/SaleClubVpnBot'),
        jsonb_build_object('key', 'profile-web-page-url', 'value', 'https://t.me/SaleClubVpnBot')
      )
    )
  );

  FOR elem IN SELECT value FROM jsonb_array_elements(rules)
  LOOP
    IF elem->>'name' = 'Happ iOS' THEN
      CONTINUE;
    END IF;
    IF elem->>'name' = 'Fallback Base64' THEN
      fallback := elem;
      CONTINUE;
    END IF;
    cleaned := cleaned || jsonb_build_array(elem);
  END LOOP;

  IF fallback IS NULL THEN
    RAISE EXCEPTION 'Fallback Base64 rule not found';
  END IF;

  rules := cleaned || jsonb_build_array(ios_rule) || jsonb_build_array(fallback);

  UPDATE subscription_settings
  SET response_rules = jsonb_set(response_rules, '{rules}', rules)
  WHERE uuid = '00000000-0000-0000-0000-000000000000';
END $$;
SQL
}

restart_stack() {
  log 'Restarting subscription stack...'
  cd /opt/remnawave
  docker compose restart caddy 2>/dev/null || true
  docker compose ps --format '{{.Name}}' | while read -r name; do
    case "$name" in
      *subscription*|remnawave|caddy)
        docker compose restart "$name" 2>/dev/null || docker restart "$name" 2>/dev/null || true
        ;;
    esac
  done
  sleep 6
}

verify() {
  log 'Verifying iOS Happ subscription...'
  local headers status ctype announce

  headers=$(curl -sS -D - -o /dev/null -A "$IOS_UA" "https://sub.sclubvpn.xyz/${TEST_UUID}" 2>&1 || true)
  status=$(printf '%s' "$headers" | awk 'toupper($1) ~ /^HTTP/ {print $2; exit}')
  ctype=$(printf '%s' "$headers" | awk -F': ' 'tolower($1)=="content-type" {print $2; exit}' | tr -d '\r')
  announce=$(printf '%s' "$headers" | awk -F': ' 'tolower($1)=="announce" {print $2; exit}' | tr -d '\r')

  log "HTTP status: ${status:-unknown}"
  log "Content-Type: ${ctype:-unknown}"
  log "announce: ${announce:-<missing>}"

  [[ "${status:-}" == "200" ]] || { log 'FAIL: not HTTP 200'; return 1; }
  [[ "$ctype" == application/json* ]] || { log 'FAIL: expected application/json'; return 1; }
  [[ -n "${announce:-}" && "$announce" != base64:* ]] || { log 'FAIL: plain announce header required for iOS'; return 1; }
  log 'Verification passed.'
}

main() {
  rollback_broken_state
  apply_ios_srr_rule
  flush_cache
  restart_stack
  verify
  log 'Done. Refresh subscription in Happ on iPhone.'
}

main "$@"
