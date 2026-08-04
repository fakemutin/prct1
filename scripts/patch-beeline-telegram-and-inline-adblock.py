#!/usr/bin/env python3
"""Beeline Telegram/browser fix + inline YouTube adblock (no Happ routing profile)."""
from pathlib import Path

path = Path("/opt/satkavpn/happ_merge.py")
text = path.read_text()

# 1) UDP 443 block -> proxy everywhere in Beeline routing
text = text.replace(
    '{"type": "field", "network": "udp", "port": "443", "outboundTag": "block"}',
    '{"type": "field", "network": "udp", "port": "443", "outboundTag": "proxy"}',
)
print("UDP 443: block -> proxy")

# 2) Remove old broken finalize_beeline_tunnel_cfg if present (replaced by repo version)
import re

old_tunnel = re.search(
    r"def finalize_beeline_tunnel_cfg\(cfg: dict\).*?(?=\ndef [a-z_])",
    text,
    re.S,
)
if old_tunnel and "rebuild_beeline_whitelist_routing(cfg)" not in old_tunnel.group(0):
    print("WARN: old finalize_beeline_tunnel_cfg still on server — copy full happ_merge.py from repo")

# 3) HAPP_ROUTING default off
text = text.replace(
    "HAPP_ROUTING = os.environ.get(\"HAPP_ROUTING\") or build_happ_routing_url()",
    "HAPP_ROUTING = os.environ.get(\"HAPP_ROUTING\", \"\").strip()",
)

path.write_text(text)
print("inline adblock / routing header patch markers OK")

server = Path("/opt/satkavpn/happ-merge-server.py")
if server.exists():
    st = server.read_text()
    st = st.replace(
        '"announce": "Включите routing-профиль из подписки (YouTube без рекламы) · @satkavpnsupport"',
        '"announce": "YouTube без рекламы встроен в серверы · @satkavpnsupport"',
    )
    st = st.replace('"routing": True', '"routing": False')
    st = st.replace(
        'if meta["routing"] or HAPP_ROUTING:',
        'if meta.get("routing") and HAPP_ROUTING:',
    )
    server.write_text(st)
    print("happ-merge-server.py updated")
