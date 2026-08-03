#!/usr/bin/env python3
"""DNS via proxy + full tunnel routing for Beeline LTE (browser needs DNS; Telegram uses fixed IPs)."""
from pathlib import Path

path = Path("/opt/satkavpn/happ_merge.py")
text = path.read_text()

helper = '''

def finalize_beeline_tunnel_cfg(cfg: dict) -> None:
    """LTE Beeline: DNS + all traffic through CDN tunnel."""
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
    }
'''

if "def finalize_beeline_tunnel_cfg" not in text:
    raise SystemExit("finalize_beeline_tunnel_cfg already applied or base file changed")

print("already applied or run on server via /tmp/fix_beeline_dns.py")
