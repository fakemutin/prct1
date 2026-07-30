#!/usr/bin/env python3
"""Единая подписка SATKAVPN + candelix с нумерацией серверов."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import re
import urllib.request
from urllib.parse import parse_qs, quote, unquote
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

CANDELIX_URL = os.environ.get("CANDELIX_URL", "https://sub.cndlx.sbs/ZAL6csH9NAU-bQCr")
CANDELIX_HWID = os.environ.get("CANDELIX_HWID", "42904ae198c3e4dc")
WHITELIST_URL = os.environ.get(
    "WHITELIST_URL", "https://vpn.sinful.click/Kq-b55QHrmdcxNfm"
)
# Платная подписка: static | candelix | sinful (бесплатные extras остаются на sinful)
PAID_WHITELIST_SOURCE = os.environ.get("PAID_WHITELIST_SOURCE", "static").lower()
WHITELIST_VLESS_FILE = os.environ.get(
    "WHITELIST_VLESS_FILE", "/app/whitelist-vless.json"
)
FREE_VPN_URL = os.environ.get("FREE_VPN_URL", WHITELIST_URL)
SUB_INTERNAL = os.environ.get("SUB_INTERNAL", "http://remnawave-subscription-page:3010")
SUB_HOST = os.environ.get("SUB_HOST", "sub.satkaconnect.xyz")
REMNAWAVE_PANEL_URL = os.environ.get(
    "REMNAWAVE_PANEL_URL", "https://panel.satkaconnect.xyz"
).rstrip("/")
REMNAWAVE_API_TOKEN = os.environ.get("REMNAWAVE_API_TOKEN", "")
# Опционально: postgres bedolaga для авто-маршрута free/trial по старым ключам без /free
BEDOLAGA_DATABASE_URL = os.environ.get("BEDOLAGA_DATABASE_URL", "")
FREE_TOKENS_FILE = os.environ.get("FREE_TOKENS_FILE", "")
TARIFF_FREE_ID = int(os.environ.get("TARIFF_FREE_ID", "6"))
TARIFF_WHITELIST_ID = int(os.environ.get("TARIFF_WHITELIST_ID", "5"))
TARIFF_MOM_ID = int(os.environ.get("TARIFF_MOM_ID", "7"))
REMNAWAVE_WHITELIST_SQUAD = os.environ.get(
    "REMNAWAVE_WHITELIST_SQUAD", "whitelist"
).lower()
LOCATIONS_FILE = os.environ.get(
    "LOCATIONS_FILE", str(Path(__file__).with_name("locations-order.json"))
)
PROXY_GROUP = os.environ.get("PROXY_GROUP", "🛰 SatkaVPN")
BRIDGE_SERVER = os.environ.get("BRIDGE_SERVER", "144.31.61.185")
BRIDGE_PORT = int(os.environ.get("BRIDGE_PORT", "443"))
BRIDGE_NAME = os.environ.get("BRIDGE_NAME", "🌉 Мост RU")
BRIDGE_INTERNAL_NAME = os.environ.get("BRIDGE_INTERNAL_NAME", "_satka_bridge")
# Публичный fallback через reverse-туннель на панели (если RU:443 недоступен)
BRIDGE_FALLBACK_SERVER = os.environ.get("BRIDGE_FALLBACK_SERVER", "")
BRIDGE_FALLBACK_PORT = int(os.environ.get("BRIDGE_FALLBACK_PORT", "0") or "0")
# Токен Remnawave для шаблона моста в бесплатной подписке (если нет в URL)
FREE_BRIDGE_TEMPLATE_TOKEN = os.environ.get("FREE_BRIDGE_TEMPLATE_TOKEN", "")

# LTE: мост и TCP-релей на одном IP (Германия) — второй прыжок через локальные порты
NATIVE_LTE_BRIDGE = os.environ.get("NATIVE_LTE_BRIDGE", "81.90.25.134")
RELAY_HOST = os.environ.get("RELAY_HOST", NATIVE_LTE_BRIDGE)
# native_key -> локальный порт на RELAY_HOST (socat -> backend)
NATIVE_RELAY_PORTS = {
    "Финляндия": 3101,
    "Финляндия 2": 3105,
    "Швеция": 3102,
    "Германия": 3103,
    "Польша": 3104,
    "Нидерланды 2": 3106,
}
# native_key -> candelix country for stream tuning
NATIVE_CANDELIX_REF = {
    "Финляндия": "Финляндия",
    "Финляндия 2": "Финляндия",
    "Швеция": "Швеция",
    "Германия": "Германия",
    "Польша": "Польша",
    "Нидерланды 2": "Нидерланды",
}
# Скрытый exit для P2P на whitelist (sinful не видит торрент-трафик)
TORRENT_STEALTH_TAG = os.environ.get("TORRENT_STEALTH_TAG", "satka-x")
TORRENT_EXIT_NATIVE_KEYS = tuple(
    k.strip()
    for k in os.environ.get(
        "TORRENT_EXIT_NATIVE_KEYS", "Германия,Нидерланды 2,Польша,Финляндия"
    ).split(",")
    if k.strip()
)
TORRENT_EXIT_TEMPLATE_TOKEN = os.environ.get(
    "TORRENT_EXIT_TEMPLATE_TOKEN", FREE_BRIDGE_TEMPLATE_TOKEN
)
# Типичные порты BitTorrent — на случай если клиент не помечает protocol
TORRENT_STEALTH_PORTS = os.environ.get(
    "TORRENT_STEALTH_PORTS",
    "6881-6889,6969,8999,51413,49001-49009,1025-65535",
)
# Трекеры и DHT — не через sinful (даже если sniffing не сработал)
TORRENT_STEALTH_DOMAINS = tuple(
    d.strip()
    for d in os.environ.get(
        "TORRENT_STEALTH_DOMAINS",
        "domain:tracker,"
        "domain:announce,"
        "domain:retracker.local,"
        "domain:rutracker.org,"
        "domain:rutracker.net,"
        "domain:rutracker.cc,"
        "domain:bt4g.org,"
        "domain:opentrackr.org,"
        "domain:open.stealth.si,"
        "domain:exodus.desync.com,"
        "domain:tracker.opentrackr.org,"
        "domain:torrent.eu.org,"
        "domain:ipv4.rer.lol,"
        "domain:retracker.net,"
        "domain:pubt.net,"
        "domain:nyaa.tracker,"
        "domain:tracker.torrent.eu.org,"
        "domain:tracker.tiny-vps.com,"
        "domain:tracker.moeking.me,"
        "domain:open.demonii.com",
    ).split(",")
    if d.strip()
)

SKIP_CANDELIX = re.compile(r"Обход\s+Белых\s+Списков", re.I)
CANDELIX_WHITELIST_PATTERN = re.compile(r"Обход\s+Белых\s+Списков\s*№(\d+)", re.I)
SKIP_CANDELIX_RU = re.compile(r"^\s*🇷🇺\s*Россия\s*\[TCP\]\s*$", re.I)
CANDELIX_YT_MATCH = re.compile(r"YT\s*NO\s*ADS|без\s*реклам|YT\s*б/р", re.I)
WHITELIST_PATTERN = re.compile(r"белые\s*списки", re.I)
FREE_VPN_SKIP = re.compile(r"белые\s*списки|YT|б/р|RU-сервис", re.I)
FREE_VPN_MATCH = re.compile(
    r"(?:Польша (?:[1579]|10)|Германия [13]|⚡Автоматический)$",
    re.I,
)
REMARK_FLAG_RE = re.compile(r"^([\U0001F1E6-\U0001F1FF]{2})")

INTERNAL_HEADERS = {
    "Host": SUB_HOST,
    "X-Forwarded-Proto": "https",
    "X-Forwarded-For": "127.0.0.1",
    "X-Real-IP": "127.0.0.1",
}


HAPP_ROUTING = os.environ.get("HAPP_ROUTING", """happ://routing/onadd/eyJOYW1lIjogIlNhdGthVlBOIOKAlCBZb3VUdWJlINCx0LXQtyDRgNC10LrQu9Cw0LzRiyIsICJHbG9iYWxQcm94eSI6ICJ0cnVlIiwgIlJvdXRlT3JkZXIiOiAiYmxvY2stcHJveHktZGlyZWN0IiwgIlJlbW90ZUROU1R5cGUiOiAiRG9IIiwgIlJlbW90ZUROU0RvbWFpbiI6ICJodHRwczovL2Nsb3VkZmxhcmUtZG5zLmNvbS9kbnMtcXVlcnkiLCAiRG9tZXN0aWNETlNUeXBlIjogIkRvVSIsICJHZW9pcHVybCI6ICJodHRwczovL2dpdGh1Yi5jb20vTG95YWxzb2xkaWVyL3YycmF5LXJ1bGVzLWRhdC9yZWxlYXNlcy9sYXRlc3QvZG93bmxvYWQvZ2VvaXAuZGF0IiwgIkdlb3NpdGV1cmwiOiAiaHR0cHM6Ly9naXRodWIuY29tL0xveWFsc29sZGllci92MnJheS1ydWxlcy1kYXQvcmVsZWFzZXMvbGF0ZXN0L2Rvd25sb2FkL2dlb3NpdGUuZGF0IiwgIlVzZUNodW5rRmlsZXMiOiAidHJ1ZSIsICJEaXJlY3RJcCI6IFsiZ2VvaXA6cHJpdmF0ZSIsICIxMC4wLjAuMC84IiwgIjE3Mi4xNi4wLjAvMTIiLCAiMTkyLjE2OC4wLjAvMTYiXSwgIkJsb2NrU2l0ZXMiOiBbImdlb3NpdGU6Y2F0ZWdvcnktYWRzLWFsbCIsICJkb21haW46Z29vZ2xlYWRzZXJ2aWNlcy5jb20iLCAiZG9tYWluOmdvb2dsZXN5bmRpY2F0aW9uLmNvbSIsICJkb21haW46ZG91YmxlY2xpY2submV0IiwgImRvbWFpbjphZHNlcnZpY2UuZ29vZ2xlLmNvbSIsICJkb21haW46cGFnZWFkMi5nb29nbGVzeW5kaWNhdGlvbi5jb20iLCAiZG9tYWluOmFkcy55b3V0dWJlLmNvbSIsICJkb21haW46bWFuaWZlc3QuZ29vZ2xldmlkZW8uY29tIiwgImRvbWFpbjpzLnlvdXR1YmUuY29tIl0sICJQcm94eVNpdGVzIjogWyJnZW9zaXRlOnlvdXR1YmUiLCAiZ2Vvc2l0ZTpnb29nbGUiXSwgIkRvbWFpblN0cmF0ZWd5IjogIklQSWZOb25NYXRjaCIsICJGYWtlRE5TIjogImZhbHNlIn0=""")

ADBLOCK_DOMAINS = [
    "domain:googleadservices.com",
    "domain:googlesyndication.com",
    "domain:doubleclick.net",
    "domain:adservice.google.com",
    "domain:pagead2.googlesyndication.com",
    "domain:ads.youtube.com",
    "domain:manifest.googlevideo.com",
    "domain:s.youtube.com",
    "domain:pubads.g.doubleclick.net",
    "domain:static.doubleclick.net",
]

YOUTUBE_ADBLOCK_DOMAINS = [
    "full:youtube.com/pagead/",
    "full:www.youtube.com/pagead/",
    "full:m.youtube.com/pagead/",
    "domain:ads.youtube.com",
    "domain:manifest.googlevideo.com",
    "domain:s.youtube.com",
    "domain:pubads.g.doubleclick.net",
    "domain:static.doubleclick.net",
]

REGULAR_ADBLOCK_DOMAINS = list(
    dict.fromkeys(ADBLOCK_DOMAINS + YOUTUBE_ADBLOCK_DOMAINS)
)

WHITELIST_TOP_NUMBERS = frozenset({1, 2, 4, 11})
# Автовыбор: проверенные с VPS (2 RU, 4 LV, 6 FI, 12 NL)
WHITELIST_AUTO_POOL = (2, 4, 6, 12)
REGULAR_TOP_LTE_NUMBERS = frozenset({13, 15, 16, 19, 22, 23, 24, 25, 26})
REGULAR_YT_WIFI_NUMBERS = frozenset({15, 19, 23, 24, 25, 26})
REGULAR_AUTO_POOL = (13, 15, 16, 19, 22, 23, 24, 25, 26)

WHITELIST_NUMBERS = tuple(range(1, 13))
REGULAR_STABLE_NUMBERS = tuple(range(13, 27))
REGULAR_UNSTABLE_NUMBERS = tuple(range(27, 32))

AUTO_WHITELIST_REMARK = "🎲 Авто-выбор белые списки"
AUTO_LOCATION_REMARK = "🎲 Авто-выбор локации"
AUTO_BALANCER_TAG = "auto-pick"
SUBSCRIPTION_EXPIRED_REMARK = "Продлите подписку в боте @satkavpn_bot"

RU_DIRECT_DOMAINS = [
    "regexp:.*\\.ru$",
    "regexp:.*\\.su$",
    "regexp:.*\\.рф$",
]

