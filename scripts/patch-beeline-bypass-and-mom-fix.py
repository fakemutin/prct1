#!/usr/bin/env python3
"""Fix Beeline CDN bypass (UDP 443 via proxy) + revert mom tariff whitelist subset."""
from pathlib import Path

path = Path("/opt/satkavpn/happ_merge.py")
text = path.read_text()

# 1) Beeline: UDP/443 must go through tunnel (QUIC/CDN bypass), not block
old_udp = '{"type": "field", "network": "udp", "port": "443", "outboundTag": "block"}'
new_udp = '{"type": "field", "network": "udp", "port": "443", "outboundTag": "proxy"}'
if old_udp in text:
    text = text.replace(old_udp, new_udp)
    print("beeline UDP 443: block -> proxy")
elif new_udp in text:
    print("beeline UDP 443 already proxy")
else:
    print("WARN: UDP 443 rule not found")

# 2) Mom tariff: only original whitelist subset + Beeline (not all #1-12)
mom_old = """    server_no = append_whitelist_subset(
        result,
        server_no,
        numbers=WHITELIST_NUMBERS,
        auto_pool=WHITELIST_AUTO_POOL,
        natives=natives,
        remark_formatter=format_mom_whitelist_remark,
    )"""
mom_new = """    server_no = append_whitelist_subset(
        result,
        server_no,
        numbers=MOM_WHITELIST_NUMBERS,
        auto_pool=MOM_WHITELIST_NUMBERS,
        natives=natives,
        remark_formatter=format_mom_whitelist_remark,
    )"""
if mom_old in text:
    text = text.replace(mom_old, mom_new)
    print("mom tariff: reverted to MOM_WHITELIST_NUMBERS")
elif mom_new in text:
    print("mom tariff already correct")
else:
  # partial v4 state
    text2 = text.replace(
        "numbers=WHITELIST_NUMBERS,\n        auto_pool=WHITELIST_AUTO_POOL,\n        natives=natives,\n        remark_formatter=format_mom_whitelist_remark,",
        "numbers=MOM_WHITELIST_NUMBERS,\n        auto_pool=MOM_WHITELIST_NUMBERS,\n        natives=natives,\n        remark_formatter=format_mom_whitelist_remark,",
        1,
    )
    if text2 != text:
        text = text2
        print("mom tariff: reverted (alt pattern)")
    else:
        print("WARN: mom merge_mom block not found")

path.write_text(text)
print("patch OK")
