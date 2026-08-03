#!/usr/bin/env python3
"""Align Beeline client cfg with CDN guide: UDP DNS via tunnel, guide xmux/buffer tuning."""
from pathlib import Path

path = Path("/opt/satkavpn/happ_merge.py")
text = path.read_text()

old_optimize = '''def optimize_beeline_xhttp_extra(cfg: dict) -> None:
    """Stable xmux; keep CDN padding obfs (no maxConnections — breaks Happ/Safari)."""
    ob = get_vless_outbound(cfg) or get_user_vless_outbound(cfg)
    if not ob:
        return
    xh = ob.get("streamSettings", {}).get("xhttpSettings", {})
    extra = xh.get("extra")
    if not isinstance(extra, dict):
        return
    extra["xmux"] = {
        "maxConcurrency": "8",
        "hMaxRequestTimes": "300-600",
        "hMaxReusableSecs": "900-1800",
    }
    extra.setdefault("xPaddingBytes", "50-150")
    extra.setdefault("xPaddingObfsMode", True)
    extra.setdefault("xPaddingMethod", "tokenish")
    extra.setdefault("xPaddingHeader", "X-Api-Key")
    extra.setdefault("xPaddingPlacement", "header")
    extra["scMinPostsIntervalMs"] = "2-4"'''

new_optimize = '''def optimize_beeline_xhttp_extra(cfg: dict) -> None:
    """Beeline CDN guide: xmux 1, 3MB posts, sc interval 5-10ms (no maxConnections)."""
    ob = get_vless_outbound(cfg) or get_user_vless_outbound(cfg)
    if not ob:
        return
    xh = ob.get("streamSettings", {}).get("xhttpSettings", {})
    if not isinstance(xh, dict):
        return
    extra = xh.get("extra")
    if not isinstance(extra, dict):
        extra = {}
        xh["extra"] = extra
    extra["xmux"] = {"maxConcurrency": "1"}
    extra.setdefault("xPaddingBytes", "50-150")
    extra.setdefault("xPaddingObfsMode", True)
    extra.setdefault("xPaddingMethod", "tokenish")
    extra.setdefault("xPaddingHeader", "X-Api-Key")
    extra.setdefault("xPaddingPlacement", "header")
    extra["scMinPostsIntervalMs"] = "5-10"
    extra["scMaxEachPostBytes"] = 3000000
    extra["scMaxBufferedPosts"] = 100
    xh["scMaxBufferedPosts"] = 100
    xh["scMaxEachPostBytes"] = 3000000
    xh["scMaxConcurrentPosts"] = 10
    xh["scMinPostsIntervalMs"] = 5
    xh["noSSEHeader"] = True
    xh["noGRPCHeader"] = True
    xh["serverMaxHeaderBytes"] = 32768'''

old_finalize = '''def finalize_beeline_tunnel_cfg(cfg: dict) -> None:
    """LTE Beeline: DoH for browser; banks/apps direct with real DNS (no fakeip)."""
    strip_whitelist_outbounds(cfg)
    ensure_block_outbound(cfg)
    ensure_direct_outbound(cfg)
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
            {"tag": "remote-dns", "address": "https://1.1.1.1/dns-query", "detour": "proxy"},
            {"tag": "direct-dns", "address": "1.1.1.1"},
        ],
        "rules": [
            {"domain": direct_names, "server": "direct-dns"},
        ],
        "queryStrategy": "UseIPv4",
        "disableFallback": True,
    }
    cfg["routing"] = {
        "domainStrategy": "IPIfNonMatch",
        "rules": [
            {"type": "field", "ip": list(PRIVATE_CIDRS), "outboundTag": "direct"},
            *_whitelist_direct_bypass_rules(),
            {"type": "field", "network": "udp", "port": "443", "outboundTag": "block"},
            {"type": "field", "network": "tcp,udp", "outboundTag": "proxy"},
        ],
    }'''

new_finalize = '''def finalize_beeline_tunnel_cfg(cfg: dict) -> None:
    """LTE Beeline: UDP DNS via tunnel (fast browser); banks direct; guide xhttp tuning."""
    strip_whitelist_outbounds(cfg)
    ensure_block_outbound(cfg)
    ensure_direct_outbound(cfg)
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
            {"tag": "remote-dns", "address": "1.1.1.1", "detour": "proxy"},
            {"tag": "remote-dns2", "address": "8.8.8.8", "detour": "proxy"},
            {"tag": "direct-dns", "address": "1.1.1.1"},
        ],
        "rules": [
            {"domain": direct_names, "server": "direct-dns"},
        ],
        "queryStrategy": "UseIPv4",
        "disableFallback": True,
        "disableCache": False,
    }
    cfg["routing"] = {
        "domainStrategy": "IPIfNonMatch",
        "rules": [
            {"type": "field", "ip": list(PRIVATE_CIDRS), "outboundTag": "direct"},
            *_whitelist_direct_bypass_rules(),
            {"type": "field", "network": "udp", "port": "443", "outboundTag": "block"},
            {"type": "field", "network": "tcp,udp", "outboundTag": "proxy"},
        ],
    }'''

if "UDP DNS via tunnel" in text:
    print("guide-speed already applied")
    raise SystemExit(0)

if old_optimize not in text:
    raise SystemExit("optimize_beeline_xhttp_extra block not found")
if old_finalize not in text:
    raise SystemExit("finalize_beeline_tunnel_cfg block not found")

text = text.replace(old_optimize, new_optimize)
text = text.replace(old_finalize, new_finalize)
path.write_text(text)
print("guide-speed patch OK")