# Российские приложения из белых списков операторов — direct, чтобы не ругались на VPN
WHITELIST_APP_DIRECT_DOMAINS = [
    # Сбер
    "domain:sberbank.ru",
    "domain:sberbank.com",
    "domain:online.sberbank.ru",
    "domain:cms.sberbank.ru",
    "domain:api.sberbank.ru",
    "domain:sber.ru",
    "domain:id.sberbank.ru",
    "domain:sberbank-id.ru",
    "domain:sbervisa.ru",
    "domain:sberdevices.ru",
    "domain:sbol.io",
    # Ozon
    "domain:ozon.ru",
    "domain:ozon.by",
    "domain:ozon.com",
    "domain:ozonusercontent.com",
    "domain:ozone.ru",
    "domain:ozonapi.ru",
    # 2ГИС
    "domain:2gis.ru",
    "domain:2gis.com",
    "domain:2gis.biz",
    "domain:dgis.ru",
    "domain:api.2gis.com",
    # Магнит
    "domain:magnit.ru",
    "domain:magnit.com",
    "domain:app.magnit.ru",
    # Wildberries
    "domain:wildberries.ru",
    "domain:wb.ru",
    "domain:wbbasket.ru",
    "domain:wildberries.by",
    "domain:wbxcontent.com",
    "domain:wbcontent.net",
    # Газпромнефть
    "domain:gazprom-neft.ru",
    "domain:gpnmarket.ru",
    "domain:g-pay.ru",
    "domain:azs.gazprom-neft.ru",
]

WHITELIST_APP_DIRECT_PROCESSES = [
    "ru.sberbankmobile",
    "ru.ozon.app.android",
    "ru.dublgis.dgismobile",
    "ru.tander.magnit",
    "com.wildberries.ru",
    "ru.gazpromneft.azs",
]

# IP-check — direct, чтобы 2ip.ru показывал реальный IP пользователя
WHITELIST_IP_CHECK_DOMAINS = [
    "domain:2ip.ru",
    "domain:2ip.io",
    "domain:2ip.me",
    "domain:myip.ru",
    "domain:whoer.net",
    "domain:whoer.com",
    "domain:ipify.org",
    "domain:api.ipify.org",
    "domain:ifconfig.me",
    "domain:icanhazip.com",
    "domain:ipinfo.io",
    "domain:ip.me",
    "domain:whatismyip.com",
    "domain:whatismyipaddress.com",
    "domain:check-host.net",
    "domain:speedtest.net",
    "domain:fast.com",
]

PRIVATE_CIDRS = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "127.0.0.0/8",
    "169.254.0.0/16",
]

MIHOMO_ADBLOCK_RULES = [
    "DOMAIN-SUFFIX,googleadservices.com,REJECT",
    "DOMAIN-SUFFIX,googlesyndication.com,REJECT",
    "DOMAIN-SUFFIX,doubleclick.net,REJECT",
    "DOMAIN-SUFFIX,ads.youtube.com,REJECT",
    "DOMAIN-SUFFIX,manifest.googlevideo.com,REJECT",
    "DOMAIN-KEYWORD,pagead,REJECT",
]

MIHOMO_WHITELIST_APP_RULES = [
  # Сбер, Ozon, 2ГИС, Магнит, Wildberries, Газпромнефть — direct (без VPN)
    "PROCESS-NAME,ru.sberbankmobile,DIRECT",
    "PROCESS-NAME,ru.ozon.app.android,DIRECT",
    "PROCESS-NAME,ru.dublgis.dgismobile,DIRECT",
    "PROCESS-NAME,ru.tander.magnit,DIRECT",
    "PROCESS-NAME,com.wildberries.ru,DIRECT",
    "PROCESS-NAME,ru.gazpromneft.azs,DIRECT",
    "DOMAIN-SUFFIX,sberbank.ru,DIRECT",
    "DOMAIN-SUFFIX,sberbank.com,DIRECT",
    "DOMAIN-SUFFIX,sber.ru,DIRECT",
    "DOMAIN-SUFFIX,sbol.io,DIRECT",
    "DOMAIN-SUFFIX,ozon.ru,DIRECT",
    "DOMAIN-SUFFIX,ozonusercontent.com,DIRECT",
    "DOMAIN-SUFFIX,ozonapi.ru,DIRECT",
    "DOMAIN-SUFFIX,2gis.ru,DIRECT",
    "DOMAIN-SUFFIX,2gis.com,DIRECT",
    "DOMAIN-SUFFIX,dgis.ru,DIRECT",
    "DOMAIN-SUFFIX,magnit.ru,DIRECT",
    "DOMAIN-SUFFIX,wildberries.ru,DIRECT",
    "DOMAIN-SUFFIX,wb.ru,DIRECT",
    "DOMAIN-SUFFIX,wbbasket.ru,DIRECT",
    "DOMAIN-SUFFIX,wbxcontent.com,DIRECT",
    "DOMAIN-SUFFIX,gazprom-neft.ru,DIRECT",
    "DOMAIN-SUFFIX,gpnmarket.ru,DIRECT",
    "DOMAIN-SUFFIX,g-pay.ru,DIRECT",
]


def ensure_block_outbound(cfg: dict) -> None:
    outbounds = cfg.setdefault("outbounds", [])
    if not any(o.get("tag") == "block" for o in outbounds):
        outbounds.append({"tag": "block", "protocol": "blackhole"})


def ensure_direct_outbound(cfg: dict) -> None:
    outbounds = cfg.setdefault("outbounds", [])
    if not any(o.get("tag") == "direct" for o in outbounds):
        outbounds.append({"tag": "direct", "protocol": "freedom"})


def _whitelist_direct_bypass_rules() -> list[dict]:
    """Правила direct для IP-check и российских приложений из белых списков."""
    rules: list[dict] = [
        {
            "type": "field",
            "domain": list(WHITELIST_IP_CHECK_DOMAINS),
            "outboundTag": "direct",
        },
    ]
    if WHITELIST_APP_DIRECT_DOMAINS:
        rules.append(
            {
                "type": "field",
                "domain": list(WHITELIST_APP_DIRECT_DOMAINS),
                "outboundTag": "direct",
            }
        )
    if WHITELIST_APP_DIRECT_PROCESSES:
        rules.append(
            {
                "type": "field",
                "process": list(WHITELIST_APP_DIRECT_PROCESSES),
                "outboundTag": "direct",
            }
        )
    return rules


def _whitelist_default_egress_rule(
    *,
    proxy_tag: str = "proxy",
    balancer_tag: str | None = None,
) -> dict:
    if balancer_tag:
        return {
            "type": "field",
            "network": "tcp,udp",
            "balancerTag": balancer_tag,
        }
    return {
        "type": "field",
        "network": "tcp,udp",
        "outboundTag": proxy_tag,
    }


def rebuild_whitelist_routing(
    cfg: dict,
    *,
    proxy_tag: str = "proxy",
    balancer_tag: str | None = None,
) -> None:
    """Белые списки: IP-check и RU-приложения → direct, остальное → proxy."""
    ensure_direct_outbound(cfg)
    cfg["routing"] = {
        "domainStrategy": "IPIfNonMatch",
        "rules": [
            {"type": "field", "ip": list(PRIVATE_CIDRS), "outboundTag": "direct"},
            *_whitelist_direct_bypass_rules(),
            _whitelist_default_egress_rule(
                proxy_tag=proxy_tag, balancer_tag=balancer_tag
            ),
        ],
    }


def rebuild_whitelist_passthrough_routing(
    cfg: dict,
    *,
    proxy_tag: str = "proxy",
    balancer_tag: str | None = None,
) -> None:
    rebuild_whitelist_routing(
        cfg, proxy_tag=proxy_tag, balancer_tag=balancer_tag
    )


def strip_whitelist_outbounds(cfg: dict) -> None:
    """Один proxy-outbound + direct, без satka-x и прочих веток."""
    proxy = whitelist_primary_outbound(cfg) or get_vless_outbound(cfg)
    outbounds: list[dict] = []
    if proxy:
        ob = copy.deepcopy(proxy)
        ob["tag"] = "proxy"
        outbounds.append(ob)
    cfg["outbounds"] = outbounds
    ensure_direct_outbound(cfg)


def rebuild_safe_routing(cfg: dict) -> None:
    """Минимальный routing без geosite/geoip — совместим с XrayCore в Happ."""
    ensure_block_outbound(cfg)
    cfg["routing"] = {
        "domainStrategy": "IPIfNonMatch",
        "rules": [
            {"type": "field", "domain": list(ADBLOCK_DOMAINS), "outboundTag": "block"},
            {"type": "field", "domain": list(RU_DIRECT_DOMAINS), "outboundTag": "direct"},
            {"type": "field", "ip": list(PRIVATE_CIDRS), "outboundTag": "direct"},
            {"type": "field", "protocol": ["bittorrent"], "outboundTag": "direct"},
        ],
    }


def rebuild_regular_routing(cfg: dict) -> None:
    """Обычные локации: блок рекламы YouTube + базовые правила."""
    ensure_block_outbound(cfg)
    cfg["routing"] = {
        "domainStrategy": "IPIfNonMatch",
        "rules": [
            {"type": "field", "domain": list(REGULAR_ADBLOCK_DOMAINS), "outboundTag": "block"},
            {"type": "field", "domain": list(RU_DIRECT_DOMAINS), "outboundTag": "direct"},
            {"type": "field", "ip": list(PRIVATE_CIDRS), "outboundTag": "direct"},
            {"type": "field", "protocol": ["bittorrent"], "outboundTag": "direct"},
        ],
    }


def finalize_regular_cfg(cfg: dict, *, ping_seed: str | None = None) -> None:
    sanitize_routing(cfg)
    rebuild_regular_routing(cfg)
    optimize_performance(cfg)
    if ping_seed:
        apply_fake_ping_meta(cfg, ping_seed)


def sanitize_routing(cfg: dict) -> None:
    """Убрать balancers/observatory и geo-правила из исходника Candelix."""
    routing = cfg.get("routing")
    if routing:
        routing.pop("balancers", None)
        routing.pop("domainMatcher", None)
    cfg.pop("burstObservatory", None)
    cfg.pop("observatory", None)


def stable_fake_ping_ms(seed: str) -> int:
    digest = hashlib.md5(seed.encode(), usedforsecurity=False).hexdigest()
    return 20 + (int(digest[:8], 16) % 81)


def apply_fake_ping_meta(cfg: dict, seed: str) -> None:
    """Стабильный фейк-пинг для колонки теста в Happ (не в названии)."""
    ping_ms = stable_fake_ping_ms(seed)
    meta = cfg.setdefault("meta", {})
    meta["ping"] = ping_ms
    meta["latency"] = ping_ms
    cfg["ping"] = ping_ms


def simplify_dns(cfg: dict) -> None:
    cfg["dns"] = {
        "servers": ["1.1.1.1", "8.8.8.8"],
        "queryStrategy": "UseIPv4",
    }


def optimize_performance(cfg: dict) -> None:
    """Упростить конфиг Candelix: быстрее и стабильнее."""
    simplify_dns(cfg)
    for ob in cfg.get("outbounds", []):
        if ob.get("protocol") != "vless":
            continue
        ss = ob.setdefault("streamSettings", {})
        sock = ss.setdefault("sockopt", {})
        sock.setdefault("tcpFastOpen", True)
        sock.setdefault("tcpNoDelay", True)
        sock.setdefault("domainStrategy", "UseIPv4")


def finalize_cfg(cfg: dict, *, ping_seed: str | None = None) -> None:
    sanitize_routing(cfg)
    rebuild_safe_routing(cfg)
    optimize_performance(cfg)
    if ping_seed:
        apply_fake_ping_meta(cfg, ping_seed)


SECTION_WHITELIST = "Для моб. операторов"
SECTION_REGULAR = "Обычные локации"
SECTION_MOM_WHITELIST = "Интернет при глушилках и номер"
SECTION_MOM_SERVERS = "Серверы"

MOM_WHITELIST_NUMBERS = (2, 4, 6, 12)
MOM_REGULAR_NUMBERS = (13, 15, 16, 19)
MOM_REGULAR_PURPOSE = "Для работы Telegram и YouTube"

HWID_FORWARD_REQUEST_HEADERS = frozenset({
    "x-hwid",
    "x-device-os",
    "x-ver-os",
    "x-device-model",
    "user-agent",
})

HWID_FORWARD_RESPONSE_HEADERS = frozenset({
    "x-hwid-active",
    "x-hwid-not-supported",
    "x-hwid-max-devices-reached",
    "x-hwid-limit",
})


class NativeSubscriptionError(Exception):
    def __init__(self, status: int, headers: dict[str, str] | None = None) -> None:
        super().__init__(f"native subscription HTTP {status}")
        self.status = status
        self.headers = headers or {}


def pick_hwid_request_headers(headers: dict | None) -> dict[str, str]:
    if not headers:
        return {}
    out: dict[str, str] = {}
    for key, value in headers.items():
        lower = key.lower()
        if lower in HWID_FORWARD_REQUEST_HEADERS and value:
            out[lower] = value
    return out


def pick_hwid_response_headers(headers: dict | None) -> dict[str, str]:
    if not headers:
        return {}
    return {
        key: value
        for key, value in headers.items()
        if key.lower() in HWID_FORWARD_RESPONSE_HEADERS
    }


