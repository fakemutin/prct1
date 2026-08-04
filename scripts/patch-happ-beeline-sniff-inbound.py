#!/usr/bin/env python3
"""Add sniffing inbound so fakeip works in Happ browser profiles."""
from pathlib import Path

path = Path("/opt/satkavpn/happ_merge.py")
text = path.read_text()

marker = "def optimize_beeline_xhttp_extra(cfg: dict) -> None:"

sniff_fn = '''def ensure_beeline_sniff_inbound(cfg: dict) -> None:
    """Per-profile JSON has no TUN inbound; sniffing is required for fakeip browsers."""
    if cfg.get("inbounds"):
        ensure_whitelist_sniffing(cfg)
        return
    cfg["inbounds"] = [
        {
            "tag": "sniff-in",
            "port": 10853,
            "listen": "127.0.0.1",
            "protocol": "socks",
            "settings": {"auth": "noauth", "udp": True},
            "sniffing": {
                "enabled": True,
                "routeOnly": True,
                "destOverride": ["http", "tls", "quic"],
            },
        }
    ]


'''

if "def ensure_beeline_sniff_inbound" in text:
    print("sniff inbound already present")
else:
    if marker not in text:
        raise SystemExit("marker not found")
    text = text.replace(marker, sniff_fn + marker)

old_call = "    ensure_whitelist_sniffing(cfg)\n    optimize_beeline_xhttp_extra(cfg)"
new_call = "    ensure_beeline_sniff_inbound(cfg)\n    optimize_beeline_xhttp_extra(cfg)"

if old_call not in text:
    if new_call in text:
        print("call already updated")
    else:
        raise SystemExit("finalize call pattern not found")
else:
    text = text.replace(old_call, new_call)

path.write_text(text)
print("sniff inbound patch OK")
