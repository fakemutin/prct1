#!/usr/bin/env python3
"""YouTube adblock v2: sniffing + DNS block + Happ routing for whitelist."""
import re
from pathlib import Path

path = Path("/opt/satkavpn/happ_merge.py")
text = path.read_text()

MARKER = "YOUTUBE_ADBLOCK_V2"

if MARKER in text:
    print("youtube-adblock-v2 already applied")
    raise SystemExit(0)

# Expand YOUTUBE block if v1 marker present
yt_extra = '''    "full:youtube.com/get_midroll_info",
    "full:www.youtube.com/get_midroll_info",
    "full:m.youtube.com/get_midroll_info",
    "full:youtube.com/initplayback",
    "full:www.youtube.com/initplayback",
    "domain:redirector.googlevideo.com",
    "domain:redirector.c.youtube.com",'''

if "get_midroll_info" not in text and '"full:m.youtube.com/ptracking"' in text:
    text = text.replace(
        '"full:m.youtube.com/ptracking",',
        '"full:m.youtube.com/ptracking",\n' + yt_extra,
        1,
    )

# MIHOMO URL-REGEX
if "URL-REGEX" not in text and "MIHOMO_ADBLOCK_RULES" in text:
    text = text.replace(
        '    "DOMAIN-KEYWORD,adservice,REJECT",\n]',
        '    "DOMAIN-KEYWORD,adservice,REJECT",\n'
        '    "URL-REGEX,(?i)^https?://([^/]+\\\\.)?youtube\\\\.com/(pagead|api/stats/ads|ptracking|get_midroll),REJECT",\n'
        '    "URL-REGEX,(?i)^https?://([^/]+\\\\.)?googlevideo\\\\.com/.*(oad=|cmo=ad|source=oad),REJECT",\n'
        ']',
        1,
    )

HELPER_BLOCK = '''
ADBLOCK_DNS_TAG = "adblock-dns"


def is_beeline_cfg(cfg: dict) -> bool:
    remark = cfg.get("remarks", "") or ""
    if BEELINE_WHITELIST_REMARK in remark:
        return True
    blob = json.dumps(cfg, ensure_ascii=False, default=str)
    return any(
        m in blob
        for m in (
            "noe0mevhvk.a.trbcdn.net",
            "bee-he.satkaconnect",
            "wr6wsz097v.a.trbcdn.net",
        )
    )


def ensure_adblock_sniffing(cfg: dict) -> None:
    """TLS/HTTP/QUIC sniff — без этого domain-правила на YouTube не работают."""
    sniffing = {
        "enabled": True,
        "routeOnly": True,
        "destOverride": ["http", "tls", "quic"],
    }
    inbounds = cfg.get("inbounds")
    if not inbounds:
        cfg["inbounds"] = [
            {
                "tag": "sniff-in",
                "protocol": "dokodemo-door",
                "listen": "127.0.0.1",
                "port": 1088,
                "settings": {"network": "tcp,udp", "followRedirect": True},
                "sniffing": sniffing,
            }
        ]
        return
    for inbound in inbounds:
        sniff = inbound.setdefault("sniffing", {})
        sniff["enabled"] = True
        sniff.setdefault("routeOnly", True)
        dest = list(sniff.get("destOverride") or [])
        for proto in ("http", "tls", "quic"):
            if proto not in dest:
                dest.append(proto)
        sniff["destOverride"] = dest


def apply_adblock_dns(cfg: dict) -> None:
    """DNS-level block для рекламных доменов."""
    dns = cfg.setdefault("dns", {})
    servers = dns.get("servers") or ["1.1.1.1"]
    if not isinstance(servers, list):
        servers = [servers]
    new_servers: list = []
    has_block = False
    has_remote = False
    for s in servers:
        if isinstance(s, dict):
            tag = s.get("tag")
            if tag == ADBLOCK_DNS_TAG:
                has_block = True
            else:
                has_remote = True
            new_servers.append(s)
        else:
            has_remote = True
            new_servers.append(s)
    if not has_block:
        new_servers.append({"tag": ADBLOCK_DNS_TAG, "address": "rcode://success"})
    if not has_remote:
        new_servers.insert(
            0, {"tag": "dns-remote", "address": "1.1.1.1", "detour": "proxy"}
        )
    dns["servers"] = new_servers
    dns_domains: list[str] = []
    for entry in REGULAR_ADBLOCK_DOMAINS:
        if entry.startswith("domain:"):
            dns_domains.append(entry[7:])
        elif entry.startswith("full:"):
            host = entry[5:].split("/", 1)[0]
            if host:
                dns_domains.append(host)
    dns_domains = list(dict.fromkeys(dns_domains))
    rules = list(dns.get("rules") or [])
    if not any(
        isinstance(r, dict) and r.get("server") == ADBLOCK_DNS_TAG for r in rules
    ):
        rules.insert(0, {"domain": dns_domains, "server": ADBLOCK_DNS_TAG})
    dns["rules"] = rules
    dns.setdefault("queryStrategy", "UseIPv4")


def finalize_adblock_layer(cfg: dict) -> None:
    """Sniff + DNS block (все серверы кроме Beeline)."""
    if is_beeline_cfg(cfg):
        return
    ensure_adblock_sniffing(cfg)
    apply_adblock_dns(cfg)

# YOUTUBE_ADBLOCK_V2
'''

