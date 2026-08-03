#!/usr/bin/env python3
"""Speed optimizations for Beeline LTE tunnel."""
from pathlib import Path

path = Path("/opt/satkavpn/happ_merge.py")
text = path.read_text()

old_finalize = '''def finalize_beeline_tunnel_cfg(cfg: dict) -> None:
    """LTE Beeline: DNS + all traffic through CDN tunnel (browser needs DNS; Telegram uses fixed IPs)."""
    strip_whitelist_outbounds(cfg)
    ensure_block_outbound(cfg)
    for ob in cfg.get("outbounds", []):
        if ob.get("tag") == "proxy" and ob.get("protocol") == "vless":
            ss = ob.setdefault("streamSettings", {})
            sock = ss.setdefault("sockopt", {})
            sock["tcpFastOpen"] = True
            sock["tcpNoDelay"] = True
            sock["domainStrategy"] = "UseIPv4"
    cfg["dns"] = {
        "servers": [
            {"address": "https://1.1.1.1/dns-query", "detour": "proxy"},
            {"address": "https://8.8.8.8/dns-query", "detour": "proxy"},
        ],
        "queryStrategy": "UseIPv4",
        "disableFallback": True,
    }
    cfg["routing"] = {
        "domainStrategy": "IPIfNonMatch",
        "rules": [
            {"type": "field", "ip": list(PRIVATE_CIDRS), "outboundTag": "direct"},
            {"type": "field", "network": "udp", "port": "443", "outboundTag": "block"},
            {"type": "field", "network": "tcp,udp", "outboundTag": "proxy"},
        ],
    }'''

new_finalize = '''def optimize_beeline_xhttp_extra(cfg: dict) -> None:
    """Lower xhttp overhead: more mux concurrency, no padding delays."""
    ob = get_vless_outbound(cfg) or get_user_vless_outbound(cfg)
    if not ob:
        return
    xh = ob.get("streamSettings", {}).get("xhttpSettings", {})
    extra = xh.get("extra")
    if not isinstance(extra, dict):
        return
    extra["xmux"] = {"maxConcurrency": "32", "maxConnections": "16"}
    extra["xPaddingBytes"] = "0-0"
    for k in ("xPaddingObfsMode", "xPaddingMethod", "xPaddingHeader", "xPaddingPlacement"):
        extra.pop(k, None)
    extra["scMinPostsIntervalMs"] = "0-0"


def finalize_beeline_tunnel_cfg(cfg: dict) -> None:
    """LTE Beeline: fast DNS + full tunnel through CDN."""
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
        "servers": [{"address": "1.1.1.1", "detour": "proxy"}],
        "queryStrategy": "UseIPv4",
        "disableCache": False,
    }
    cfg["routing"] = {
        "domainStrategy": "AsIs",
        "rules": [
            {"type": "field", "ip": list(PRIVATE_CIDRS), "outboundTag": "direct"},
            {"type": "field", "network": "udp", "port": "443", "outboundTag": "block"},
            {"type": "field", "network": "tcp,udp", "outboundTag": "proxy"},
        ],
    }'''

if old_finalize not in text:
    raise SystemExit("finalize_beeline_tunnel_cfg block not found")
text = text.replace(old_finalize, new_finalize)

# TLS: allow HTTP/1.1 fallback for less overhead on small requests
text = text.replace(
    '        "alpn": ["h2"],',
    '        "alpn": ["h2", "http/1.1"],',
    1,
)

path.write_text(text)
print("speed patch OK")
