#!/usr/bin/env python3
"""Browser speed: fakeip DNS + sniffing + aggressive xmux (keeps padding obfs)."""
from pathlib import Path

path = Path("/opt/satkavpn/happ_merge.py")
text = path.read_text()

old_optimize = '''def optimize_beeline_xhttp_extra(cfg: dict) -> None:
    """Raise xmux concurrency; keep CDN padding (do not strip obfs keys)."""
    ob = get_vless_outbound(cfg) or get_user_vless_outbound(cfg)
    if not ob:
        return
    xh = ob.get("streamSettings", {}).get("xhttpSettings", {})
    extra = xh.get("extra")
    if not isinstance(extra, dict):
        return
    extra["xmux"] = {"maxConcurrency": "8"}
    extra.setdefault("xPaddingBytes", "50-150")
    extra.setdefault("xPaddingObfsMode", True)
    extra.setdefault("xPaddingMethod", "tokenish")
    extra.setdefault("xPaddingHeader", "X-Api-Key")
    extra.setdefault("xPaddingPlacement", "header")
    extra["scMinPostsIntervalMs"] = "2-4"'''

new_optimize = '''def optimize_beeline_xhttp_extra(cfg: dict) -> None:
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

old_finalize = '''def finalize_beeline_tunnel_cfg(cfg: dict) -> None:
    """LTE Beeline: fast mux + DoH DNS through tunnel (browser + Telegram)."""
    strip_whitelist_outbounds(cfg)
    ensure_block_outbound(cfg)
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
        "servers": [{"address": "https://1.1.1.1/dns-query", "detour": "proxy"}],
        "queryStrategy": "UseIPv4",
        "disableFallback": True,
        "disableCache": False,
    }
    cfg["routing"] = {
        "domainStrategy": "IPIfNonMatch",
        "rules": [
            {"type": "field", "ip": list(PRIVATE_CIDRS), "outboundTag": "direct"},
            {"type": "field", "network": "udp", "port": "443", "outboundTag": "block"},
            {"type": "field", "network": "tcp,udp", "outboundTag": "proxy"},
        ],
    }'''

new_finalize = '''def finalize_beeline_tunnel_cfg(cfg: dict) -> None:
    """LTE Beeline: fakeip for browsers + mux tuning; Telegram keeps working on IPs."""
    strip_whitelist_outbounds(cfg)
    ensure_block_outbound(cfg)
    ensure_whitelist_sniffing(cfg)
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

if "fakeip" in text and "hMaxRequestTimes" in text and "maxConcurrency\": \"16\"" in text:
    print("browser-speed already applied")
    raise SystemExit(0)

if old_optimize not in text:
    raise SystemExit("optimize_beeline_xhttp_extra block not found")
if old_finalize not in text:
    raise SystemExit("finalize_beeline_tunnel_cfg block not found")

text = text.replace(old_optimize, new_optimize)
text = text.replace(old_finalize, new_finalize)
path.write_text(text)
print("browser-speed patch OK")