if "def finalize_adblock_layer" not in text:
    anchor = "MIHOMO_WHITELIST_APP_RULES = ["
    if anchor not in text:
        raise SystemExit("MIHOMO_WHITELIST_APP_RULES anchor not found")
    text = text.replace(anchor, HELPER_BLOCK + anchor, 1)

# finalize_regular_cfg
old_reg = '''def finalize_regular_cfg(cfg: dict, *, ping_seed: str | None = None) -> None:
    sanitize_routing(cfg)
    rebuild_regular_routing(cfg)
    optimize_performance(cfg)
    if ping_seed:'''
new_reg = '''def finalize_regular_cfg(cfg: dict, *, ping_seed: str | None = None) -> None:
    sanitize_routing(cfg)
    rebuild_regular_routing(cfg)
    optimize_performance(cfg)
    finalize_adblock_layer(cfg)
    if ping_seed:'''
if old_reg in text:
    text = text.replace(old_reg, new_reg)

# finalize_cfg
old_fc = '''def finalize_cfg(cfg: dict, *, ping_seed: str | None = None) -> None:
    sanitize_routing(cfg)
    rebuild_safe_routing(cfg)
    optimize_performance(cfg)
    if ping_seed:'''
new_fc = '''def finalize_cfg(cfg: dict, *, ping_seed: str | None = None) -> None:
    sanitize_routing(cfg)
    rebuild_safe_routing(cfg)
    optimize_performance(cfg)
    finalize_adblock_layer(cfg)
    if ping_seed:'''
if old_fc in text:
    text = text.replace(old_fc, new_fc)

# finalize_whitelist_cfg
old_wl = '''    rebuild_whitelist_routing(cfg)
    ensure_whitelist_sniffing(cfg)
    optimize_performance(cfg)
    if ping_seed:'''
new_wl = '''    rebuild_whitelist_routing(cfg)
    ensure_whitelist_sniffing(cfg)
    optimize_performance(cfg)
    finalize_adblock_layer(cfg)
    if ping_seed:'''
if old_wl in text:
    text = text.replace(old_wl, new_wl)

# build_balancer_cfg
old_bal = '''    optimize_performance(result)
    apply_fake_ping_meta(result, remark)
    return result


def normalize_country'''
new_bal = '''    optimize_performance(result)
    finalize_adblock_layer(result)
    apply_fake_ping_meta(result, remark)
    return result


def normalize_country'''
if old_bal in text:
    text = text.replace(old_bal, new_bal)

# catch-all proxy in regular routing
if '"network": "tcp,udp", "outboundTag": "proxy"' not in text.split(
    "def rebuild_regular_routing", 1
)[1].split("def ", 2)[0]:
    text = text.replace(
        '{"type": "field", "protocol": ["bittorrent"], "outboundTag": "direct"},\n        ],\n    }\n\n\ndef finalize_regular_cfg',
        '{"type": "field", "protocol": ["bittorrent"], "outboundTag": "direct"},\n'
        '            {"type": "field", "network": "tcp,udp", "outboundTag": "proxy"},\n'
        '        ],\n    }\n\n\ndef finalize_regular_cfg',
        1,
    )

path.write_text(text)
print("youtube-adblock-v2 patch OK")

# happ-merge-server whitelist routing
server_path = Path("/opt/satkavpn/happ-merge-server.py")
if server_path.exists():
    st = server_path.read_text()
    st = re.sub(
        r'"whitelist":\s*\{[^}]*"routing":\s*False',
        '"whitelist": {\n        "title": "SatkaVPN Whitelist",\n'
        '        "announce": "@satkavpnsupport — платная подписка «Белые списки»",\n'
        '        "routing": True',
        st,
        count=1,
    )
    if '"routing": True' in st.split("whitelist", 1)[1][:200]:
        server_path.write_text(st)
        print("happ-merge-server whitelist routing=True")
