#!/usr/bin/env bash
# Non-interactive Beeline CDN origin (Caddy) for NL node with existing nginx SNI on :443.
# Usage (on server as root):
#   DOMAIN=nl-bee.satkaconnect.xyz EMAIL=admin@satkaconnect.xyz bash beeline-cdn-deploy-nl.sh
set +H
set -euo pipefail

DOMAIN="${DOMAIN:-nl-bee.satkaconnect.xyz}"
EMAIL="${EMAIL:-admin@satkaconnect.xyz}"
NODEPORT="${NODEPORT:-7443}"
NGINX_STREAM="/etc/nginx/nginx.conf"

say() { printf '%s\n' "$*"; }

if [ "$(id -u)" != "0" ]; then
  say "Run as root"
  exit 1
fi

apt-get update -y >/dev/null 2>&1 || true
apt-get install -y curl dnsutils ca-certificates >/dev/null 2>&1 || true

MYIP="$(curl -s4 --max-time 10 https://api.ipify.org || true)"
DNSIP="$(dig +short A "$DOMAIN" @1.1.1.1 | tail -n1)"
say "Server IP : ${MYIP:-?}"
say "DNS A     : ${DNSIP:-<not set yet>}"

if [ -n "$MYIP" ] && [ -n "$DNSIP" ] && [ "$DNSIP" != "$MYIP" ]; then
  say "WARNING: $DOMAIN points to $DNSIP, expected $MYIP"
  say "Fix DNS (gray cloud / DNS only) before expecting a valid certificate."
fi

# Free :80 for ACME — landing page is optional on this node.
if docker ps --format '{{.Names}}' | grep -qx satkavpn-web; then
  say "Stopping satkavpn-web on :80 (can restart later on another port)."
  docker stop satkavpn-web >/dev/null || true
fi

if ! command -v caddy >/dev/null 2>&1; then
  say "Installing Caddy..."
  apt-get install -y debian-keyring debian-archive-keyring apt-transport-https gnupg >/dev/null
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    >/etc/apt/sources.list.d/caddy-stable.list
  apt-get update -y >/dev/null
  apt-get install -y caddy >/dev/null
fi

TP="${TUNNEL_PATH:-}"
if [ -z "$TP" ]; then
W1=(assets static media data core files public cdn)
W2=(data img cache track pixel feed api sync)
V=(v1 v2 v3 v4 v6)
X=(php js json aspx)
w1="${W1[$((RANDOM % 7))]}"
w2="${W2[$((RANDOM % 8))]}"
ver="${V[$((RANDOM % 5))]}"
ext="${X[$((RANDOM % 4))]}"
TP="/${w1}/${w2}/${ver}/$(openssl rand -hex 3).${ext}"
fi

mkdir -p /var/www/html
if [ ! -f /var/www/html/index.html ]; then
  cat >/var/www/html/index.html <<'HTMLEOF'
<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"><title>Доступ</title></head>
<body style="font-family:sans-serif;text-align:center;padding:40px"><h1>Вход</h1>
<p>Авторизация на сервере</p></body></html>
HTMLEOF
fi

mkdir -p /etc/caddy
if [ -f /etc/caddy/Caddyfile ]; then
  cp -a /etc/caddy/Caddyfile "/etc/caddy/Caddyfile.bak-$(date +%Y%m%d-%H%M%S)"
fi

cat >/etc/caddy/Caddyfile <<EOF
{
	email $EMAIL
	auto_https disable_redirects
	servers {
		protocols h1 h2
	}
}

https://$DOMAIN:9443 {
	bind 127.0.0.1
	@tunnel {
		path $TP*
		query auth=*
	}
	handle @tunnel {
		reverse_proxy 127.0.0.1:$NODEPORT
	}
	handle /health {
		respond "ok" 200
	}
	handle {
		root * /var/www/html
		file_server
	}
}
EOF

caddy fmt --overwrite /etc/caddy/Caddyfile >/dev/null 2>&1 || true
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile

# Route Beeline origin SNI through existing nginx stream multiplexer.
if [ -f "$NGINX_STREAM" ] && ! grep -q "$DOMAIN" "$NGINX_STREAM"; then
  say "Patching nginx stream SNI map for $DOMAIN -> 127.0.0.1:9443"
  cp -a "$NGINX_STREAM" "${NGINX_STREAM}.bak-$(date +%Y%m%d-%H%M%S)"
  python3 - "$DOMAIN" "$NGINX_STREAM" <<'PY'
import sys
from pathlib import Path

domain, path = sys.argv[1], Path(sys.argv[2])
text = path.read_text()
needle = "    map $ssl_preread_server_name $upstream {"
insert = f"        {domain}              caddy_ssl;\n"
upstream = "\n    upstream caddy_ssl {\n        server 127.0.0.1:9443;\n    }\n"
if needle not in text:
    raise SystemExit("nginx stream map not found")
if insert.strip() not in text:
    text = text.replace(needle, needle + "\n" + insert, 1)
if "upstream caddy_ssl" not in text:
    text = text.replace("\n    upstream web_ssl {", upstream + "\n    upstream web_ssl {", 1)
path.write_text(text)
PY
  nginx -t
  systemctl reload nginx
fi

systemctl enable caddy >/dev/null 2>&1 || true
systemctl restart caddy
sleep 3

if ! systemctl is-active --quiet caddy; then
  journalctl -u caddy --since "2 min ago" --no-pager | tail -n 30
  exit 1
fi

cat >/root/beeline-cdn-info.txt <<EOF
=== Beeline CDN origin (NL / 2.26.96.26) ===
Origin domain (источник в Beeline CDN) : $DOMAIN
IP origin (A-запись, DNS only)         : $MYIP
Порт remnanode XHTTP inbound           : $NODEPORT
Путь туннеля (Rewrite + Xray + Host)   : $TP
Rewrite в Beeline CDN                  : ${TP}/ -> ${TP%/}
Проверка заглушки                      : https://$DOMAIN/
Проверка туннеля                       : https://$DOMAIN$TP?auth=test
Создано                                : $(date -Iseconds)

DNS в Cloudflare (satkaconnect.xyz):
  Тип: A
  Имя: ${DOMAIN%%.satkaconnect.xyz}
  Значение: $MYIP
  Proxy: ВЫКЛ (серое облако / DNS only)

В Beeline CDN (ресурс):
  Источник: $DOMAIN:443
  HTTPS к источнику: ВКЛ
  SNI / Hostname: $DOMAIN
  Rewrite: ${TP}/ -> ${TP%/}
EOF

cat /root/beeline-cdn-info.txt
