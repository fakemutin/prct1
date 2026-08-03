#!/bin/bash
# SatkaVPN VPS tune — reduce load without touching core services (bot, panel, cabinet, VPN).
set -euo pipefail

echo "=== Satka VPS tune $(date -Is) ==="

# 1. Stop crash-looping tg-parser mirror (wastes CPU every 15s)
if systemctl is-active tg-parser-mirror.service &>/dev/null; then
  echo "Disabling tg-parser-mirror (crash loop)..."
  systemctl stop tg-parser-mirror.service
  systemctl disable tg-parser-mirror.service
fi

# 2. Trim journal logs
echo "Vacuuming journal to 80M..."
journalctl --vacuum-size=80M || true

# 3. Docker build cache prune (safe)
echo "Pruning docker build cache..."
docker builder prune -f 2>/dev/null || true
docker image prune -f 2>/dev/null || true

# 4. PostgreSQL memory tune (2GB VPS — lower shared_buffers)
for c in bedolaga-db remnawave-db; do
  if docker ps --format '{{.Names}}' | grep -qx "$c"; then
    echo "Tuning $c PostgreSQL memory..."
    docker exec "$c" psql -U postgres -c "ALTER SYSTEM SET shared_buffers = '64MB';" 2>/dev/null || \
      docker exec "$c" psql -U postgres -d postgres -c "ALTER SYSTEM SET shared_buffers = '64MB';" 2>/dev/null || true
    docker exec "$c" psql -U postgres -c "ALTER SYSTEM SET work_mem = '2MB';" 2>/dev/null || \
      docker exec "$c" psql -U postgres -d postgres -c "ALTER SYSTEM SET work_mem = '2MB';" 2>/dev/null || true
    docker exec "$c" psql -U postgres -c "ALTER SYSTEM SET maintenance_work_mem = '32MB';" 2>/dev/null || \
      docker exec "$c" psql -U postgres -d postgres -c "ALTER SYSTEM SET maintenance_work_mem = '32MB';" 2>/dev/null || true
  fi
done

# 5. Swappiness — prefer RAM for active services
if [ -f /proc/sys/vm/swappiness ]; then
  echo 10 > /proc/sys/vm/swappiness
  grep -q '^vm.swappiness' /etc/sysctl.d/99-satka-tune.conf 2>/dev/null || \
    echo 'vm.swappiness=10' >> /etc/sysctl.d/99-satka-tune.conf
fi

# 6. Drop caches once (frees pagecache, not app data)
sync
echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true

echo "=== Before restart ==="
free -h
uptime

# Restart DB containers to apply PG settings (brief downtime on DB only)
for c in bedolaga-db remnawave-db; do
  if docker ps --format '{{.Names}}' | grep -qx "$c"; then
    echo "Restarting $c..."
    docker restart "$c"
    sleep 3
  fi
done

echo "=== After tune ==="
free -h
uptime
docker stats --no-stream 2>/dev/null | head -15
echo "Done."
