#!/usr/bin/env python3
"""Max YouTube adblock on all servers except Beeline (whitelist routing + regular + mihomo)."""
from pathlib import Path

path = Path("/opt/satkavpn/happ_merge.py")
text = path.read_text()

MARKER = "YOUTUBE_ADBLOCK_MAX_V1"

if MARKER in text:
    print("youtube-adblock-max already applied")
    raise SystemExit(0)

NEW_HAPP_ROUTING = (
    'happ://routing/onadd/eyJOYW1lIjogIlNhdGthVlBOIOKAlCBZb3VUdWJlINCx0LXQtyDRgNC10LrQu9Cw0LzRiyIsICJHbG9iYWxQcm94eSI6ICJ0cnVlIiwgIlJvdXRlT3JkZXIiOiAiYmxvY2stcHJveHktZGlyZWN0IiwgIlJlbW90ZUROU1R5cGUiOiAiRG9IIiwgIlJlbW90ZUROU0RvbWFpbiI6ICJodHRwczovL2Nsb3VkZmxhcmUtZG5zLmNvbS9kbnMtcXVlcnkiLCAiRG9tZXN0aWNETlNUeXBlIjogIkRvVSIsICJHZW9zaXRldXJsIjogImh0dHBzOi8vZ2l0aHViLmNvbS9Mb3lhbHNvbGRpZXIvdjJyYXktcnVsZXMtZGF0L3JlbGVhc2VzL2xhdGVzdC9kb3dubG9hZC9nZW9zaXRlLmRhdCIsICJHZW9pcHVybCI6ICJodHRwczovL2dpdGh1Yi5jb20vTG95YWxzb2xkaWVyL3YycmF5LXJ1bGVzLWRhdC9yZWxlYXNlcy9sYXRlc3QvZG93bmxvYWQvZ2VvaXAuZGF0IiwgIlVzZUNodW5rRmlsZXMiOiAidHJ1ZSIsICJEaXJlY3RJcCI6IFsiZ2VvaXA6cHJpdmF0ZSIsICIxMC4wLjAuMC84IiwgIjE3Mi4xNi4wLjAvMTIiLCAiMTkyLjE2OC4wLjAvMTYiXSwgIkJsb2NrU2l0ZXMiOiBbImdlb3NpdGU6Y2F0ZWdvcnktYWRzLWFsbCIsICJkb21haW46Z29vZ2xlYWRzZXJ2aWNlcy5jb20iLCAiZG9tYWluOmdvb2dsZXN5bmRpY2F0aW9uLmNvbSIsICJkb21haW46ZG91YmxlY2xpY2submV0IiwgImRvbWFpbjphZHNlcnZpY2UuZ29vZ2xlLmNvbSIsICJkb21haW46cGFnZWFkMi5nb29nbGVzeW5kaWNhdGlvbi5jb20iLCAiZG9tYWluOmFkcy55b3V0dWJlLmNvbSIsICJkb21haW46cy55b3V0dWJlLmNvbSIsICJkb21haW46c3N0YXRzLnlvdXR1YmUuY29tIiwgImRvbWFpbjptYW5pZmVzdC5nb29nbGV2aWRlby5jb20iLCAiZG9tYWluOnB1YmFkcy5nLmRvdWJsZWNsaWNrLm5ldCIsICJkb21haW46c3RhdGljLmRvdWJsZWNsaWNrLm5ldCIsICJkb21haW46Z29vZ2xlYWRzLmcuZG91YmxlY2xpY2submV0IiwgImRvbWFpbjphZGUuZ29vZ2xlc3luZGljYXRpb24uY29tIiwgImRvbWFpbjoybWRuLm5ldCIsICJkb21haW46Z29vZ2xldGFnbWFuYWdlci5jb20iLCAiZG9tYWluOmdvb2dsZXRhZ3NlcnZpY2VzLmNvbSIsICJkb21haW46Z29vZ2xlLWFuYWx5dGljcy5jb20iLCAiZG9tYWluOmZscy5kb3VibGVjbGljay5uZXQiLCAiZnVsbDp5b3V0dWJlLmNvbS9wYWdlYWQvIiwgImZ1bGw6d3d3LnlvdXR1YmUuY29tL3BhZ2VhZC8iLCAiZnVsbDptLnlvdXR1YmUuY29tL3BhZ2VhZC8iLCAiZnVsbDp5b3V0dWJlLmNvbS9hcGkvc3RhdHMvYWRzIiwgImZ1bGw6d3d3LnlvdXR1YmUuY29tL2FwaS9zdGF0cy9hZHMiLCAiZnVsbDp5b3V0dWJlLmNvbS9wdHJhY2tpbmciLCAiZnVsbDp3d3cueW91dHViZS5jb20vcHRyYWNraW5nIl0sICJQcm94eVNpdGVzIjogWyJnZW9zaXRlOnlvdXR1YmUiLCAiZ2Vvc2l0ZTpnb29nbGUiXSwgIkRvbWFpblN0cmF0ZWd5IjogIklQSWZOb25NYXRjaCIsICJGYWtlRE5TIjogImZhbHNlIn0='
)

