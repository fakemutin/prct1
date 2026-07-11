#!/usr/bin/env bash
# SCLUBvpn: полный откат наших экспериментов (502/500)
# Запуск на VPS: bash /opt/remnawave/scripts/sclubvpn-rollback.sh

set -euo pipefail

ANNOUNCE=$'– Реферальная система SCLUBvpn –\n💸 Получай 25% с каждой продажи! Пригласи 4 человек и получи бесплатный доступ.'
SUPPORT_URL='https://t.me/SaleClubVpnBot'
TEST_UUID='KsBo-X23wXaVktZM'

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

psql() {
  docker exec remnawave-db psql -U postgres -d postgres -v ON_ERROR_STOP=1 "$@"
}

rollback_hosts() {
  log 'Очистка server_description на хостах...'
  psql -c "UPDATE hosts SET server_description = NULL WHERE uuid IN (
    '373bec64-a450-4477-bae4-3e6510992768',
    '93c4b867-3568-4bf2-9870-73945ba49460'
  );"
}

rollback_subscription_settings() {
  log 'Откат subscription_settings к рабочему состоянию...'
  psql -c "UPDATE subscription_settings SET
    serve_json_at_base_subscription = false,
    happ_announce = \$ann\$${ANNOUNCE}\$ann\$,
    custom_response_headers = '{\"support-url\": \"${SUPPORT_URL}\", \"profile-web-page-url\": \"${SUPPORT_URL}\"}'::jsonb
  WHERE uuid = '00000000-0000-0000-0000-000000000000';"
}

remove_experimental_srr_rules() {
  log 'Удаление экспериментальных SRR-правил (Happ iOS и др.)...'
  docker exec -i remnawave-db psql -U postgres -d postgres -v ON_ERROR_STOP=1 <<'SQL'
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
}

flush_cache() {
  log 'Очистка Redis...'
  docker exec remnawave-redis valkey-cli -s /var/run/valkey/valkey.sock FLUSHALL >/dev/null
}

restart_stack() {
  log 'Перезапуск контейнеров...'
  cd /opt/remnawave
  docker compose ps --format '{{.Name}}' | while read -r name; do
    case "$name" in
      *subscription*|remnawave|caddy|redis|db)
        docker compose restart "$name" 2>/dev/null || docker restart "$name" 2>/dev/null || true
        ;;
    esac
  done
  sleep 8
}

verify() {
  log 'Проверка подписки...'
  local headers status

  headers=$(curl -sS -D - -o /dev/null -A 'Mozilla/5.0' "https://sub.sclubvpn.xyz/${TEST_UUID}" 2>&1 || true)
  status=$(printf '%s' "$headers" | awk 'toupper($1) ~ /^HTTP/ {print $2; exit}')

  log "sub.sclubvpn.xyz -> HTTP ${status:-unknown}"
  [[ "${status:-}" == "200" ]] || {
    headers=$(curl -sS -D - -o /dev/null -A 'Mozilla/5.0' "https://panel.sclubvpn.xyz/api/sub/${TEST_UUID}" 2>&1 || true)
    status=$(printf '%s' "$headers" | awk 'toupper($1) ~ /^HTTP/ {print $2; exit}')
    log "panel api/sub -> HTTP ${status:-unknown}"
  }

  [[ "${status:-}" == "200" ]] || return 1
  log 'Подписка снова отвечает 200.'
}

main() {
  rollback_hosts
  rollback_subscription_settings
  remove_experimental_srr_rules
  flush_cache
  restart_stack
  verify
  log 'Откат завершён.'
}

main "$@"
