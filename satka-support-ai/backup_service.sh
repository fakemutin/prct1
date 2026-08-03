#!/bin/bash
# Full backup of Satka Support AI on the server.
set -euo pipefail

SERVICE_DIR="/opt/satka-support-ai"
BACKUP_ROOT="/opt/backups/satka-support-ai"
STAMP=$(date -u +%Y%m%d-%H%M%S)
BACKUP_DIR="${BACKUP_ROOT}/${STAMP}"
ARCHIVE="${BACKUP_ROOT}/satka-support-ai-full-${STAMP}.tar.gz"

mkdir -p "$BACKUP_DIR"

echo "[1/5] Copying service files..."
cp -a "$SERVICE_DIR" "$BACKUP_DIR/opt-satka-support-ai"

echo "[2/5] Saving Docker state..."
docker ps -a --filter name=satka_support_ai > "$BACKUP_DIR/docker-ps.txt" 2>&1 || true
docker logs satka_support_ai --tail 200 > "$BACKUP_DIR/docker-logs-tail.txt" 2>&1 || true
docker inspect satka_support_ai > "$BACKUP_DIR/docker-inspect.json" 2>&1 || true

echo "[3/5] Writing manifest..."
cat > "$BACKUP_DIR/MANIFEST.txt" <<EOF
Satka Support AI — full backup
Created (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)
Host: $(hostname)
Service path: ${SERVICE_DIR}

Contents:
- opt-satka-support-ai/  (code, .env, sessions/, docker-compose)
- docker-ps.txt
- docker-logs-tail.txt
- docker-inspect.json
- RESTORE.md

Restore: see RESTORE.md
EOF

cat > "$BACKUP_DIR/RESTORE.md" <<'EOF'
# Restore Satka Support AI

```bash
cd /opt
systemctl stop satka-support-ai 2>/dev/null || true
docker compose -f /opt/satka-support-ai/docker-compose.yml down 2>/dev/null || true

# from extracted backup folder:
cp -a opt-satka-support-ai /opt/satka-support-ai

cd /opt/satka-support-ai
docker compose up -d --build --force-recreate
docker logs satka_support_ai --tail 30
```

Sessions in `sessions/` — keep them to stay logged in as @satkavpnsupport.
EOF

echo "[4/5] Creating archive..."
tar -czf "$ARCHIVE" -C "$BACKUP_ROOT" "$STAMP"

echo "[5/5] Cleanup temp dir, keep archive only..."
rm -rf "$BACKUP_DIR"

ls -lh "$ARCHIVE"
echo "BACKUP_PATH=$ARCHIVE"
sha256sum "$ARCHIVE"

# keep last 10 backups
ls -1t "${BACKUP_ROOT}"/satka-support-ai-full-*.tar.gz 2>/dev/null | tail -n +11 | xargs -r rm -f

echo "Done."