HAPP_UA_RE = re.compile(r"happ", re.I)
CLASH_UA_RE = re.compile(
    r"clash|mihomo|stash|koala|clashmeta|verge|flclash|nyanpasu|metacubex|karing",
    re.I,
)
V2RAY_UA_RE = re.compile(
    r"v2ray|incy|hiddify|nekobox|matsuri|shadowrocket|quantumult|surge|clash|stash|sing-box|passwall|streisand|foxray|loon|pharos|kitsunebi",
    re.I,
)


def is_happ_client(user_agent: str) -> bool:
    return bool(HAPP_UA_RE.search(user_agent or ""))


def is_clash_client(user_agent: str) -> bool:
    return bool(CLASH_UA_RE.search(user_agent or ""))


def is_v2ray_style_client(user_agent: str) -> bool:
    return bool(V2RAY_UA_RE.search(user_agent or ""))


def resolve_client_hwid(
    token: str, client_headers: dict | None, user_agent: str
) -> dict[str, str]:
    del token, user_agent
    return pick_hwid_request_headers(client_headers)


def subscription_hwid_error(hwid_headers: dict[str, str]) -> bool:
    return (
        hwid_headers.get("x-hwid-max-devices-reached") == "true"
        or hwid_headers.get("x-hwid-not-supported") == "true"
    )


def get_user_vless_outbound(cfg: dict, *, allow_placeholder: bool = False) -> dict | None:
    outbounds = cfg.get("outbounds") or []

    def valid(ob: dict) -> bool:
        if ob.get("protocol") != "vless":
            return False
        v = ob.get("settings", {}).get("vnext", [{}])[0]
        addr = v.get("address")
        port = v.get("port", 0)
        if allow_placeholder:
            return bool(addr) and port > 0
        return bool(addr) and addr not in ("0.0.0.0",) and port > 1

    for tag in ("proxy", "main"):
        for ob in outbounds:
            if ob.get("tag") == tag and valid(ob):
                return ob
    for ob in outbounds:
        if valid(ob):
            return ob
    return None


def vless_outbound_to_uri(ob: dict, remark: str) -> str:
    vnext = ob["settings"]["vnext"][0]
    user = vnext["users"][0]
    uuid = user["id"]
    host = vnext["address"]
    port = vnext["port"]

    params = ["encryption=none"]
    flow = user.get("flow")
    if flow:
        params.append(f"flow={flow}")

    ss = ob.get("streamSettings") or {}
    net = ss.get("network", "tcp")
    params.append(f"type={net}")

    if net == "ws":
        ws = ss.get("wsSettings") or {}
        if ws.get("path"):
            params.append(f"path={quote(ws['path'], safe='')}")
        host_hdr = (ws.get("headers") or {}).get("Host")
        if host_hdr:
            params.append(f"host={quote(host_hdr, safe='')}")
    elif net == "grpc":
        grpc = ss.get("grpcSettings") or {}
        if grpc.get("serviceName"):
            params.append(f"serviceName={quote(grpc['serviceName'], safe='')}")

    elif net == "xhttp":
        xhttp = ss.get("xhttpSettings") or {}
        if xhttp.get("path"):
            params.append(f"path={quote(xhttp['path'], safe='')}")
        if xhttp.get("host"):
            params.append(f"host={quote(xhttp['host'], safe='')}")
        if xhttp.get("mode"):
            params.append(f"mode={quote(xhttp['mode'], safe='')}")

    security = ss.get("security", "none")
    params.append(f"security={security}")

    if security == "reality":
        rs = ss.get("realitySettings") or {}
        if rs.get("serverName"):
            params.append(f"sni={quote(rs['serverName'], safe='')}")
        if rs.get("publicKey"):
            params.append(f"pbk={quote(rs['publicKey'], safe='')}")
        if rs.get("shortId"):
            params.append(f"sid={quote(rs['shortId'], safe='')}")
        if rs.get("fingerprint"):
            params.append(f"fp={quote(rs['fingerprint'], safe='')}")
        if rs.get("spiderX"):
            params.append(f"spx={quote(rs['spiderX'], safe='')}")
    elif security == "tls":
        ts = ss.get("tlsSettings") or {}
        if ts.get("serverName"):
            params.append(f"sni={quote(ts['serverName'], safe='')}")
        if ts.get("fingerprint"):
            params.append(f"fp={quote(ts['fingerprint'], safe='')}")

    if net == "tcp":
        tcp = ss.get("tcpSettings") or {}
        header = tcp.get("header") or {}
        if header.get("type") in (None, "", "none"):
            params.append("headerType=none")

    fragment = quote(remark, safe="")
    return f"vless://{uuid}@{host}:{port}?{'&'.join(params)}#{fragment}"


def configs_to_vless_base64(configs: list, hwid_headers: dict[str, str]) -> bytes:
    allow_placeholder = subscription_hwid_error(hwid_headers)
    lines: list[str] = []
    for cfg in configs:
        remark = cfg.get("remarks", "")
        if not allow_placeholder and ("⬇️" in remark or "🎲" in remark):
            continue
        ob = get_user_vless_outbound(cfg, allow_placeholder=allow_placeholder)
        if not ob:
            continue
        lines.append(vless_outbound_to_uri(ob, remark))
    payload = "\n".join(lines).encode()
    return base64.b64encode(payload)


def merge_subscription_vless_base64(
    token: str, client_headers: dict | None = None
) -> tuple[bytes, dict[str, str]]:
    merged, hwid_headers = merge_subscription(token, client_headers)
    return configs_to_vless_base64(merged, hwid_headers), hwid_headers


def merge_whitelist_vless_base64(token: str = "") -> bytes:
    return configs_to_vless_base64(merge_whitelist_subscription(token), {})


def merge_free_vless_base64(
    token: str = "", client_headers: dict | None = None
) -> bytes:
    return configs_to_vless_base64(
        merge_free_subscription(token, client_headers), {}
    )


def format_separator_remarks(title: str) -> str:
    """⬇️ Заголовок ⬇️ по центру строки в списке Happ."""
    core = re.sub(r"^[⬇️↓\s]+|[⬇️↓\s]+$", "", (title or "").strip()) or title.strip()
    label = f"⬇️ {core} ⬇️"
    width = 38
    pad_total = max(0, width - len(label))
    left = pad_total // 2
    return (" " * left) + label + (" " * (pad_total - left))


def build_separator_cfg(title: str) -> dict:
    """Заголовок-разделитель в списке Happ (не подключается)."""
    return {
        "remarks": format_separator_remarks(title),
        "dns": {"servers": ["1.1.1.1"], "queryStrategy": "UseIPv4"},
        "routing": {
            "domainStrategy": "IPIfNonMatch",
            "rules": [{"type": "field", "network": "tcp,udp", "outboundTag": "block"}],
        },
        "inbounds": [],
        "outbounds": [
            {"tag": "block", "protocol": "blackhole"},
        ],
        "meta": {"serverDescription": "список ниже"},
    }


def build_expired_notice_cfg() -> dict:
    """Сообщение в списке локаций Happ при истёкшей подписке."""
    return build_separator_cfg(SUBSCRIPTION_EXPIRED_REMARK)


CANDELIX_HEADERS = {
    "x-hwid": CANDELIX_HWID,
    "x-device-os": "iOS",
    "User-Agent": "Happ/2.0",
}

WHITELIST_HEADERS = {"User-Agent": "Happ/2.0"}


@lru_cache(maxsize=1)
def load_locations() -> tuple[dict, ...]:
    with open(LOCATIONS_FILE, encoding="utf-8") as f:
        return tuple(json.load(f))


def location_family(name: str) -> str:
    """Базовое имя локации: «Финляндия 2» → «Финляндия»."""
    m = re.match(r"^(.+?)(?:\s+\d+)?$", (name or "").strip())
    return (m.group(1) if m else name).strip()


def build_family_numbers(locations: list) -> dict[int, int | None]:
    """Индекс локации → номер внутри семейства (#N) или None если копий нет."""
    families: dict[str, list[int]] = {}
    for i, loc in enumerate(locations):
        if loc.get("type") == "separator":
            continue
        families.setdefault(location_family(loc["name"]), []).append(i)

    out: dict[int, int | None] = {}
    for indices in families.values():
        if len(indices) == 1:
            out[indices[0]] = None
        else:
            for ordinal, idx in enumerate(indices, 1):
                out[idx] = ordinal
    return out


def format_remark(flag: str, name: str, *, number: int) -> str:
    return f"{flag} {name} #{number}"


def location_badges(number: int) -> str:
    if number in REGULAR_TOP_LTE_NUMBERS:
        badge = "LTE | ТОП"
        if number in REGULAR_YT_WIFI_NUMBERS:
            badge += " | YT б/р | Wi-Fi"
        return badge
    return "WIFI"


def format_mom_whitelist_remark(
    item: dict, number: int, *, candelix: bool = False
) -> str:
    flag = whitelist_flag_for_item(item, number, candelix=candelix)
    if number in WHITELIST_TOP_NUMBERS:
        return f"{flag} Белые списки | ТОП"
    return f"{flag} Белые списки"


def format_mom_location_remark(flag: str, name: str, *, number: int) -> str:
    del number
    return f"{flag} {name} | {MOM_REGULAR_PURPOSE}"


def format_location_remark(flag: str, name: str, *, number: int) -> str:
    badge = location_badges(number)
    return f"{flag} {name} | {badge} #{number}"


def whitelist_sort_key(number: int) -> tuple[int, int]:
    return (0 if number in WHITELIST_TOP_NUMBERS else 1, number)


def number_sort_key(value: int) -> int:
    return value


def locations_by_number(locations: list[dict]) -> list[dict]:
    return sorted(locations, key=lambda loc: int(loc["number"]))


def location_sort_key(loc: dict) -> tuple[int, int]:
    tier = loc.get("tier", "wifi")
    number = int(loc.get("number", 999))
    return (0 if tier == "top_lte" else 1, number)


def split_location_sections(locations: list[dict]) -> tuple[list[dict], dict | None, list[dict]]:
    stable: list[dict] = []
    unstable: list[dict] = []
    unstable_sep: dict | None = None
    after_sep = False
    for loc in locations:
        if loc.get("type") == "separator":
            after_sep = True
            unstable_sep = loc
            continue
        if after_sep:
            unstable.append(loc)
        else:
            stable.append(loc)
    return stable, unstable_sep, unstable


def proxy_outbound(cfg: dict) -> dict | None:
    for ob in cfg.get("outbounds", []):
        if ob.get("protocol") == "vless" and ob.get("tag") == "proxy":
            return copy.deepcopy(ob)
    ob = get_vless_outbound(cfg)
    return copy.deepcopy(ob) if ob else None


def collect_aux_outbounds(base: dict) -> list[dict]:
    """Все outbounds кроме основного proxy (bridge, direct, block, torrent)."""
    out: list[dict] = []
    seen: set[str] = set()
    for ob in base.get("outbounds", []):
        tag = ob.get("tag", "")
        proto = ob.get("protocol", "")
        if tag == "proxy":
            continue
        if proto == "vless" and tag not in ("bridge", TORRENT_STEALTH_TAG):
            continue
        if tag in seen:
            continue
        seen.add(tag)
        out.append(copy.deepcopy(ob))
    return out


def apply_balancer_whitelist_routing(
    cfg: dict,
    selector: list[str],
    *,
    natives: dict[str, dict] | None = None,
) -> None:
    del natives
    ensure_direct_outbound(cfg)
    cfg["routing"] = {
        "domainStrategy": "IPIfNonMatch",
        "balancers": [
            {
                "tag": AUTO_BALANCER_TAG,
                "selector": selector,
                "strategy": {"type": "random"},
            }
        ],
        "rules": [
            {"type": "field", "ip": list(PRIVATE_CIDRS), "outboundTag": "direct"},
            *_whitelist_direct_bypass_rules(),
            _whitelist_default_egress_rule(balancer_tag=AUTO_BALANCER_TAG),
        ],
    }


def apply_balancer_regular_routing(cfg: dict, selector: list[str]) -> None:
    ensure_block_outbound(cfg)
    ensure_direct_outbound(cfg)
    cfg["routing"] = {
        "domainStrategy": "IPIfNonMatch",
        "balancers": [
            {
                "tag": AUTO_BALANCER_TAG,
                "selector": selector,
                "strategy": {"type": "random"},
            }
        ],
        "rules": [
            {
                "type": "field",
                "domain": list(REGULAR_ADBLOCK_DOMAINS),
                "outboundTag": "block",
            },
            {"type": "field", "domain": list(RU_DIRECT_DOMAINS), "outboundTag": "direct"},
            {"type": "field", "ip": list(PRIVATE_CIDRS), "outboundTag": "direct"},
            {"type": "field", "protocol": ["bittorrent"], "outboundTag": "direct"},
            {"type": "field", "network": "tcp", "balancerTag": AUTO_BALANCER_TAG},
            {"type": "field", "network": "udp", "balancerTag": AUTO_BALANCER_TAG},
        ],
    }


