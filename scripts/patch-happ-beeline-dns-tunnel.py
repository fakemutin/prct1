#!/usr/bin/env python3
from pathlib import Path

path = Path("/opt/satkavpn/happ_merge.py")
text = path.read_text()

helper = '''

def finalize_beeline_tunnel_cfg(cfg: dict) -> None:
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
    }
'''

if "def finalize_beeline_tunnel_cfg" not in text:
    text = text.replace(
        "def prepare_beeline_whitelist_cfg(native_cfg: dict) -> dict:",
        helper + "\ndef prepare_beeline_whitelist_cfg(native_cfg: dict) -> dict:",
    )

old = '''    cfg.pop("dns", None)
    cfg.pop("routing", None)
    cfg.pop("burstObservatory", None)
    cfg.pop("observatory", None)
    apply_beeline_client_tls(cfg)
    # real ping only for beeline LTE
    pass  # apply_fake_ping_meta removed
    return cfg'''

new = '''    cfg.pop("dns", None)
    cfg.pop("routing", None)
    cfg.pop("burstObservatory", None)
    cfg.pop("observatory", None)
    apply_beeline_client_tls(cfg)
    finalize_beeline_tunnel_cfg(cfg)
    return cfg'''

if old not in text:
    raise SystemExit("prepare_beeline block not found")
text = text.replace(old, new)

path.write_text(text)
print("dns/tunnel patch OK")