NEW_YOUTUBE_ADBLOCK = '''YOUTUBE_ADBLOCK_DOMAINS = [
    # YouTube pagead / stats / ptracking
    "full:youtube.com/pagead/",
    "full:www.youtube.com/pagead/",
    "full:m.youtube.com/pagead/",
    "full:music.youtube.com/pagead/",
    "full:youtube.com/api/stats/ads",
    "full:www.youtube.com/api/stats/ads",
    "full:m.youtube.com/api/stats/ads",
    "full:youtube.com/ptracking",
    "full:www.youtube.com/ptracking",
    "full:m.youtube.com/ptracking",
    # YouTube ad hosts
    "domain:ads.youtube.com",
    "domain:s.youtube.com",
    "domain:sstats.youtube.com",
    "domain:manifest.googlevideo.com",
    # Google ads stack
    "domain:googleadservices.com",
    "domain:googlesyndication.com",
    "domain:doubleclick.net",
    "domain:adservice.google.com",
    "domain:pagead2.googlesyndication.com",
    "domain:pubads.g.doubleclick.net",
    "domain:static.doubleclick.net",
    "domain:googleads.g.doubleclick.net",
    "domain:ad.doubleclick.net",
    "domain:ade.googlesyndication.com",
    "domain:fls.doubleclick.net",
    "domain:2mdn.net",
    "domain:googletagmanager.com",
    "domain:googletagservices.com",
    "domain:google-analytics.com",
    "domain:ads.googleapis.com",
    # Broad keyword matchers (Happ/Xray)
    "keyword:pagead",
    "keyword:googleads",
    "keyword:googlesyndication",
    "keyword:doubleclick",
    "keyword:adservice",
]'''

NEW_MIHOMO = '''MIHOMO_ADBLOCK_RULES = [
    "DOMAIN-SUFFIX,googleadservices.com,REJECT",
    "DOMAIN-SUFFIX,googlesyndication.com,REJECT",
    "DOMAIN-SUFFIX,doubleclick.net,REJECT",
    "DOMAIN-SUFFIX,ads.youtube.com,REJECT",
    "DOMAIN-SUFFIX,s.youtube.com,REJECT",
    "DOMAIN-SUFFIX,sstats.youtube.com,REJECT",
    "DOMAIN-SUFFIX,manifest.googlevideo.com,REJECT",
    "DOMAIN-SUFFIX,2mdn.net,REJECT",
    "DOMAIN-SUFFIX,googleads.g.doubleclick.net,REJECT",
    "DOMAIN-SUFFIX,googletagmanager.com,REJECT",
    "DOMAIN-SUFFIX,googletagservices.com,REJECT",
    "DOMAIN-SUFFIX,google-analytics.com,REJECT",
    "DOMAIN-KEYWORD,pagead,REJECT",
    "DOMAIN-KEYWORD,googleads,REJECT",
    "DOMAIN-KEYWORD,googlesyndication,REJECT",
    "DOMAIN-KEYWORD,doubleclick,REJECT",
    "DOMAIN-KEYWORD,adservice,REJECT",
]'''

ADBLOCK_RULE_LINE = (
    '            {"type": "field", "domain": list(REGULAR_ADBLOCK_DOMAINS), "outboundTag": "block"},\n'
)

# Replace YOUTUBE_ADBLOCK_DOMAINS block
import re

yt_match = re.search(r"YOUTUBE_ADBLOCK_DOMAINS = \[.*?\n\]", text, re.S)
if not yt_match:
    raise SystemExit("YOUTUBE_ADBLOCK_DOMAINS block not found")
text = text[:yt_match.start()] + NEW_YOUTUBE_ADBLOCK + text[yt_match.end():]

