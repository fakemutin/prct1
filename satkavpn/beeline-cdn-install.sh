#!/usr/bin/env bash
# NazuSetup-style installer: Caddy + заглушка + туннель к remnanode (XHTTP).
# Запуск на VPS под root: bash beeline-cdn-install.sh
set +H
set -e

B="\033[1m"; G="\033[32m"; Y="\033[33m"; R="\033[31m"; N="\033[0m"
say(){ printf "%b\n" "$1"; }

say "${B}=== SatkaVPN: Beeline CDN origin (Caddy) ===${N}"

if [ "$(id -u)" != "0" ]; then
  say "${R}Нужны права root. Выполни: sudo -i${N}"
  exit 1
fi

while :; do
  read -rp "1/3 Почта для SSL (Let's Encrypt): " EMAIL </dev/tty
  case "$EMAIL" in *?@?*.?*) break ;; *) say "${Y}Пример: admin@example.com${N}" ;; esac
done

while :; do
  read -rp "2/3 Домен НОДЫ (A-запись на этот VPS, без https): " DOMAIN </dev/tty
  DOMAIN="$(printf '%s' "$DOMAIN" | tr -d ' \t\r' | sed -e 's#^https\?://##' -e 's#/.*$##')"
  case "$DOMAIN" in *.?*) break ;; *) say "${Y}Пример: wl-1.satkaconnect.xyz${N}" ;; esac
done

read -rp "3/3 Порт инбаунда remnanode [Enter = 7443]: " NODEPORT </dev/tty
NODEPORT="${NODEPORT:-7443}"

say ""
say "${B}Проверка...${N}"
say "  почта      : $EMAIL"
say "  домен ноды : $DOMAIN"
say "  порт ноды  : $NODEPORT"
say ""

apt-get update -y >/dev/null 2>&1 || true
apt-get install -y curl dnsutils ca-certificates >/dev/null 2>&1 || true

MYIP="$(curl -s4 --max-time 10 https://api.ipify.org || true)"
DNSIP="$(dig +short A "$DOMAIN" @1.1.1.1 | tail -n1)"
say "IP сервера        : ${MYIP:-?}"
say "A-запись домена   : ${DNSIP:-нет}"

if [ -z "$DNSIP" ]; then
  say "${R}СТОП: нет A-записи. Сначала DNS, потом этот скрипт.${N}"
  exit 1
fi
if [ -n "$MYIP" ] && [ "$DNSIP" != "$MYIP" ]; then
  say "${R}СТОП: $DOMAIN -> $DNSIP, а VPS = $MYIP${N}"
  say "${Y}Исправь A-запись или выключи Cloudflare proxy (DNS only).${N}"
  exit 1
fi

BUSY="$(ss -tlnp 2>/dev/null | awk '{print $4}' | grep -E ':(80|443)$' || true)"
if [ -n "$BUSY" ]; then
  OWNER="$(ss -tlnp 2>/dev/null | grep -E ':(80|443)\s' | head -n2)"
  if printf '%s' "$OWNER" | grep -q caddy; then
    say "${Y}Порты 80/443 заняты Caddy — перенастрою.${N}"
  else
    say "${R}СТОП: 80 или 443 занят не Caddy:${N}"
    printf '%s\n' "$OWNER"
    exit 1
  fi
fi

if ! command -v caddy >/dev/null 2>&1; then
  say "${B}Устанавливаю Caddy...${N}"
  apt-get install -y debian-keyring debian-archive-keyring apt-transport-https gnupg >/dev/null
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    >/etc/apt/sources.list.d/caddy-stable.list
  apt-get update -y >/dev/null
  apt-get install -y caddy >/dev/null
fi

W1=(assets static media data core files public cdn)
W2=(data img cache track pixel feed api sync)
V=(v1 v2 v3 v4 v6)
X=(php js json aspx)
TP="/${W1[$((RANDOM % ${#W1[@]}))]}/${W2[$((RANDOM % ${#W2[@]}))]}/${V[$((RANDOM % ${#V[@]}))]}/$(openssl rand -hex 3).${X[$((RANDOM % ${#X[@]}))]}"

mkdir -p /var/www/html
if [ ! -f /var/www/html/index.html ]; then
  cat >/var/www/html/index.html <<'HTMLEOF'
<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"><title>Доступ</title></head>
<body style="font-family:sans-serif;text-align:center;padding:40px"><h1>Вход</h1>
<p>Авторизация на сервере</p></body></html>
HTMLEOF
fi

mkdir -p /etc/caddy
BAK=""
if [ -f /etc/caddy/Caddyfile ]; then
  BAK="/etc/caddy/Caddyfile.bak-$(date +%Y%m%d-%H%M%S)"
  cp -a /etc/caddy/Caddyfile "$BAK"
  say "Бэкап: $BAK"
fi

cat >/etc/caddy/Caddyfile <<EOF
{
	email $EMAIL
	servers {
		protocols h1 h2
	}
}

$DOMAIN {
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
if ! caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/tmp/caddy-val.log 2>&1; then
  say "${R}Ошибка Caddyfile:${N}"
  cat /tmp/caddy-val.log
  [ -n "$BAK" ] && cp -a "$BAK" /etc/caddy/Caddyfile
  exit 1
fi

systemctl enable caddy >/dev/null 2>&1 || true
systemctl restart caddy
sleep 3

if ! systemctl is-active --quiet caddy; then
  say "${R}Caddy не запустился:${N}"
  journalctl -u caddy --since "2 min ago" --no-pager | tail -n 20
  exit 1
fi

cat >/root/beeline-cdn-info.txt <<EOF
Домен ноды (источник в Beeline) : $DOMAIN
Порт инбаунда remnanode         : $NODEPORT
Путь туннеля                    : $TP
Проверка                        : https://$DOMAIN$TP?auth=1
Создано                         : $(date -Iseconds)
EOF

say ""
say "${G}${B}ГОТОВО${N}"
say "Путь туннеля: ${Y}$TP${N}"
say "Файл: /root/beeline-cdn-info.txt"
say "Пришли мне содержимое этого файла + тех-домен из Beeline."