def build_balancer_cfg(
    pool_cfgs: list[dict],
    remark: str,
    *,
    mode: str,
    natives: dict[str, dict] | None = None,
) -> dict | None:
    """Xray random balancer — выбор сервера на каждое подключение без обновления подписки."""
    if not pool_cfgs:
        return None

    selector: list[str] = []
    proxies: list[dict] = []
    for idx, cfg in enumerate(pool_cfgs):
        tag = f"proxy-{idx}"
        ob = proxy_outbound(cfg)
        if not ob:
            continue
        ob["tag"] = tag
        selector.append(tag)
        proxies.append(ob)

    if not selector:
        return None

    base = pool_cfgs[0]
    outbounds = proxies + collect_aux_outbounds(base)
    ensure_block_outbound({"outbounds": outbounds})
    ensure_direct_outbound({"outbounds": outbounds})

    result = {
        "remarks": remark,
        "inbounds": copy.deepcopy(base.get("inbounds", [])),
        "outbounds": outbounds,
    }

    if mode == "whitelist":
        apply_balancer_whitelist_routing(result, selector, natives=natives)
        ensure_whitelist_sniffing(result)
    else:
        apply_balancer_regular_routing(result, selector)

    optimize_performance(result)
    apply_fake_ping_meta(result, remark)
    return result


def normalize_country(remark: str) -> str | None:
    raw = remark or ""
    text = raw
    text = re.sub(r"^🔗\s*", "", text)
    text = re.sub(r"\s*#\d+\s*$", "", text)
    text = re.sub(r"\s*\[(?:TCP|LTE)\]\s*", "", text, flags=re.I)
    # Longest match first to avoid "Финляндия" matching "Финляндия 2"
    for loc in sorted(load_locations(), key=lambda x: len(x["name"]), reverse=True):
        if loc["name"] in raw or loc["name"] in text:
            return loc["name"]
    return None


def fetch_json(url: str, headers: dict | None = None) -> list:
    data, _status, _resp_headers = fetch_json_with_response(url, headers)
    return data


def fetch_json_with_response(
    url: str, headers: dict | None = None
) -> tuple[list, int, dict[str, str]]:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.load(resp)
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as exc:
        resp_headers = {k.lower(): v for k, v in exc.headers.items()}
        raise NativeSubscriptionError(exc.code, resp_headers) from exc
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array from {url}")
    return data, resp.status, resp_headers


def fetch_text(url: str, headers: dict | None = None) -> str:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=8) as resp:
        return resp.read().decode()


def fetch_native_json(
    token: str, client_headers: dict | None = None
) -> tuple[list, dict[str, str]]:
    hwid_headers = pick_hwid_request_headers(client_headers)
    headers = dict(INTERNAL_HEADERS)
    headers.update(hwid_headers)
    try:
        data, _status, resp_headers = fetch_json_with_response(
            f"{SUB_INTERNAL.rstrip('/')}/{token}/json", headers
        )
        if len(data) == 1 and "не поддерживается" in (data[0].get("remarks") or "").lower():
            raise RuntimeError("subscription page returned hwid placeholder")
        return data, pick_hwid_response_headers(resp_headers)
    except Exception as exc:
        print(f"internal json fetch failed for {token}: {exc}; using API fallback")
    try:
        return fetch_native_json_via_api(token), hwid_headers
    except NativeSubscriptionError:
        raise
    except Exception as exc:
        raise RuntimeError(f"native subscription fetch failed for {token}: {exc}") from exc


def vless_uri_to_cfg(uri: str) -> dict:
    if not uri.startswith("vless://"):
        raise ValueError(f"Expected vless URI, got: {uri[:32]}")
    rest = uri[8:]
    uuid_host, _, fragment = rest.partition("#")
    user_host, _, query = uuid_host.partition("?")
    uuid, _, host_port = user_host.partition("@")
    host, _, port_str = host_port.rpartition(":")
    params = {k: v[0] for k, v in parse_qs(query, keep_blank_values=True).items()}

    remark = unquote(fragment)
    flow = params.get("flow")
    net = params.get("type", "tcp")
    if net in ("raw", ""):
        net = "tcp"
    security = params.get("security") or "none"

    user: dict = {"id": uuid, "encryption": params.get("encryption", "none")}
    if flow:
        user["flow"] = flow

    ss: dict = {"network": net, "security": security}
    if net == "tcp":
        ss["tcpSettings"] = {"header": {"type": params.get("headerType", "none")}}
    elif net == "ws":
        ws: dict = {}
        if params.get("path"):
            ws["path"] = unquote(params["path"])
        if params.get("host"):
            ws["headers"] = {"Host": params["host"]}
        ss["wsSettings"] = ws
    elif net == "grpc":
        grpc: dict = {}
        if params.get("serviceName"):
            grpc["serviceName"] = params["serviceName"]
        if params.get("mode"):
            grpc["mode"] = params["mode"]
        ss["grpcSettings"] = grpc
    elif net == "xhttp":
        xhttp: dict = {}
        if params.get("path"):
            xhttp["path"] = unquote(params["path"])
        if params.get("host"):
            xhttp["host"] = params["host"]
        if params.get("mode"):
            xhttp["mode"] = params["mode"]
        if params.get("extra"):
            try:
                xhttp["extra"] = json.loads(unquote(params["extra"]))
            except (json.JSONDecodeError, TypeError):
                pass
        ss["xhttpSettings"] = xhttp

    if security == "reality":
        rs = {}
        if params.get("sni"):
            rs["serverName"] = params["sni"]
        if params.get("pbk"):
            rs["publicKey"] = params["pbk"]
        if params.get("sid"):
            rs["shortId"] = params["sid"]
        if params.get("fp"):
            rs["fingerprint"] = params["fp"]
        if params.get("spx"):
            rs["spiderX"] = unquote(params["spx"])
        ss["realitySettings"] = rs
    elif security == "tls":
        ts = {}
        if params.get("sni"):
            ts["serverName"] = params["sni"]
        if params.get("fp"):
            ts["fingerprint"] = params["fp"]
        ss["tlsSettings"] = ts

    return {
        "remarks": remark,
        "outbounds": [
            {
                "tag": "proxy",
                "protocol": "vless",
                "settings": {
                    "vnext": [
                        {
                            "address": host,
                            "port": int(port_str),
                            "users": [user],
                        }
                    ]
                },
                "streamSettings": ss,
            }
        ],
    }


def remnawave_api_request(path: str) -> dict:
    if not REMNAWAVE_API_TOKEN:
        raise RuntimeError("REMNAWAVE_API_TOKEN is not configured")
    url = f"{REMNAWAVE_PANEL_URL}{path}"
    panel_host = os.environ.get("PANEL_DOMAIN", "panel.satkaconnect.xyz")
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {REMNAWAVE_API_TOKEN}",
            "Host": panel_host,
            "X-Forwarded-Proto": "https",
            "X-Forwarded-For": "127.0.0.1",
            "X-Real-IP": "127.0.0.1",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as exc:
        raise NativeSubscriptionError(exc.code) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected Remnawave API payload from {path}")
    return payload


@lru_cache(maxsize=1)
def load_free_tokens() -> frozenset[str]:
    path = (FREE_TOKENS_FILE or "").strip()
    if not path or not os.path.isfile(path):
        return frozenset()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        tokens = data.get("free") if isinstance(data, dict) else data
        if isinstance(tokens, list):
            return frozenset(str(t).strip() for t in tokens if t)
    except Exception as exc:
        print(f"free tokens file load failed: {exc}")
    return frozenset()


@lru_cache(maxsize=512)
def fetch_remnawave_user(token: str) -> dict | None:
    try:
        payload = remnawave_api_request(f"/api/users/by-short-uuid/{token}")
    except (NativeSubscriptionError, OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"remnawave user lookup failed for {token}: {exc}")
        return None
    user = payload.get("response")
    return user if isinstance(user, dict) else None


def remnawave_user_squad_names(user: dict | None) -> tuple[str, ...]:
    if not user:
        return ()
    squads = user.get("activeInternalSquads") or []
    names: list[str] = []
    for squad in squads:
        if isinstance(squad, dict):
            name = (squad.get("name") or "").strip().lower()
            if name:
                names.append(name)
    return tuple(names)


@lru_cache(maxsize=512)
def lookup_tariff_id_from_bedolaga(token: str) -> int | None:
    db_url = (BEDOLAGA_DATABASE_URL or "").strip()
    if not db_url or not token:
        return None
    patterns = (
        f"%/{token}",
        f"%/{token}/%",
        f"%/{token}?%",
        f"%{token}%",
    )
    sql = """
        SELECT tariff_id
        FROM subscriptions
        WHERE status IN ('active', 'trial', 'limited')
          AND (
            subscription_url LIKE %s
            OR subscription_url LIKE %s
            OR subscription_url LIKE %s
            OR COALESCE(subscription_crypto_link, '') LIKE %s
          )
        ORDER BY
          CASE WHEN tariff_id = %s THEN 0 ELSE 1 END,
          id DESC
        LIMIT 1
    """
    params = patterns + (TARIFF_FREE_ID,)
    try:
        import psycopg2  # type: ignore[import-not-found]
    except ImportError:
        print("bedolaga tariff lookup skipped: psycopg2 is not installed")
        return None
    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
    except Exception as exc:
        print(f"bedolaga tariff lookup failed for {token}: {exc}")
        return None
    if not row or row[0] is None:
        return None
    return int(row[0])


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError):
        return None


def is_remnawave_subscription_active(user: dict | None) -> bool:
    if not user:
        return False
    status = (user.get("status") or "").upper()
    if status not in ("ACTIVE", "LIMITED"):
        return False
    expire_at = parse_iso_datetime(user.get("expireAt"))
    if expire_at is not None and expire_at <= datetime.now(timezone.utc):
        return False
    return True


@lru_cache(maxsize=512)
def is_free_subscription_active_in_bedolaga(token: str) -> bool:
    db_url = (BEDOLAGA_DATABASE_URL or "").strip()
    if not db_url or not token:
        return False
    patterns = (
        f"%/{token}",
        f"%/{token}/%",
        f"%/{token}?%",
        f"%{token}%",
    )
    sql = """
        SELECT 1
        FROM subscriptions
        WHERE tariff_id = %s
          AND status IN ('active', 'trial', 'limited')
          AND (end_date IS NULL OR end_date > NOW())
          AND (
            subscription_url LIKE %s
            OR subscription_url LIKE %s
            OR subscription_url LIKE %s
            OR COALESCE(subscription_crypto_link, '') LIKE %s
          )
        LIMIT 1
    """
    params = (TARIFF_FREE_ID,) + patterns
    try:
        import psycopg2  # type: ignore[import-not-found]
    except ImportError:
        return False
    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone() is not None
    except Exception as exc:
        print(f"bedolaga free active lookup failed for {token}: {exc}")
        return False


def is_free_subscription_active(
    token: str, client_headers: dict | None = None
) -> bool:
    """Бесплатная подписка действительна (Remnawave / bedolaga / нативные ноды)."""
    sub_token = (token or "").strip()
    if not sub_token:
        return False

    user = fetch_remnawave_user(sub_token)
    if user is not None:
        return is_remnawave_subscription_active(user)

    if is_free_subscription_active_in_bedolaga(sub_token):
        return True

    native_items = fetch_free_native_servers(sub_token, client_headers)
    if not native_items:
        return False
    if len(native_items) == 1:
        remark = (native_items[0].get("remarks") or "").lower()
        if "не поддерживается" in remark:
            return False
    return True


def is_subscription_active(token: str) -> bool:
    """Подписка Remnawave активна (платная / любой тариф)."""
    sub_token = (token or "").strip()
    if not sub_token:
        return False
    user = fetch_remnawave_user(sub_token)
    if user is None:
        return True
    return is_remnawave_subscription_active(user)


def resolve_effective_plan(token: str, explicit_plan: str | None) -> str | None:
    """Маршрут подписки: paid (None) | free | whitelist.

    Старые ключи без /free должны получать free-merge для бесплатного тарифа.
    """
    if explicit_plan in ("free", "whitelist", "mom"):
        return explicit_plan

    if token in load_free_tokens() and is_free_subscription_active(token):
        return "free"

    tariff_id = lookup_tariff_id_from_bedolaga(token)
    if tariff_id == TARIFF_FREE_ID and is_free_subscription_active(token):
        return "free"
    if tariff_id == TARIFF_WHITELIST_ID:
        return "whitelist"
    if tariff_id == TARIFF_MOM_ID:
        return "mom"

    squads = remnawave_user_squad_names(fetch_remnawave_user(token))
    if squads == (REMNAWAVE_WHITELIST_SQUAD,):
        return "whitelist"
    if squads and all(name == REMNAWAVE_WHITELIST_SQUAD for name in squads):
        return "whitelist"

    return None


def fetch_native_json_via_api(token: str) -> list:
    payload = remnawave_api_request(f"/api/subscriptions/by-short-uuid/{token}")
    links = payload.get("response", {}).get("links") or []
    if not links:
        raise RuntimeError(f"No native links for token {token}")
    return [vless_uri_to_cfg(link) for link in links]


def fetch_candelix_json() -> list:
    return fetch_json(f"{CANDELIX_URL.rstrip('/')}/json", CANDELIX_HEADERS)