mihomo_match = re.search(r"MIHOMO_ADBLOCK_RULES = \[.*?\n\]", text, re.S)
if not mihomo_match:
    raise SystemExit("MIHOMO_ADBLOCK_RULES block not found")
text = text[:mihomo_match.start()] + NEW_MIHOMO + text[mihomo_match.end():]

# rebuild_safe_routing: use full adblock list
text = text.replace(
    '{"type": "field", "domain": list(ADBLOCK_DOMAINS), "outboundTag": "block"}',
    '{"type": "field", "domain": list(REGULAR_ADBLOCK_DOMAINS), "outboundTag": "block"}',
)

# rebuild_whitelist_routing: add block rules (not used for Beeline)
old_wl = '''def rebuild_whitelist_routing(
    cfg: dict,
    *,
    proxy_tag: str = "proxy",
    balancer_tag: str | None = None,
) -> None:
    """Белые списки: IP-check и RU-приложения → direct, остальное → proxy."""
    ensure_direct_outbound(cfg)
    cfg["routing"] = {
        "domainStrategy": "IPIfNonMatch",
        "rules": [
            {"type": "field", "ip": list(PRIVATE_CIDRS), "outboundTag": "direct"},'''

new_wl = '''def rebuild_whitelist_routing(
    cfg: dict,
    *,
    proxy_tag: str = "proxy",
    balancer_tag: str | None = None,
) -> None:
    """Белые списки: блок YouTube-рекламы + direct bypass, остальное → proxy."""
    ensure_block_outbound(cfg)
    ensure_direct_outbound(cfg)
    cfg["routing"] = {
        "domainStrategy": "IPIfNonMatch",
        "rules": [
            {"type": "field", "domain": list(REGULAR_ADBLOCK_DOMAINS), "outboundTag": "block"},
            {"type": "field", "ip": list(PRIVATE_CIDRS), "outboundTag": "direct"},'''

if old_wl in text:
    text = text.replace(old_wl, new_wl)
elif "блок YouTube-рекламы + direct bypass" not in text:
    raise SystemExit("rebuild_whitelist_routing block not found")

# apply_balancer_whitelist_routing
old_bal_wl = '''def apply_balancer_whitelist_routing(
    cfg: dict,
    selector: list[str],
    *,
    natives: dict[str, dict] | None = None,
) -> None:
    del natives
    ensure_direct_outbound(cfg)
    cfg["routing"] = {
        "domainStrategy": "IPIfNonMatch",
        "balancers": [
            {
                "tag": AUTO_BALANCER_TAG,
                "selector": selector,
                "strategy": {"type": "random"},
            }
        ],
        "rules": [
            {"type": "field", "ip": list(PRIVATE_CIDRS), "outboundTag": "direct"},'''

new_bal_wl = '''def apply_balancer_whitelist_routing(
    cfg: dict,
    selector: list[str],
    *,
    natives: dict[str, dict] | None = None,
) -> None:
    del natives
    ensure_block_outbound(cfg)
    ensure_direct_outbound(cfg)
    cfg["routing"] = {
        "domainStrategy": "IPIfNonMatch",
        "balancers": [
            {
                "tag": AUTO_BALANCER_TAG,
                "selector": selector,
                "strategy": {"type": "random"},
            }
        ],
        "rules": [
            {"type": "field", "domain": list(REGULAR_ADBLOCK_DOMAINS), "outboundTag": "block"},
            {"type": "field", "ip": list(PRIVATE_CIDRS), "outboundTag": "direct"},'''

if old_bal_wl in text:
    text = text.replace(old_bal_wl, new_bal_wl)
elif "REGULAR_ADBLOCK_DOMAINS" not in text.split("apply_balancer_whitelist_routing", 1)[1].split("def ", 2)[0]:
    raise SystemExit("apply_balancer_whitelist_routing block not found")

# Default HAPP_ROUTING in happ_merge.py
if "HAPP_ROUTING = os.environ.get" in text:
    text = re.sub(
        r'HAPP_ROUTING = os\.environ\.get\("HAPP_ROUTING", """happ://routing/onadd/[^"]+"""',
        f'HAPP_ROUTING = os.environ.get("HAPP_ROUTING", """{NEW_HAPP_ROUTING}"""',
        text,
        count=1,
    )

text = text.replace(
    "PRIVATE_CIDRS = [",
    f"# {MARKER}\nPRIVATE_CIDRS = [",
    1,
)

path.write_text(text)
print("youtube-adblock-max patch OK")
