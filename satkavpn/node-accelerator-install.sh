#!/bin/bash
# SatkaVPN: backup + install node-accelerator on Remnawave node
set -euo pipefail

NA_REF="${NA_REF:-v3.9.2}"
BACKUP_ROOT="/opt/backups"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="${BACKUP_ROOT}/pre-node-accelerator-${STAMP}"
INSTALL_DIR="/opt/node-accelerator"
LOG="/var/log/node-accelerator-install-${STAMP}.log"

exec > >(tee -a "$LOG") 2>&1

echo "=== SatkaVPN node-accelerator install @ ${STAMP} ==="

mkdir -p "$BACKUP_DIR"

echo "--- Phase 1: backup ---"
nft list ruleset > "${BACKUP_DIR}/nft-ruleset.txt" 2>&1 || true
iptables-save > "${BACKUP_DIR}/iptables.txt" 2>&1 || true
ip6tables-save > "${BACKUP_DIR}/ip6tables.txt" 2>&1 || true
sysctl -a > "${BACKUP_DIR}/sysctl-all.txt" 2>&1 || true
ss -tulnp > "${BACKUP_DIR}/listening-ports.txt" 2>&1 || true
docker ps -a > "${BACKUP_DIR}/docker-ps.txt" 2>&1 || true
crontab -l > "${BACKUP_DIR}/crontab-root.txt" 2>&1 || true
cp -a /etc/ssh/sshd_config "${BACKUP_DIR}/sshd_config" 2>/dev/null || true
cp -a /etc/ssh/sshd_config.d "${BACKUP_DIR}/" 2>/dev/null || true

tar czf "${BACKUP_DIR}/opt-configs.tar.gz" \
  --ignore-failed-read \
  /opt/bedolaga/docker-compose.yml \
  /opt/bedolaga/cabinet-compose.yml \
  /opt/bedolaga/.env \
  /opt/bedolaga/custom \
  /opt/remnawave \
  /opt/remnanode \
  /opt/caddy \
  /opt/satkavpn/docker-compose-happ.yml \
  /opt/satkavpn/happ_merge.py \
  /opt/satka-support-ai/docker-compose.yml \
  2>/dev/null || true

if [ -d /etc/node-accelerator ]; then
  tar czf "${BACKUP_DIR}/etc-node-accelerator.tar.gz" /etc/node-accelerator 2>/dev/null || true
fi

echo "Backup saved to ${BACKUP_DIR}"
ls -lah "${BACKUP_DIR}"

echo "--- Phase 2: fetch node-accelerator ${NA_REF} ---"
rm -rf "${INSTALL_DIR}.tmp"
git clone --depth 1 --branch "${NA_REF}" https://github.com/jestivald/node-accelerator.git "${INSTALL_DIR}.tmp"
rm -rf "${INSTALL_DIR}"
mv "${INSTALL_DIR}.tmp" "${INSTALL_DIR}"

echo "--- Phase 3: diagnose (read-only) ---"
bash "${INSTALL_DIR}/install.sh" diagnose || true

echo "--- Phase 4: protect (firewall + CrowdSec) ---"
# Combined panel+node: Caddy 80/443, Xray 2053, socat 15443, node-agent 2222
export SSH_PORT=22
export TCP_PORTS=80,443,2053,15443
export UDP_PORTS=443
export NODE_PORT=2222
export WHITELIST="127.0.0.1,::1,13.143.130.10,2a10:ab80:3fd:82::2"
export FLEET_SYNC=0
export REMNAWAVE_NONINTERACTIVE=1
export FW_MODE=strict
bash "${INSTALL_DIR}/scripts/protect.sh"

echo "--- Phase 5: optimize (sysctl; XanMod may require reboot) ---"
export REMNAWAVE_NONINTERACTIVE=1
bash "${INSTALL_DIR}/scripts/optimize.sh"

echo "--- Phase 6: post-check ---"
command -v na-diagnose >/dev/null && na-diagnose || true
command -v na-fw-status >/dev/null && na-fw-status || true

echo "=== DONE ==="
echo "Backup: ${BACKUP_DIR}"
echo "Log: ${LOG}"
if uname -r | grep -qi xanmod; then
  echo "Kernel already XanMod — OK"
else
  echo "NOTE: reboot required for XanMod/BBRv3: uname -r -> $(uname -r)"
fi