def format_whitelist_remark(original: str, number: int) -> str:
    text = re.sub(r"\s*📃\s*", " ", original or "").strip()
    text = re.sub(r"\s+", " ", text)
    if not text.startswith("📃"):
        text = f"📃 {text}"
    return f"{text} #{number}"


# Sinful free-slot → отображаемое имя (как в платной подписке)
FREE_POLAND_SLOT = {
    "1": "Польша",
    "5": "Польша",
    "7": "Польша 2",
    "9": "Польша 3",
    "10": "Польша 4",
}
FREE_GERMANY_SLOT = {
    "1": "Германия",
    "3": "Германия 2",
}


def resolve_free_display(original: str) -> tuple[str, str]:
    """Имя и флаг для бесплатных серверов: флаг первым — Happ показывает иконку страны."""
    text = re.sub(r"\s+", " ", (original or "").strip())
    flag = ""
    m = REMARK_FLAG_RE.match(text)
    if m:
        flag = m.group(1)
        text = text[m.end():].lstrip()
    text = re.sub(r"^⚡\s*", "", text)
    text = re.sub(r"\s*\|.*$", "", text).strip()

    if re.search(r"автоматический", text, re.I):
        return flag or "🇪🇺", "Авто"

    gm = re.match(r"Германия\s*(\d+)?", text, re.I)
    if gm:
        slot = gm.group(1) or "1"
        name = FREE_GERMANY_SLOT.get(slot, f"Германия {slot}")
        return flag or "🇩🇪", name

    pm = re.match(r"Польша\s*(\d+)?", text, re.I)
    if pm:
        slot = pm.group(1) or "5"
        name = FREE_POLAND_SLOT.get(slot, f"Польша {slot}")
        return flag or "🇵🇱", name

    country = normalize_country(original)
    if country:
        for loc in load_locations():
            if loc.get("type") == "separator":
                continue
            if loc["name"] == country or country in loc.get("name", ""):
                return loc["flag"], loc["name"]

    return flag or "🌍", text or "Free"


def format_free_remark(original: str, number: int) -> str:
    flag, name = resolve_free_display(original)
    return format_remark(flag, name, number=number)


def external_json_url(base: str) -> str:
    url = base.strip().rstrip("/")
    if not url:
        return ""
    return url if url.endswith("/json") else f"{url}/json"


@lru_cache(maxsize=1)
def fetch_whitelist_json() -> tuple[dict, ...]:
    url = external_json_url(WHITELIST_URL)
    if not url:
        return ()
    try:
        items = fetch_json(url, WHITELIST_HEADERS)
    except Exception as exc:
        print(f"whitelist fetch failed: {exc}")
        return ()
    return tuple(
        item for item in items if WHITELIST_PATTERN.search(item.get("remarks", ""))
    )


@lru_cache(maxsize=1)
def fetch_candelix_whitelist_json() -> tuple[dict, ...]:
    """«Обход Белых Списков №N [LTE]» из Candelix."""
    try:
        items = fetch_candelix_json()
    except Exception as exc:
        print(f"candelix whitelist fetch failed: {exc}")
        return ()
    matched: list[tuple[int, dict]] = []
    for item in items:
        m = CANDELIX_WHITELIST_PATTERN.search(item.get("remarks", ""))
        if m:
            matched.append((int(m.group(1)), item))
    matched.sort(key=lambda x: x[0])
    return tuple(item for _, item in matched)


def fetch_paid_whitelist_json() -> tuple[dict, ...]:
    """Белые списки для платной подписки (static / Candelix / sinful)."""
    if PAID_WHITELIST_SOURCE == "static":
        return fetch_static_whitelist_json()
    if PAID_WHITELIST_SOURCE == "sinful":
        return fetch_whitelist_json()
    return fetch_candelix_whitelist_json()


def paid_whitelist_from_candelix() -> bool:
    return PAID_WHITELIST_SOURCE == "candelix"


def paid_whitelist_from_static() -> bool:
    return PAID_WHITELIST_SOURCE == "static"


@lru_cache(maxsize=1)
def fetch_static_whitelist_json() -> tuple[dict, ...]:
    path = (WHITELIST_VLESS_FILE or "").strip()
    if not path or not os.path.isfile(path):
        print(f"static whitelist file missing: {path}")
        return ()
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        print(f"static whitelist load failed: {exc}")
        return ()

    servers = data.get("servers") if isinstance(data, dict) else data
    if not isinstance(servers, list):
        return ()

    out: list[dict] = []
    for entry in servers:
        if not isinstance(entry, dict):
            continue
        uri = (entry.get("uri") or "").strip()
        if not uri:
            continue
        try:
            cfg = vless_uri_to_cfg(uri)
        except Exception as exc:
            print(f"static whitelist parse failed #{entry.get('number')}: {exc}")
            continue
        number = int(entry.get("number") or len(out) + 1)
        cfg["_wl_number"] = number
        cfg["_wl_top"] = bool(entry.get("top"))
        if entry.get("flag"):
            cfg["_wl_flag"] = entry["flag"]
        if entry.get("label"):
            cfg["_wl_label"] = entry["label"]
        out.append(cfg)

    out.sort(key=lambda item: int(item.get("_wl_number", 0)))
    return tuple(out)


def static_whitelist_number(item: dict, fallback: int) -> int:
    return int(item.get("_wl_number") or fallback)


def whitelist_item_number(item: dict, fallback: int) -> int:
    if paid_whitelist_from_static():
        return static_whitelist_number(item, fallback)
    if paid_whitelist_from_candelix():
        return candelix_whitelist_number(item, fallback)
    return fallback


def candelix_whitelist_number(item: dict, fallback: int) -> int:
    m = CANDELIX_WHITELIST_PATTERN.search(item.get("remarks", ""))
    return int(m.group(1)) if m else fallback


@lru_cache(maxsize=1)
def fetch_free_vpn_json() -> tuple[dict, ...]:
    url = external_json_url(FREE_VPN_URL)
    if not url:
        return ()
    try:
        items = fetch_json(url, WHITELIST_HEADERS)
    except Exception as exc:
        print(f"free vpn fetch failed: {exc}")
        return ()
    out = []
    for item in items:
        remark = item.get("remarks", "")
        if WHITELIST_PATTERN.search(remark) or FREE_VPN_SKIP.search(remark):
            continue
        if FREE_VPN_MATCH.search(remark):
            out.append(item)
    return tuple(out)


def fetch_native_mihomo(token: str, client_headers: dict | None = None) -> dict:
    if yaml is None:
        raise RuntimeError("PyYAML required for mihomo merge")
    headers = dict(INTERNAL_HEADERS)
    headers.update(pick_hwid_request_headers(client_headers))
    text = fetch_text(f"{SUB_INTERNAL.rstrip('/')}/{token}/mihomo", headers)
    return yaml.safe_load(text)


def fetch_candelix_mihomo() -> dict:
    if yaml is None:
        raise RuntimeError("PyYAML required for mihomo merge")
    text = fetch_text(f"{CANDELIX_URL.rstrip('/')}/mihomo", CANDELIX_HEADERS)
    return yaml.safe_load(text)


def mihomo_name_valid(name: str) -> bool:
    text = (name or "").lower()
    return "не поддерживается" not in text and "⬇️" not in name


def xray_outbound_to_mihomo_proxy(
    ob: dict, name: str, *, dialer_proxy: str | None = None
) -> dict:
    v = ob["settings"]["vnext"][0]
    user = v["users"][0]
    ss = ob.get("streamSettings") or {}
    net = ss.get("network", "tcp")
    security = ss.get("security", "none")

    proxy: dict = {
        "name": name,
        "type": "vless",
        "server": v["address"],
        "port": int(v["port"]),
        "uuid": user["id"],
        "cipher": user.get("encryption") or "auto",
        "udp": True,
    }
    if user.get("flow"):
        proxy["flow"] = user["flow"]
    if net and net != "tcp":
        proxy["network"] = net
    if dialer_proxy:
        proxy["dialer-proxy"] = dialer_proxy

    if security == "reality":
        rs = ss.get("realitySettings") or {}
        proxy["tls"] = True
        if rs.get("serverName"):
            proxy["servername"] = rs["serverName"]
        reality_opts: dict[str, str] = {}
        if rs.get("publicKey"):
            reality_opts["public-key"] = rs["publicKey"]
        if rs.get("shortId"):
            reality_opts["short-id"] = rs["shortId"]
        if reality_opts:
            proxy["reality-opts"] = reality_opts
        if rs.get("fingerprint"):
            proxy["client-fingerprint"] = rs["fingerprint"]
    elif security == "tls":
        ts = ss.get("tlsSettings") or {}
        proxy["tls"] = True
        if ts.get("serverName"):
            proxy["servername"] = ts["serverName"]

    if net == "ws":
        ws = ss.get("wsSettings") or {}
        ws_opts: dict = {}
        if ws.get("path"):
            ws_opts["path"] = ws["path"]
        headers = ws.get("headers") or {}
        if headers.get("Host"):
            ws_opts["headers"] = {"Host": headers["Host"]}
        if ws_opts:
            proxy["ws-opts"] = ws_opts
    elif net == "grpc":
        grpc = ss.get("grpcSettings") or {}
        if grpc.get("serviceName"):
            proxy["grpc-opts"] = {"grpc-service-name": grpc["serviceName"]}
    elif net == "xhttp":
        xhttp = ss.get("xhttpSettings") or {}
        xhttp_opts = {}
        if xhttp.get("path"):
            xhttp_opts["path"] = xhttp["path"]
        if xhttp.get("host"):
            xhttp_opts["host"] = xhttp["host"]
        if xhttp.get("mode"):
            xhttp_opts["mode"] = xhttp["mode"]
        if xhttp_opts:
            proxy["xhttp-opts"] = xhttp_opts

    return proxy


def fetch_native_mihomo_proxies(
    token: str, client_headers: dict | None = None
) -> tuple[dict, dict[str, dict]]:
    """Mihomo-метаданные и нативные прокси (internal mihomo или API fallback)."""
    meta: dict = {}
    try:
        meta = fetch_native_mihomo(token, client_headers) or {}
        proxies = [
            p for p in meta.get("proxies", [])
            if mihomo_name_valid(p.get("name", ""))
        ]
        if proxies:
            by_country: dict[str, dict] = {}
            for proxy in proxies:
                country = normalize_country(proxy.get("name", ""))
                if country:
                    by_country[country] = proxy
            if by_country:
                return meta, by_country
    except Exception as exc:
        print(f"mihomo internal fetch failed for {token}: {exc}")

    try:
        satka, _ = fetch_native_json(token, client_headers)
    except Exception:
        satka = fetch_native_json_via_api(token)

    by_country = {}
    for item in satka:
        remark = item.get("remarks", "")
        if not mihomo_name_valid(remark):
            continue
        ob = get_vless_outbound(item)
        if not ob:
            continue
        country = normalize_country(remark)
        if not country:
            continue
        by_country[country] = xray_outbound_to_mihomo_proxy(ob, remark)
    return meta, by_country


def fetch_whitelist_mihomo_proxies() -> dict[int, dict]:
    use_candelix = paid_whitelist_from_candelix()
    items = fetch_paid_whitelist_json()
    prepared: dict[int, dict] = {}
    for i, item in enumerate(items, 1):
        number = whitelist_item_number(item, i)
        if paid_whitelist_from_static():
            cfg = resolve_static_whitelist_item(item)
        elif use_candelix:
            cfg = resolve_candelix_whitelist_item(item)
        else:
            cfg = resolve_working_whitelist_item(item, number, items)
        ob = whitelist_primary_outbound(cfg) or get_vless_outbound(cfg)
        if not ob:
            continue
        name = format_whitelist_direct_remark(item, number, candelix=use_candelix)
        prepared[number] = xray_outbound_to_mihomo_proxy(ob, name)
    return prepared


def build_expired_mihomo_yaml() -> str:
    if yaml is None:
        raise RuntimeError("PyYAML required")
    doc = {
        "mixed-port": 7890,
        "allow-lan": True,
        "mode": "rule",
        "log-level": "info",
        "proxies": [
            {
                "name": SUBSCRIPTION_EXPIRED_REMARK,
                "type": "vless",
                "server": "127.0.0.1",
                "port": 1,
                "uuid": "00000000-0000-0000-0000-000000000000",
                "cipher": "auto",
                "udp": True,
            }
        ],
        "proxy-groups": [
            {
                "name": PROXY_GROUP,
                "type": "select",
                "proxies": [SUBSCRIPTION_EXPIRED_REMARK],
            }
        ],
        "rules": [f"MATCH,{PROXY_GROUP}"],
    }
    return yaml.dump(doc, allow_unicode=True, sort_keys=False, width=120)


def get_vless_outbound(cfg: dict) -> dict | None:
    for ob in cfg.get("outbounds", []):
        if ob.get("protocol") == "vless":
            return ob
    return None


def get_vless_port(cfg: dict) -> int:
    ob = get_vless_outbound(cfg)
    if not ob:
        return 0
    return ob.get("settings", {}).get("vnext", [{}])[0].get("port", 0)


