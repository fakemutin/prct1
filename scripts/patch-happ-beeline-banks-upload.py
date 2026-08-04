#!/usr/bin/env python3
"""Banks: direct routing + real DNS; upload: maxConnections xmux + larger POST bodies."""
from pathlib import Path

path = Path("/opt/satkavpn/happ_merge.py")
text = path.read_text()

# Extra bank domains (WHITELIST_APP_DIRECT_DOMAINS already has Sber/Ozon/etc.)
extra_banks_marker = "BEELINE_TECH_DOMAIN = os.environ.get"
extra_banks_block = '''BEELINE_EXTRA_BANK_DOMAINS = [
    "domain:tinkoff.ru",
    "domain:tbank.ru",
    "domain:tbankonline.ru",
    "domain:vtb.ru",
    "domain:online.vtb.ru",
    "domain:alfabank.ru",
    "domain:alfabank.com",
    "domain:raiffeisen.ru",
    "domain:yoomoney.ru",
    "domain:nspk.ru",
    "domain:sbp.nspk.ru",
    "domain:rosbank.ru",
    "domain:open.ru",
    "domain:gosuslugi.ru",
    "domain:esia.gosuslugi.ru",
    "domain:psbank.ru",
    "domain:homecredit.ru",
    "domain:rencredit.ru",
    "domain:sovcombank.ru",
    "domain:uralsib.ru",
    "domain:akbars.ru",
    "domain:modulbank.ru",
    "domain:tochka.com",
    "domain:banki.ru",
]

'''

if "BEELINE_EXTRA_BANK_DOMAINS" not in text:
    if extra_banks_marker not in text:
        raise SystemExit("BEELINE_TECH_DOMAIN marker not found")
    text = text.replace(extra_banks_marker, extra_banks_block + extra_banks_marker)

helper_marker = "def ensure_beeline_sniff_inbound(cfg: dict) -> None:"
helper_fn = '''def beeline_direct_domain_names() -> list[str]:
    """Plain hostnames for DNS/routing direct (banks, RU apps, IP-check)."""
    names: list[str] = []
    for entry in (
        WHITELIST_APP_DIRECT_DOMAINS
        + BEELINE_EXTRA_BANK_DOMAINS
        + WHITELIST_IP_CHECK_DOMAINS
    ):
        if entry.startswith("domain:"):
            names.append(entry[7:])
        else:
            names.append(entry)
    return names


'''

if "def beeline_direct_domain_names" not in text:
    if helper_marker not in text:
        raise SystemExit("ensure_beeline_sniff_inbound marker not found")
    text = text.replace(helper_marker, helper_fn + helper_marker)

old_optimize = '''def optimize_beeline_xhttp_extra(cfg: dict) -> None:
    """High throughput xmux; keep CDN padding obfs keys."""
    ob = get_vless_outbound(cfg) or get_user_vless_outbound(cfg)
    if not ob:
        return
    xh = ob.get("streamSettings", {}).get("xhttpSettings", {})
    extra = xh.get("extra")
    if not isinstance(extra, dict):
        return
    extra["xmux"] = {
        "maxConcurrency": "16",
        "hMaxRequestTimes": "300-600",
        "hMaxReusableSecs": "900-1800",
    }
    extra.setdefault("xPaddingBytes", "50-150")
    extra.setdefault("xPaddingObfsMode", True)
    extra.setdefault("xPaddingMethod", "tokenish")
    extra.setdefault("xPaddingHeader", "X-Api-Key")
    extra.setdefault("xPaddingPlacement", "header")
    extra["scMinPostsIntervalMs"] = "1-2"'''

new_optimize = '''def optimize_beeline_xhttp_extra(cfg: dict) -> None:
    """Upload: parallel connections + large POST bodies; keep CDN padding obfs."""
    ob = get_vless_outbound(cfg) or get_user_vless_outbound(cfg)
    if not ob:
        return
    xh = ob.get("streamSettings", {}).get("xhttpSettings", {})
    extra = xh.get("extra")
    if not isinstance(extra, dict):
        return
    # maxConnections only (not with maxConcurrency) — better packet-up upload
    extra["xmux"] = {
        "maxConnections": "12",
        "hMaxRequestTimes": "400-800",
        "hMaxReusableSecs": "1200-2400",
        "hKeepAlivePeriod": -1,
    }
    extra.setdefault("xPaddingBytes", "40-100")
    extra.setdefault("xPaddingObfsMode", True)
    extra.setdefault("xPaddingMethod", "tokenish")
    extra.setdefault("xPaddingHeader", "X-Api-Key")
    extra.setdefault("xPaddingPlacement", "header")
    extra["scMinPostsIntervalMs"] = "0-1"
    extra["scMaxEachPostBytes"] = "2000000"
    extra["scMaxBufferedPosts"] = 64'''

