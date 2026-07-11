#!/usr/bin/env bash
# SCLUBvpn: ПОЛНЫЙ откат до состояния до всех экспериментов
# Запуск на VPS: bash scripts/sclubvpn-rollback.sh

set -euo pipefail

TEST_UUID='KsBo-X23wXaVktZM'

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

psql() {
  docker exec remnawave-db psql -U postgres -d postgres -v ON_ERROR_STOP=1 "$@"
}

rollback_hosts() {
  log 'Очистка server_description на всех хостах...'
  psql -c "UPDATE hosts SET server_description = NULL;"
}

rollback_subscription_settings() {
  log 'Полный откат subscription_settings...'
  psql -c "UPDATE subscription_settings SET
    serve_json_at_base_subscription = false,
    happ_announce = NULL,
    happ_routing = NULL,
    custom_response_headers = NULL
  WHERE uuid = '00000000-0000-0000-0000-000000000000';"
}

remove_experimental_srr_rules() {
  log 'Удаление экспериментальных SRR-правил...'
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
  log 'Перезапуск всех контейнеров...'
  for c in remnawave-db remnawave-redis remnawave remnawave-subscription-page caddy; do
    docker restart "$c" 2>/dev/null || true
  done
  sleep 25
}

verify() {
  log 'Проверка подписки...'
  local status

  status=$(curl -s -o /dev/null -w '%{http_code}' -A 'Happ/4.12.0/ios/2606121423635' "https://sub.sclubvpn.xyz/${TEST_UUID}")
  log "iOS Happ -> HTTP ${status}"
  [[ "$status" == "200" ]] || return 1

  status=$(curl -s -o /dev/null -w '%{http_code}' -A 'Happ/4.12.0/windows/123' "https://sub.sclubvpn.xyz/${TEST_UUID}")
  log "Windows Happ -> HTTP ${status}"
  [[ "$status" == "200" ]] || return 1

  log 'Подписка отвечает 200 на iOS и Windows.'
}

main() {
  rollback_hosts
  rollback_subscription_settings
  remove_experimental_srr_rules
  flush_cache
  restart_stack
  verify
  log 'Полный откат завершён. happ_announce и custom_response_headers = NULL.'
}

main "$@"