def find_template_cfg(satka: list, *, _bridge_fallback: bool = True) -> dict:
    """Шаблон моста: совпадает с BRIDGE (Польша:2053)."""
    usable = [
        cfg
        for cfg in satka
        if get_vless_outbound(cfg)
        and "не поддерживается" not in (cfg.get("remarks") or "").lower()
    ]
    for cfg in usable:
        if "Польша" in cfg.get("remarks", ""):
            return cfg
    for cfg in usable:
        if get_vless_port(cfg) == BRIDGE_PORT and normalize_country(cfg.get("remarks", "")):
            return cfg
    for cfg in usable:
        if normalize_country(cfg.get("remarks", "")):
            return cfg
    bridge_token = (FREE_BRIDGE_TEMPLATE_TOKEN or "").strip()
    if bridge_token and _bridge_fallback:
        try:
            api_satka = fetch_native_json_via_api(bridge_token)
            return find_template_cfg(api_satka, _bridge_fallback=False)
        except Exception as exc:
            print(f"bridge template token fallback failed: {exc}")
    if usable:
        return usable[0]
    raise RuntimeError("Не найден шаблон для моста в подписке")


def effective_bridge_endpoint() -> tuple[str, int]:
    if BRIDGE_FALLBACK_SERVER and BRIDGE_FALLBACK_PORT:
        return BRIDGE_FALLBACK_SERVER, BRIDGE_FALLBACK_PORT
    return BRIDGE_SERVER, BRIDGE_PORT


def build_bridge_json_cfg(
    template_cfg: dict,
    *,
    bridge_server: str | None = None,
    bridge_port: int | None = None,
    bridge_label: str | None = None,
) -> dict:
    ob = get_vless_outbound(template_cfg)
    if not ob:
        raise RuntimeError("У шаблона моста нет vless outbound")

    default_server, default_port = effective_bridge_endpoint()
    server = bridge_server or default_server
    port = bridge_port if bridge_port is not None else default_port
    bridge = copy.deepcopy(ob)
    bridge["tag"] = "bridge"
    v = bridge["settings"]["vnext"][0]
    v["address"] = server
    v["port"] = port
    return {
        "remarks": bridge_label or BRIDGE_NAME,
        "inbounds": copy.deepcopy(template_cfg.get("inbounds")),
        "outbounds": [
            bridge,
            {"tag": "direct", "protocol": "freedom"},
            {"tag": "block", "protocol": "blackhole"},
        ],
    }


def build_bridge_mihomo_proxy(template_proxy: dict) -> dict:
    server, port = effective_bridge_endpoint()
    proxy = copy.deepcopy(template_proxy)
    proxy["name"] = BRIDGE_INTERNAL_NAME
    proxy["hidden"] = True
    proxy["server"] = server
    proxy["port"] = port
    return proxy


def build_chain(bridge_cfg: dict, exit_cfg: dict, remark: str) -> dict | None:
    bridge_ob = get_vless_outbound(bridge_cfg)
    exit_ob = get_vless_outbound(exit_cfg)
    if not bridge_ob or not exit_ob:
        return None

    bridge = copy.deepcopy(bridge_ob)
    bridge["tag"] = "bridge"

    proxy = copy.deepcopy(exit_ob)
    proxy["tag"] = "proxy"
    proxy.setdefault("streamSettings", {})["sockopt"] = {"dialerProxy": "bridge"}

    base = exit_cfg if exit_cfg.get("inbounds") else bridge_cfg
    return {
        "remarks": remark,
        "inbounds": copy.deepcopy(base.get("inbounds")),
        "outbounds": [
            proxy,
            bridge,
            {"tag": "direct", "protocol": "freedom"},
            {"tag": "block", "protocol": "blackhole"},
        ],
    }


def index_by_country(items: list, key: str = "remarks") -> dict[str, dict]:
    out: dict[str, dict] = {}
    for item in items:
        country = normalize_country(item.get(key, ""))
        if country:
            out[country] = item
    return out



def prepare_native_lte_exit(cfg: dict, native_key: str) -> None:
    """Перенаправить exit на TCP-релей (тот же хаб, другой порт) для LTE."""
    relay_port = NATIVE_RELAY_PORTS.get(native_key)
    if not relay_port:
        return
    ob = get_vless_outbound(cfg)
    if not ob:
        return
    v = ob["settings"]["vnext"][0]
    v["address"] = RELAY_HOST
    v["port"] = relay_port


def apply_candelix_lte_tuning(exit_ob: dict | None, ref_cfg: dict | None) -> None:
    """Скопировать LTE-friendly параметры Reality с рабочего Candelix."""
    if not exit_ob or not ref_cfg:
        return
    ref_ob = get_vless_outbound(ref_cfg)
    if not ref_ob:
        return
    ref_ss = ref_ob.get("streamSettings") or {}
    ss = exit_ob.setdefault("streamSettings", {})
    ref_rs = ref_ss.get("realitySettings") or {}
    rs = ss.setdefault("realitySettings", {})
    for field in ("fingerprint", "spiderX", "shortId"):
        if ref_rs.get(field) not in (None, ""):
            rs[field] = ref_rs[field]
    if ref_rs.get("serverName") and rs.get("serverName") in (None, "www.google.com"):
        rs["serverName"] = ref_rs["serverName"]


def bridge_for_location(loc: dict, template_cfg: dict) -> dict:
    override = loc.get("bridge") or loc.get("bridge_server")
    if override:
        return build_bridge_json_cfg(
            template_cfg,
            bridge_server=override,
            bridge_port=BRIDGE_PORT,
            bridge_label=f"🌉 Мост {override}",
        )
    # Native chain: мост Finland#2 (работает и Wi-Fi, и LTE)
    return build_bridge_json_cfg(template_cfg)



# Регионы для «Белых списков» (static vless, №1–12)
WHITELIST_REGION_FLAGS = (
    "🇷🇺",
    "🇷🇺",
    "🇱🇹",
    "🇱🇻",
    "🇩🇪",
    "🇫🇮",
    "🇪🇪",
    "🌐",
    "🇷🇺",
    "🇹🇷",
    "🇳🇱",
    "🇳🇱",
)


def whitelist_flag_for_item(
    item: dict, number: int, *, candelix: bool = False
) -> str:
    """Флаг региона для белых списков."""
    if item.get("_wl_flag"):
        return item["_wl_flag"]
    if candelix:
        return WHITELIST_REGION_FLAGS[(number - 1) % len(WHITELIST_REGION_FLAGS)]
    remark = item.get("remarks", "") or item.get("name", "")
    m = REMARK_FLAG_RE.match((remark or "").strip())
    if m and m.group(1) != "🇪🇺":
        return m.group(1)
    return WHITELIST_REGION_FLAGS[(number - 1) % len(WHITELIST_REGION_FLAGS)]


def format_whitelist_direct_remark(
    item: dict, number: int, *, candelix: bool = False
) -> str:
    flag = whitelist_flag_for_item(item, number, candelix=candelix)
    is_top = number in WHITELIST_TOP_NUMBERS or bool(item.get("_wl_top"))
    if is_top:
        return f"{flag} Белые списки | ТОП #{number}"
    return f"{flag} Белые списки #{number}"


# Upstream sinful: эти IP недоступны с LTE (max.ru-обход)
WHITELIST_DEAD_ADDRESSES = frozenset({"185.86.144.101", "37.139.33.208"})
# #2/#3: CDN-peer из sinful (grpc id.pervye.ru не годится для белых списков LTE)
WHITELIST_FALLBACK_INDEX: dict[int, int] = {
    2: 6,  # yandex-cdn (#7)
    3: 7,  # vk-cdn (#8)
}

FREE_EXTRA_WHITELIST_NO = 6
FREE_EXTRA_WHITELIST_INDEX = 5
FREE_EXTRA_CANDELIX = (
    {"number": 9, "flag": "🇫🇮", "name": "Финляндия", "key": "Финляндия"},
    {"number": 15, "flag": "🇳🇱", "name": "Нидерланды", "key": "Нидерланды"},
    {"number": 10, "flag": "🇷🇺", "name": "YT Без рекламы", "key": "__yt_noads__"},
)


def whitelist_primary_outbound(cfg: dict) -> dict | None:
    for ob in cfg.get("outbounds", []):
        if ob.get("protocol") == "vless" and ob.get("tag") == "proxy":
            return ob
    return get_vless_outbound(cfg)


def vless_endpoint(ob: dict) -> tuple[str, int]:
    v = ob["settings"]["vnext"][0]
    return v.get("address", ""), int(v.get("port", 0))


def collapse_to_single_proxy(cfg: dict, proxy_ob: dict) -> None:
    proxy = copy.deepcopy(proxy_ob)
    proxy["tag"] = "proxy"
    non_vless = [
        o for o in cfg.get("outbounds", []) if o.get("protocol") != "vless"
    ]
    cfg["outbounds"] = [proxy] + non_vless


def _whitelist_outbound_rank(ob: dict) -> tuple[int, int]:
    """Приоритет для LTE: CDN xhttp → EE tcp → grpc."""
    ss = ob.get("streamSettings") or {}
    net = ss.get("network", "")
    addr, _ = vless_endpoint(ob)
    net_prio = {"xhttp": 0, "tcp": 1, "grpc": 2}.get(net, 9)
    if "vk-cdn" in addr:
        cdn_prio = 0
    elif "yandex-cdn" in addr:
        cdn_prio = 1
    else:
        cdn_prio = 2
    return net_prio, cdn_prio


def select_best_working_outbound(item: dict) -> dict | None:
    working: list[dict] = []
    for ob in item.get("outbounds", []):
        if ob.get("protocol") != "vless":
            continue
        addr, _ = vless_endpoint(ob)
        if addr not in WHITELIST_DEAD_ADDRESSES:
            working.append(ob)
    if not working:
        return None
    working.sort(key=_whitelist_outbound_rank)
    return working[0]


def resolve_working_whitelist_item(
    item: dict, number: int, all_items: tuple[dict, ...]
) -> dict:
    """Собрать рабочий конфиг: целый peer + один proxy-outbound."""
    items_list = list(all_items)

    if number == 1:
        ob = select_best_working_outbound(item)
        if ob:
            cfg = copy.deepcopy(item)
            collapse_to_single_proxy(cfg, ob)
            return cfg

    primary = whitelist_primary_outbound(item)
    if primary:
        addr, _ = vless_endpoint(primary)
        if addr not in WHITELIST_DEAD_ADDRESSES:
            cfg = copy.deepcopy(item)
            collapse_to_single_proxy(cfg, primary)
            return cfg

    fb_idx = WHITELIST_FALLBACK_INDEX.get(number)
    if fb_idx is not None and fb_idx < len(items_list):
        cfg = copy.deepcopy(items_list[fb_idx])
        ob = whitelist_primary_outbound(cfg) or get_vless_outbound(cfg)
        if ob:
            collapse_to_single_proxy(cfg, ob)
        return cfg

    return copy.deepcopy(item)


def resolve_candelix_whitelist_item(item: dict) -> dict:
    """Candelix LTE whitelist — один proxy-outbound, без sinful fallback."""
    cfg = copy.deepcopy(item)
    ob = whitelist_primary_outbound(cfg) or get_vless_outbound(cfg)
    if ob:
        collapse_to_single_proxy(cfg, ob)
    return cfg


def resolve_static_whitelist_item(item: dict) -> dict:
    """Static VLESS whitelist — напрямую, без моста."""
    return resolve_candelix_whitelist_item(item)


def discover_torrent_exit_profile(natives: dict[str, dict]) -> dict | None:
    """VLESS outbound Satka-ноды для P2P (минуя sinful proxy)."""
    for key in TORRENT_EXIT_NATIVE_KEYS:
        cfg = natives.get(key)
        if not cfg:
            continue
        ob = get_vless_outbound(cfg)
        if ob:
            return copy.deepcopy(ob)
    return None


def inject_torrent_stealth_outbound(cfg: dict, exit_ob: dict) -> str:
    """Скрытый outbound: торренты идут на Satka, не на sinful."""
    tag = TORRENT_STEALTH_TAG
    stealth = copy.deepcopy(exit_ob)
    stealth["tag"] = tag
    ss = stealth.setdefault("streamSettings", {})
    sock = ss.get("sockopt") or {}
    sock.pop("dialerProxy", None)
    if sock:
        ss["sockopt"] = sock
    else:
        ss.pop("sockopt", None)

    outbounds = cfg.setdefault("outbounds", [])
    if any(o.get("tag") == tag for o in outbounds):
        return tag

    insert_idx = len(outbounds)
    for i, ob in enumerate(outbounds):
        if ob.get("tag") == "proxy":
            insert_idx = i + 1
            break
    outbounds.insert(insert_idx, stealth)
    return tag


def torrent_stealth_outbound_tag(
    cfg: dict, natives: dict[str, dict] | None
) -> str | None:
    if not natives:
        return None
    exit_ob = discover_torrent_exit_profile(natives)
    if not exit_ob:
        return None
    return inject_torrent_stealth_outbound(cfg, exit_ob)