old_finalize = '''def finalize_beeline_tunnel_cfg(cfg: dict) -> None:
    """LTE Beeline: fakeip for browsers + mux tuning; Telegram keeps working on IPs."""
    strip_whitelist_outbounds(cfg)
    ensure_block_outbound(cfg)
    ensure_beeline_sniff_inbound(cfg)
    optimize_beeline_xhttp_extra(cfg)
    for ob in cfg.get("outbounds", []):
        if ob.get("tag") == "proxy" and ob.get("protocol") == "vless":
            ss = ob.setdefault("streamSettings", {})
            sock = ss.setdefault("sockopt", {})
            sock["tcpFastOpen"] = True
            sock["tcpNoDelay"] = True
            sock["domainStrategy"] = "UseIPv4"
            sock["tcpKeepAliveInterval"] = 30
    cfg["dns"] = {
        "servers": [
            {
                "tag": "remote-dns",
                "address": "https://1.1.1.1/dns-query",
                "detour": "proxy",
            },
            {
                "tag": "fakeip",
                "address": "fakeip",
            },
        ],
        "rules": [
            {
                "queryType": ["A", "AAAA"],
                "server": "fakeip",
            }
        ],
        "fakeip": {
            "ipPool": "198.18.0.0/15",
            "poolType": "IPv4",
        },
        "queryStrategy": "UseIPv4",
        "disableFallback": True,
    }
    cfg["routing"] = {
        "domainStrategy": "IPIfNonMatch",
        "rules": [
            {"type": "field", "ip": list(PRIVATE_CIDRS), "outboundTag": "direct"},
            {"type": "field", "ip": ["198.18.0.0/15"], "outboundTag": "proxy"},
            {"type": "field", "network": "udp", "port": "443", "outboundTag": "block"},
            {"type": "field", "network": "tcp,udp", "outboundTag": "proxy"},
        ],
    }'''

new_finalize = '''def finalize_beeline_tunnel_cfg(cfg: dict) -> None:
    """LTE Beeline: fakeip browsers, banks direct + real DNS, mux upload tuning."""
    strip_whitelist_outbounds(cfg)
    ensure_block_outbound(cfg)
    ensure_direct_outbound(cfg)
    ensure_beeline_sniff_inbound(cfg)
    optimize_beeline_xhttp_extra(cfg)
    direct_names = beeline_direct_domain_names()
    for ob in cfg.get("outbounds", []):
        if ob.get("tag") == "proxy" and ob.get("protocol") == "vless":
            ss = ob.setdefault("streamSettings", {})
            sock = ss.setdefault("sockopt", {})
            sock["tcpFastOpen"] = True
            sock["tcpNoDelay"] = True
            sock["domainStrategy"] = "UseIPv4"
            sock["tcpKeepAliveInterval"] = 30
    cfg["dns"] = {
        "servers": [
            {"tag": "direct-dns", "address": "local"},
            {"tag": "remote-dns", "address": "https://1.1.1.1/dns-query", "detour": "proxy"},
            {"tag": "fakeip", "address": "fakeip"},
        ],
        "rules": [
            {"domain": direct_names, "server": "direct-dns"},
            {"queryType": ["A", "AAAA"], "server": "fakeip"},
        ],
        "fakeip": {"ipPool": "198.18.0.0/15", "poolType": "IPv4"},
        "queryStrategy": "UseIPv4",
        "disableFallback": True,
    }
    cfg["routing"] = {
        "domainStrategy": "IPIfNonMatch",
        "rules": [
            {"type": "field", "ip": list(PRIVATE_CIDRS), "outboundTag": "direct"},
            *_whitelist_direct_bypass_rules(),
            {"type": "field", "ip": ["198.18.0.0/15"], "outboundTag": "proxy"},
            {"type": "field", "network": "udp", "port": "443", "outboundTag": "block"},
            {"type": "field", "network": "tcp,udp", "outboundTag": "proxy"},
        ],
    }'''

if old_optimize not in text:
  if "maxConnections" in text and "beeline_direct_domain_names" in text:
      print("banks-upload already applied")
      path.write_text(text)
      raise SystemExit(0)
  raise SystemExit("optimize block not found")

text = text.replace(old_optimize, new_optimize)
if old_finalize not in text:
    raise SystemExit("finalize block not found")
text = text.replace(old_finalize, new_finalize)

path.write_text(text)
print("banks-upload patch OK")
