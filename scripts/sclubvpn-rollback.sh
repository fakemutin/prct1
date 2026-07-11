#!/usr/bin/env bash
# SCLUBvpn: откат к РАБОЧЕМУ состоянию (до экспериментов с SRR/JSON)
# НЕ обнулять custom_response_headers — иначе profile-web-page-url ломает Happ!
# Run on VPS: bash scripts/sclubvpn-rollback.sh

set -euo pipefail

ANNOUNCE=$'– Реферальная система SCLUBvpn –\n💸 Получай 25% с каждой продажи! Пригласи 4 человек и получи бесплатный доступ.'
SUPPORT_URL='https://t.me/SaleClubVpnBot'
TEST_UUID='KsBo-X23wXaVktZM'

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

psql() {
  docker exec remnawave-db psql -U postgres -d postgres -v ON_ERROR_STOP=1 "$@"
}

rollback_hosts() {
  log 'Очистка server_description...'
  psql -c "UPDATE hosts SET server_description = NULL;"
}

rollback_subscription_settings() {
  log 'Восстановление рабочих subscription_settings...'
  psql -c "UPDATE subscription_settings SET
    serve_json_at_base_subscription = false,
    happ_announce = \$ann\$${ANNOUNCE}\$ann\$,
    happ_routing = NULL,
    custom_response_headers = '{\"support-url\": \"${SUPPORT_URL}\", \"profile-web-page-url\": \"${SUPPORT_URL}\"}'::jsonb
  WHERE uuid = '00000000-0000-0000-0000-000000000000';"
}

remove_experimental_srr_rules() {
  log 'Удаление SRR Happ iOS...'
  psql -c "UPDATE subscription_settings
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
      '[]'::jsonb
    )
  )
  WHERE uuid = '00000000-0000-0000-0000-000000000000';"
}

flush_cache() {
  log 'Очистка Redis...'
  docker exec remnawave-redis valkey-cli -s /var/run/valkey/valkey.sock FLUSHALL >/dev/null
}

restart_stack() {
  log 'Перезапуск контейнеров...'
  docker restart remnawave remnawave-subscription-page caddy 2>/dev/null || true
  sleep 22
}

verify() {
  log 'Проверка...'
  local status headers

  headers=$(curl -sI -A 'Happ/4.12.0/ios/2606121423635' "https://sub.sclubvpn.xyz/${TEST_UUID}")
  status=$(printf '%s' "$headers" | awk 'toupper($1) ~ /^HTTP/ {print $2; exit}')
  log "iOS -> HTTP ${status:-unknown}"

  printf '%s' "$headers" | grep -qi 'profile-web-page-url: https://t.me/SaleClubVpnBot' \
    && log 'profile-web-page-url OK' \
    || { log 'WARN: profile-web-page-url неверный'; return 1; }

  [[ "${status:-}" == "200" ]] || return 1
  log 'Подписка работает.'
}

main() {
  rollback_hosts
  rollback_subscription_settings
  remove_experimental_srr_rules
  flush_cache
  restart_stack
  verify
  log 'Откат к рабочему состоянию завершён.'
}

main "$@"