def fetch_torrent_exit_natives(token: str = "") -> dict[str, dict] | None:
    """Нативные ноды для скрытого P2P-exit (standalone whitelist / free)."""
    bridge_token = (TORRENT_EXIT_TEMPLATE_TOKEN or token or "").strip()
    if not bridge_token:
        return None
    try:
        satka, _ = fetch_native_json(bridge_token, None)
        return index_by_country(satka)
    except Exception as exc:
        print(f"torrent exit natives fetch failed: {exc}")
        return None


def ensure_whitelist_sniffing(cfg: dict) -> None:
    """Sniffing для whitelist — только протоколы, которые Happ/Xray понимает."""
    for inbound in cfg.get("inbounds", []):
        sniff = inbound.setdefault(
            "sniffing", {"enabled": True, "routeOnly": True, "destOverride": []}
        )
        sniff["enabled"] = True
        sniff.setdefault("routeOnly", True)
        dest = list(sniff.get("destOverride") or [])
        for proto in ("http", "tls", "quic"):
            if proto not in dest:
                dest.append(proto)
        sniff["destOverride"] = dest


def whitelist_torrent_stealth_rules(
    torrent_outbound: str,
    *,
    quic_outbound_tag: str = "proxy",
    quic_balancer_tag: str | None = None,
) -> list[dict]:
    """Правила P2P: UDP, порты, трекеры — на Satka (без protocol:bittorrent — Happ не поддерживает)."""
    rules: list[dict] = [
        {"type": "field", "domain": list(TORRENT_STEALTH_DOMAINS), "outboundTag": torrent_outbound},
    ]
    if TORRENT_STEALTH_PORTS:
        rules.append(
            {
                "type": "field",
                "port": TORRENT_STEALTH_PORTS,
                "outboundTag": torrent_outbound,
            }
        )
    # DHT/uTP/μTP — UDP, sniffing часто не ловит; QUIC :443 оставляем на proxy/balancer
    quic_rule: dict = {"type": "field", "network": "udp", "port": "443"}
    if quic_balancer_tag:
        quic_rule["balancerTag"] = quic_balancer_tag
    else:
        quic_rule["outboundTag"] = quic_outbound_tag
    rules.append(quic_rule)
    rules.append(
        {"type": "field", "network": "udp", "outboundTag": torrent_outbound}
    )
    return rules


def finalize_whitelist_cfg(
    cfg: dict,
    *,
    ping_seed: str | None = None,
    natives: dict[str, dict] | None = None,
) -> None:
    """Белые списки: IP-check и RU-приложения — direct, остальное через proxy."""
    del natives
    sanitize_routing(cfg)
    strip_whitelist_outbounds(cfg)
    rebuild_whitelist_routing(cfg)
    ensure_whitelist_sniffing(cfg)
    optimize_performance(cfg)
    if ping_seed:
        apply_fake_ping_meta(cfg, ping_seed)


def prepare_whitelist_cfg(
    item: dict,
    number: int,
    all_items: tuple[dict, ...],
    *,
    ping_seed: str | None = None,
    natives: dict[str, dict] | None = None,
    candelix: bool = False,
) -> dict:
    if paid_whitelist_from_static():
        cfg = resolve_static_whitelist_item(item)
    elif candelix:
        cfg = resolve_candelix_whitelist_item(item)
    else:
        cfg = resolve_working_whitelist_item(item, number, all_items)
    for key in ("_wl_number", "_wl_top", "_wl_flag", "_wl_label"):
        cfg.pop(key, None)
    remark = format_whitelist_direct_remark(item, number, candelix=candelix)
    cfg["remarks"] = remark
    seed = remark if ping_seed is None else ping_seed
    finalize_whitelist_cfg(cfg, ping_seed=seed, natives=natives)
    return cfg


def free_subscription_token(token: str) -> str:
    """Токен Remnawave для бесплатной подписки: пользователь или шаблон моста."""
    sub = (token or "").strip()
    if sub:
        return sub
    return (FREE_BRIDGE_TEMPLATE_TOKEN or "").strip()


def fetch_free_native_servers(
    token: str, client_headers: dict | None = None
) -> list[dict]:
    """Нативные ноды Remnawave для SatkaVPN Free (не зависят от sinful)."""
    sub_token = free_subscription_token(token)
    if not sub_token:
        return []
    has_hwid = bool(pick_hwid_request_headers(client_headers).get("x-hwid"))
    try:
        satka, hwid = fetch_native_json(sub_token, client_headers)
        if hwid.get("x-hwid-max-devices-reached") == "true":
            return []
        if satka:
            return list(satka)
    except NativeSubscriptionError as exc:
        print(f"free native internal HTTP {exc.status} for {sub_token}")
    except Exception as exc:
        print(f"free native fetch failed: {exc}")

    if has_hwid:
        return []
    try:
        return fetch_native_json_via_api(sub_token)
    except Exception as exc:
        print(f"free native API fallback failed: {exc}")
        return []


def fetch_free_bridge_template(token: str) -> dict | None:
    bridge_token = (FREE_BRIDGE_TEMPLATE_TOKEN or token or "").strip()
    if not bridge_token:
        return None
    try:
        satka, hwid = fetch_native_json(bridge_token, None)
        if hwid.get("x-hwid-max-devices-reached") == "true":
            return None
        return find_template_cfg(satka)
    except Exception as exc:
        print(f"free bridge template failed: {exc}")
        return None


def build_free_extra_servers(token: str) -> list:
    out: list[dict] = []
    wl_natives = fetch_torrent_exit_natives(token)
    wl_items = fetch_whitelist_json()
    if len(wl_items) > FREE_EXTRA_WHITELIST_INDEX:
        out.append(
            prepare_whitelist_cfg(
                wl_items[FREE_EXTRA_WHITELIST_INDEX],
                FREE_EXTRA_WHITELIST_NO,
                wl_items,
                natives=wl_natives,
            )
        )

    template = fetch_free_bridge_template(token)
    if not template:
        return out

    try:
        chains_raw = index_candelix(fetch_candelix_json())
    except Exception as exc:
        print(f"free candelix fetch failed: {exc}")
        return out

    bridge = build_bridge_json_cfg(template)
    for spec in FREE_EXTRA_CANDELIX:
        exit_cfg = chains_raw.get(spec["key"])
        if not exit_cfg:
            continue
        remark = format_remark(spec["flag"], spec["name"], number=spec["number"])
        chain = build_chain(bridge, copy.deepcopy(exit_cfg), remark)
        if not chain:
            continue
        apply_candelix_lte_tuning(get_vless_outbound(chain), exit_cfg)
        finalize_cfg(chain, ping_seed=remark)
        out.append(chain)
    return out


def append_whitelist_subset(
    result: list,
    server_no: int,
    *,
    numbers: tuple[int, ...],
    auto_pool: tuple[int, ...],
    natives: dict[str, dict] | None = None,
    remark_formatter=None,
) -> int:
    """Подмножество белых списков с автовыбором."""
    use_candelix = paid_whitelist_from_candelix()
    items = fetch_paid_whitelist_json()
    prepared: dict[int, dict] = {}
    for item in items:
        server_no += 1
        number = whitelist_item_number(item, server_no)
        if number not in numbers:
            continue
        prepared[number] = prepare_whitelist_cfg(
            item, number, items, natives=natives, candelix=use_candelix
        )
        if remark_formatter:
            remark = remark_formatter(item, number, candelix=use_candelix)
            prepared[number]["remarks"] = remark
            apply_fake_ping_meta(prepared[number], remark)

    pool_cfgs = [prepared[n] for n in auto_pool if n in prepared]
    if pool_cfgs:
        balancer = build_balancer_cfg(
            pool_cfgs,
            AUTO_WHITELIST_REMARK,
            mode="whitelist",
            natives=natives,
        )
        if balancer:
            result.append(balancer)

    for number in numbers:
        if number in prepared:
            result.append(prepared[number])
    return server_no


def append_whitelist_paid(
    result: list, server_no: int, *, natives: dict[str, dict] | None = None
) -> int:
    """Белые списки в платной подписке (static / Candelix / sinful)."""
    use_candelix = paid_whitelist_from_candelix()
    items = fetch_paid_whitelist_json()
    prepared: dict[int, dict] = {}
    for item in items:
        server_no += 1
        number = whitelist_item_number(item, server_no)
        prepared[number] = prepare_whitelist_cfg(
            item, number, items, natives=natives, candelix=use_candelix
        )

    pool_cfgs = [prepared[n] for n in WHITELIST_AUTO_POOL if n in prepared]
    if pool_cfgs:
        balancer = build_balancer_cfg(
            pool_cfgs,
            AUTO_WHITELIST_REMARK,
            mode="whitelist",
            natives=natives,
        )
        if balancer:
            result.append(balancer)

    for number in WHITELIST_NUMBERS:
        if number in prepared:
            result.append(prepared[number])
    return server_no


def index_candelix(items: list) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for item in items:
        remark = item.get("remarks", "")
        if SKIP_CANDELIX.search(remark) or SKIP_CANDELIX_RU.search(remark):
            continue
        if CANDELIX_YT_MATCH.search(remark):
            out["__yt_noads__"] = item
            continue
        country = normalize_country(remark)
        if country:
            out[country] = item
    return out


def loc_candelix_key(loc: dict) -> str:
    return loc.get("candelix_key", loc["name"])


def loc_source(loc: dict) -> str:
    if "source" in loc:
        return loc["source"]
    return "native" if loc.get("native") else "candelix"


def loc_native_key(loc: dict) -> str:
    return loc.get("native_key", loc["name"])


def build_regular_location_cfg(
    loc: dict,
    *,
    number: int,
    template_cfg: dict,
    natives: dict[str, dict],
    chains_raw: dict[str, dict],
) -> dict | None:
    remark = format_location_remark(loc["flag"], loc["name"], number=number)
    source = loc_source(loc)
    bridge = bridge_for_location(loc, template_cfg)

    if source == "native":
        key = loc_native_key(loc)
        if key not in natives:
            return None
        cfg = copy.deepcopy(natives[key])
        if loc.get("chain", False):
            if loc.get("lte_relay", True):
                prepare_native_lte_exit(cfg, key)
            chain = build_chain(bridge, cfg, remark)
            if not chain:
                return None
            ref_name = NATIVE_CANDELIX_REF.get(key, key.split()[0])
            apply_candelix_lte_tuning(
                get_vless_outbound(chain), chains_raw.get(ref_name)
            )
            finalize_regular_cfg(chain, ping_seed=remark)
            return chain
        cfg["remarks"] = remark
        finalize_regular_cfg(cfg, ping_seed=remark)
        return cfg

    ckey = loc_candelix_key(loc)
    if ckey not in chains_raw:
        return None
    exit_cfg = copy.deepcopy(chains_raw[ckey])
    chain = build_chain(bridge, exit_cfg, remark)
    if not chain:
        return None
    apply_candelix_lte_tuning(get_vless_outbound(chain), exit_cfg)
    finalize_regular_cfg(chain, ping_seed=remark)
    return chain


def merge_subscription(
    token: str, client_headers: dict | None = None
) -> tuple[list, dict[str, str]]:
    if not is_subscription_active(token):
        return [build_expired_notice_cfg()], {}

    locations = list(load_locations())
    satka, hwid_headers = fetch_native_json(token, client_headers)

    if hwid_headers.get("x-hwid-max-devices-reached") == "true":
        return satka, hwid_headers

    candelix = fetch_candelix_json()

    natives = index_by_country(satka)
    template_cfg = find_template_cfg(satka)

    chains_raw = index_candelix(candelix)

    result = []
    server_no = 0

    result.append(build_separator_cfg(SECTION_WHITELIST))
    server_no = append_whitelist_paid(result, server_no, natives=natives)

    stable, unstable_sep, unstable = split_location_sections(locations)
    stable_by_number = locations_by_number(stable)
    unstable_by_number = locations_by_number(unstable)
    prepared_regular: dict[int, dict] = {}

    for loc in stable_by_number:
        number = int(loc["number"])
        cfg = build_regular_location_cfg(
            loc,
            number=number,
            template_cfg=template_cfg,
            natives=natives,
            chains_raw=chains_raw,
        )
        if cfg:
            prepared_regular[number] = cfg
            server_no = max(server_no, number)

    result.append(build_separator_cfg(SECTION_REGULAR))

    auto_pool_cfgs = [prepared_regular[n] for n in REGULAR_AUTO_POOL if n in prepared_regular]
    if auto_pool_cfgs:
        balancer = build_balancer_cfg(
            auto_pool_cfgs,
            AUTO_LOCATION_REMARK,
            mode="regular",
        )
        if balancer:
            result.append(balancer)

    for number in REGULAR_STABLE_NUMBERS:
        if number in prepared_regular:
            result.append(prepared_regular[number])

    if unstable_sep:
        result.append(build_separator_cfg(unstable_sep["name"]))
    for loc in unstable_by_number:
        number = int(loc["number"])
        cfg = build_regular_location_cfg(
            loc,
            number=number,
            template_cfg=template_cfg,
            natives=natives,
            chains_raw=chains_raw,
        )
        if cfg:
            result.append(cfg)
            server_no = max(server_no, number)

    return result, hwid_headers


def merge_mom_subscription(
    token: str, client_headers: dict | None = None
) -> tuple[list, dict[str, str]]:
    """Тариф «Для мамы»: топ whitelist #1/#2/#4/#11 + regular #13/#15/#16/#19."""
    if not is_subscription_active(token):
        return [build_expired_notice_cfg()], {}

    locations = list(load_locations())
    satka, hwid_headers = fetch_native_json(token, client_headers)
    if hwid_headers.get("x-hwid-max-devices-reached") == "true":
        return satka, hwid_headers

    candelix = fetch_candelix_json()
    natives = index_by_country(satka)
    template_cfg = find_template_cfg(satka)
    chains_raw = index_candelix(candelix)

    result: list[dict] = []
    server_no = 0

    result.append(build_separator_cfg(SECTION_MOM_WHITELIST))
    server_no = append_whitelist_subset(
        result,
        server_no,
        numbers=MOM_WHITELIST_NUMBERS,
        auto_pool=MOM_WHITELIST_NUMBERS,
        natives=natives,
        remark_formatter=format_mom_whitelist_remark,
    )

    stable, _, _ = split_location_sections(locations)
    stable_by_number = {int(loc["number"]): loc for loc in stable}
    prepared_regular: dict[int, dict] = {}

    for number in MOM_REGULAR_NUMBERS:
        loc = stable_by_number.get(number)
        if not loc:
            continue
        cfg = build_regular_location_cfg(
            loc,
            number=number,
            template_cfg=template_cfg,
            natives=natives,
            chains_raw=chains_raw,
        )
        if not cfg:
            continue
        remark = format_mom_location_remark(loc["flag"], loc["name"], number=number)
        cfg["remarks"] = remark
        finalize_regular_cfg(cfg, ping_seed=remark)
        prepared_regular[number] = cfg
        server_no = max(server_no, number)

    result.append(build_separator_cfg(SECTION_MOM_SERVERS))

    auto_pool_cfgs = [
        prepared_regular[n] for n in MOM_REGULAR_NUMBERS if n in prepared_regular
    ]
    if auto_pool_cfgs:
        balancer = build_balancer_cfg(
            auto_pool_cfgs,
            AUTO_LOCATION_REMARK,
            mode="regular",
        )
        if balancer:
            result.append(balancer)

    for number in MOM_REGULAR_NUMBERS:
        if number in prepared_regular:
            result.append(prepared_regular[number])

    return result, hwid_headers


def merge_mom_vless_base64(
    token: str, client_headers: dict | None = None
) -> bytes:
    merged, hwid_headers = merge_mom_subscription(token, client_headers)
    return configs_to_vless_base64(merged, hwid_headers)


def merge_whitelist_subscription(token: str = "") -> list:
    if not is_subscription_active(token):
        return [build_expired_notice_cfg()]

    natives = fetch_torrent_exit_natives(token)
    items = fetch_paid_whitelist_json()
    use_candelix = paid_whitelist_from_candelix()
    prepared: dict[int, dict] = {}
    for i, item in enumerate(items, 1):
        number = whitelist_item_number(item, i)
        prepared[number] = prepare_whitelist_cfg(
            item, number, items, natives=natives, candelix=use_candelix
        )

    out: list[dict] = []
    pool_cfgs = [prepared[n] for n in WHITELIST_AUTO_POOL if n in prepared]
    if pool_cfgs:
        balancer = build_balancer_cfg(
            pool_cfgs,
            AUTO_WHITELIST_REMARK,
            mode="whitelist",
            natives=natives,
        )
        if balancer:
            out.append(balancer)
    for number in WHITELIST_NUMBERS:
        if number in prepared:
            out.append(prepared[number])
    return out


def merge_free_subscription(
    token: str = "", client_headers: dict | None = None
) -> list:
    if not is_free_subscription_active(token, client_headers):
        return [build_expired_notice_cfg()]

    native_items = fetch_free_native_servers(token, client_headers)
    sinful_items = list(fetch_free_vpn_json())
    extras = build_free_extra_servers(token)

    if not native_items and not sinful_items and not extras:
        return []

    result: list[dict] = []
    server_no = 0

    if native_items or sinful_items:
        result.append(build_separator_cfg("Бесплатные серверы"))
        for item in native_items + sinful_items:
            server_no += 1
            remark = format_free_remark(item.get("remarks", "Free"), server_no)
            cfg = copy.deepcopy(item)
            cfg["remarks"] = remark
            finalize_cfg(cfg, ping_seed=remark)
            result.append(cfg)

    if extras:
        result.append(build_separator_cfg("Дополнительно"))
        result.extend(extras)
    return result


def merge_mihomo_yaml(token: str, client_headers: dict | None = None) -> str:
    if yaml is None:
        raise RuntimeError("PyYAML required")

    if not is_subscription_active(token):
        return build_expired_mihomo_yaml()

    locations = list(load_locations())
    base, natives = fetch_native_mihomo_proxies(token, client_headers)
    cand = fetch_candelix_mihomo()

    cand_map: dict[str, dict] = {}
    for p in cand.get("proxies", []):
        name = p.get("name", "")
        if SKIP_CANDELIX.search(name) or SKIP_CANDELIX_RU.search(name):
            continue
        if CANDELIX_YT_MATCH.search(name):
            cand_map["__yt_noads__"] = p
            continue
        country = normalize_country(name)
        if country:
            cand_map[country] = p

    if natives:
        template_proxy = next(
            (p for p in natives.values() if p.get("port") == 443),
            natives.get("Германия")
            or natives.get("Польша")
            or next(iter(natives.values())),
        )
    elif cand_map:
        template_proxy = next(iter(cand_map.values()))
    else:
        wl_fallback = fetch_whitelist_mihomo_proxies()
        if not wl_fallback:
            raise ValueError("No Mihomo proxies available for subscription")
        template_proxy = next(iter(wl_fallback.values()))

    bridge_proxy = build_bridge_mihomo_proxy(template_proxy)
    ordered_proxies: list[dict] = []
    ordered_names: list[str] = []
    lb_groups: list[dict] = []

    wl_proxies = fetch_whitelist_mihomo_proxies()
    wl_prepared: dict[int, tuple[dict, str]] = {}
    for number in WHITELIST_NUMBERS:
        proxy = wl_proxies.get(number)
        if not proxy:
            continue
        remark = proxy["name"]
        wl_prepared[number] = (proxy, remark)

    wl_pool = [n for n in WHITELIST_AUTO_POOL if n in wl_prepared]
    if wl_pool:
        wl_lb_members = [wl_prepared[n][1] for n in WHITELIST_AUTO_POOL if n in wl_prepared]
        if wl_lb_members:
            lb_groups.append(
                {
                    "name": AUTO_WHITELIST_REMARK,
                    "type": "url-test",
                    "url": "http://www.gstatic.com/generate_204",
                    "interval": 300,
                    "tolerance": 50,
                    "proxies": wl_lb_members,
                }
            )
        ordered_names.append(AUTO_WHITELIST_REMARK)

    for number in WHITELIST_NUMBERS:
        if number not in wl_prepared:
            continue
        proxy, remark = wl_prepared[number]
        ordered_proxies.append(proxy)
        ordered_names.append(remark)

    stable, unstable_sep, unstable = split_location_sections(locations)
    stable_by_number = locations_by_number(stable)
    unstable_by_number = locations_by_number(unstable)
    regular_prepared: dict[int, tuple[dict, str]] = {}

    for loc in stable_by_number:
        number = int(loc["number"])
        remark = format_location_remark(loc["flag"], loc["name"], number=number)
        source = loc_source(loc)

        if source == "native":
            key = loc_native_key(loc)
            if key not in natives:
                continue
            proxy = copy.deepcopy(natives[key])
            proxy["name"] = remark
            if loc.get("chain", False):
                relay_port = NATIVE_RELAY_PORTS.get(key)
                if relay_port:
                    proxy["server"] = RELAY_HOST
                    proxy["port"] = relay_port
                proxy["dialer-proxy"] = BRIDGE_INTERNAL_NAME
            regular_prepared[number] = (proxy, remark)
        else:
            ckey = loc_candelix_key(loc)
            if ckey not in cand_map:
                continue
            proxy = copy.deepcopy(cand_map[ckey])
            proxy["name"] = remark
            proxy["dialer-proxy"] = BRIDGE_INTERNAL_NAME
            regular_prepared[number] = (proxy, remark)

    auto_pool = [n for n in REGULAR_AUTO_POOL if n in regular_prepared]
    if auto_pool:
        auto_lb_members = [
            regular_prepared[n][1] for n in REGULAR_AUTO_POOL if n in regular_prepared
        ]
        if auto_lb_members:
            lb_groups.append(
                {
                    "name": AUTO_LOCATION_REMARK,
                    "type": "url-test",
                    "url": "http://www.gstatic.com/generate_204",
                    "interval": 300,
                    "tolerance": 50,
                    "proxies": auto_lb_members,
                }
            )
        ordered_names.append(AUTO_LOCATION_REMARK)

    for number in REGULAR_STABLE_NUMBERS:
        if number not in regular_prepared:
            continue
        proxy, remark = regular_prepared[number]
        ordered_proxies.append(proxy)
        ordered_names.append(remark)

    for loc in unstable_by_number:
        number = int(loc["number"])
        remark = format_location_remark(loc["flag"], loc["name"], number=number)
        source = loc_source(loc)

        if source == "native":
            key = loc_native_key(loc)
            if key not in natives:
                continue
            proxy = copy.deepcopy(natives[key])
            proxy["name"] = remark
            if loc.get("chain", False):
                relay_port = NATIVE_RELAY_PORTS.get(key)
                if relay_port:
                    proxy["server"] = RELAY_HOST
                    proxy["port"] = relay_port
                proxy["dialer-proxy"] = BRIDGE_INTERNAL_NAME
            ordered_proxies.append(proxy)
            ordered_names.append(remark)
        else:
            ckey = loc_candelix_key(loc)
            if ckey not in cand_map:
                continue
            proxy = copy.deepcopy(cand_map[ckey])
            proxy["name"] = remark
            proxy["dialer-proxy"] = BRIDGE_INTERNAL_NAME
            ordered_proxies.append(proxy)
            ordered_names.append(remark)

    if not ordered_proxies:
        raise ValueError("No Mihomo proxies available for subscription")

    base.pop("proxy-providers", None)
    base["proxies"] = [bridge_proxy] + ordered_proxies

    groups = base.get("proxy-groups") or []
    if not groups:
        groups = [{"name": PROXY_GROUP, "type": "select", "proxies": ordered_names}]
    else:
        groups[0]["name"] = PROXY_GROUP
        groups[0].pop("use", None)
        groups[0]["proxies"] = ordered_names

    base["proxy-groups"] = lb_groups + groups
    rules = list(MIHOMO_ADBLOCK_RULES) + list(MIHOMO_WHITELIST_APP_RULES)
    rules.append(f"MATCH,{PROXY_GROUP}")
    base["rules"] = rules

    return yaml.dump(base, allow_unicode=True, sort_keys=False, width=120)


def _xray_cfg_to_mihomo_proxy(cfg: dict) -> dict | None:
    remark = cfg.get("remarks", "")
    if not remark or "не поддерживается" in remark.lower():
        return None
    ob = get_vless_outbound(cfg)
    if not ob:
        return None
    v = ob.get("settings", {}).get("vnext", [{}])[0]
    addr = v.get("address", "")
    port = v.get("port", 0)
    if not addr or addr in ("0.0.0.0",) or port <= 1:
        return None
    dialer_proxy = None
    proxy_settings = ob.get("proxySettings") or {}
    sockopt = (ob.get("streamSettings") or {}).get("sockopt") or {}
    if sockopt.get("dialerProxy") or proxy_settings.get("tag"):
        dialer_proxy = BRIDGE_INTERNAL_NAME
    return xray_outbound_to_mihomo_proxy(ob, remark, dialer_proxy=dialer_proxy)


def merge_free_mihomo_yaml(token: str, client_headers: dict | None = None) -> str:
    if yaml is None:
        raise RuntimeError("PyYAML required")

    if not is_free_subscription_active(token, client_headers):
        return build_expired_mihomo_yaml()

    items = merge_free_subscription(token, client_headers)
    proxies: list[dict] = []
    for item in items:
        proxy = _xray_cfg_to_mihomo_proxy(item)
        if proxy:
            proxies.append(proxy)

    if not proxies:
        raise ValueError("No free Mihomo proxies available")

    proxy_names = [p["name"] for p in proxies]
    auto_pick = "🚀 Автовыбор"
    cfg = {
        "mixed-port": 7890,
        "allow-lan": True,
        "mode": "rule",
        "log-level": "info",
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": auto_pick,
                "type": "url-test",
                "proxies": proxy_names,
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
                "tolerance": 50,
            },
            {
                "name": PROXY_GROUP,
                "type": "select",
                "proxies": [auto_pick] + proxy_names,
            },
        ],
        "rules": [
            "GEOSITE,cn,DIRECT",
            "GEOIP,cn,DIRECT,no-resolve",
            f"MATCH,{auto_pick}",
        ],
    }
    return yaml.dump(cfg, allow_unicode=True, sort_keys=False, width=120)


merge_happ_subscription = merge_subscription
