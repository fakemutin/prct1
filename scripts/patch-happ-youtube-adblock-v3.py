#!/usr/bin/env python3
"""YouTube adblock v3: fix HAPP_ROUTING header + max block rules."""
import re
from pathlib import Path

MERGE = Path("/opt/satkavpn/happ_merge.py")
SERVER = Path("/opt/satkavpn/happ-merge-server.py")
MARKER = "YOUTUBE_ADBLOCK_V3"

text = MERGE.read_text()
if MARKER in text:
    print("v3 already applied")
    raise SystemExit(0)

# build_happ_routing_url + HAPP_ROUTING fix
if "def build_happ_routing_url" not in text:
    anchor = "\nADBLOCK_DOMAINS = ["
    helper = '''

def build_happ_routing_url() -> str:
    """Happ routing profile: geosite ads + explicit YouTube/Google ad domains."""
    block_sites = [
        "geosite:category-ads-all",
        "geosite:category-ads",
        "geosite:google-ads",
        "domain:googleadservices.com",
        "domain:googlesyndication.com",
        "domain:doubleclick.net",
        "domain:adservice.google.com",
        "domain:pagead2.googlesyndication.com",
        "domain:ads.youtube.com",
        "domain:s.youtube.com",
        "domain:sstats.youtube.com",
        "domain:manifest.googlevideo.com",
        "domain:redirector.googlevideo.com",
        "domain:redirector.c.youtube.com",
        "domain:pubads.g.doubleclick.net",
        "domain:static.doubleclick.net",
        "domain:googleads.g.doubleclick.net",
        "domain:ade.googlesyndication.com",
        "domain:2mdn.net",
        "domain:googletagmanager.com",
        "domain:googletagservices.com",
        "domain:google-analytics.com",
        "domain:gvt1.com",
        "domain:gvt2.com",
        "full:youtube.com/pagead/",
        "full:www.youtube.com/pagead/",
        "full:m.youtube.com/pagead/",
        "full:youtube.com/api/stats/ads",
        "full:www.youtube.com/api/stats/ads",
        "full:youtube.com/ptracking",
        "full:www.youtube.com/ptracking",
        "full:youtube.com/get_midroll_info",
        "full:www.youtube.com/get_midroll_info",
        "full:youtube.com/initplayback",
        "full:www.youtube.com/initplayback",
    ]
    routing = {
        "Name": "SatkaVPN — YouTube без рекламы",
        "GlobalProxy": "true",
        "RouteOrder": "block-proxy-direct",
        "RemoteDNSType": "DoH",
        "RemoteDNSDomain": "https://cloudflare-dns.com/dns-query",
        "DomesticDNSType": "DoU",
        "Geositeurl": "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat",
        "Geoipurl": "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat",
        "UseChunkFiles": "true",
        "DirectIp": ["geoip:private", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"],
        "BlockSites": block_sites,
        "ProxySites": ["geosite:youtube", "geosite:google"],
        "DomainStrategy": "IPIfNonMatch",
        "FakeDNS": "false",
    }
    payload = base64.b64encode(
        json.dumps(routing, ensure_ascii=False).encode()
    ).decode()
    return f"happ://routing/onadd/{payload}"


HAPP_ROUTING = os.environ.get("HAPP_ROUTING") or build_happ_routing_url()
# YOUTUBE_ADBLOCK_V3
'''
    if anchor not in text:
        raise SystemExit("ADBLOCK_DOMAINS anchor not found")
    text = text.replace(anchor, helper + anchor, 1)
    # remove old static HAPP_ROUTING if still above
    text = re.sub(
        r"HAPP_ROUTING = os\.environ\.get\(\"HAPP_ROUTING\", \"\"\"happ://routing/onadd/[^\"]+\"\"\"\)\n+",
        "",
        text,
        count=1,
    )

# YOUTUBE_ADBLOCK_REGEXP
if "YOUTUBE_ADBLOCK_REGEXP" not in text:
    text = text.replace(
        "REGULAR_ADBLOCK_DOMAINS = list(\n    dict.fromkeys(ADBLOCK_DOMAINS + YOUTUBE_ADBLOCK_DOMAINS)\n)",
        "YOUTUBE_ADBLOCK_REGEXP = [\n"
        '    "regexp:.*pagead.*",\n'
        '    "regexp:.*googleads.*",\n'
        '    "regexp:.*doubleclick.*",\n'
        '    "regexp:.*googlesyndication.*",\n'
        '    "regexp:.*adservice.*",\n'
        "]\n\n"
        "REGULAR_ADBLOCK_DOMAINS = list(\n"
        "    dict.fromkeys(ADBLOCK_DOMAINS + YOUTUBE_ADBLOCK_DOMAINS + YOUTUBE_ADBLOCK_REGEXP)\n"
        ")",
        1,
    )

# inject_routing_adblock_rules
if "def inject_routing_adblock_rules" not in text:
    inject = '''

def is_separator_cfg(cfg: dict) -> bool:
    return "⬇️" in (cfg.get("remarks", "") or "")


def inject_routing_adblock_rules(cfg: dict) -> None:
    if is_beeline_cfg(cfg) or is_separator_cfg(cfg):
        return
    ensure_block_outbound(cfg)
    routing = cfg.setdefault(
        "routing", {"domainStrategy": "IPIfNonMatch", "rules": []}
    )
    routing["domainStrategy"] = "IPIfNonMatch"
    rules = list(routing.get("rules") or [])
    has_block = any(
        r.get("outboundTag") == "block" and r.get("domain") for r in rules
    )
    if not has_block:
        rules.insert(
            0,
            {
                "type": "field",
                "domain": list(REGULAR_ADBLOCK_DOMAINS),
                "outboundTag": "block",
            },
        )
    routing["rules"] = rules
'''
    text = text.replace(
        "def ensure_adblock_sniffing(cfg: dict) -> None:",
        inject + "\ndef ensure_adblock_sniffing(cfg: dict) -> None:",
        1,
    )

# strengthen is_beeline_cfg
text = text.replace(
    '    remark = cfg.get("remarks", "") or ""\n    if BEELINE_WHITELIST_REMARK in remark:',
    '    remark = (cfg.get("remarks", "") or "").lower()\n'
    '    if "лучшие белые списки" in remark and "оператор" in remark:\n'
    '        return True\n'
    '    if BEELINE_WHITELIST_REMARK.lower() in remark:',
    1,
)

# finalize_adblock_layer inject routing
text = text.replace(
    "    ensure_adblock_sniffing(cfg)\n    apply_adblock_dns(cfg)",
    "    ensure_adblock_sniffing(cfg)\n    inject_routing_adblock_rules(cfg)\n    apply_adblock_dns(cfg)",
    1,
)

text = text.replace(
    'if is_beeline_cfg(cfg):\n        return\n    ensure_adblock_sniffing',
    'if is_beeline_cfg(cfg) or is_separator_cfg(cfg):\n        return\n    ensure_adblock_sniffing',
    1,
)

text = text.replace("rcode://success", "rcode://refused")

if "# YOUTUBE_ADBLOCK_V3" not in text:
    text = text.replace("# YOUTUBE_ADBLOCK_V3", "# YOUTUBE_ADBLOCK_V3", 1)
else:
    text = text.replace(
        "HAPP_ROUTING = os.environ.get(\"HAPP_ROUTING\") or build_happ_routing_url()",
        "HAPP_ROUTING = os.environ.get(\"HAPP_ROUTING\") or build_happ_routing_url()\n# YOUTUBE_ADBLOCK_V3",
        1,
    )

MERGE.write_text(text)
print("happ_merge v3 OK")

if SERVER.exists():
    st = SERVER.read_text()
    if "HAPP_ROUTING" not in st.split("from happ_merge import")[1].split(")")[0]:
        st = st.replace(
            "from happ_merge import (\n    NativeSubscriptionError,",
            "from happ_merge import (\n    HAPP_ROUTING,\n    NativeSubscriptionError,",
            1,
        )
    st = re.sub(
        r'if meta\["routing"\]:\s*routing = os\.environ\.get\("HAPP_ROUTING", ""\)\s*if routing:\s*self\.send_header\("routing", routing\)',
        'if meta["routing"] or HAPP_ROUTING:\n'
        '            routing_value = os.environ.get("HAPP_ROUTING") or HAPP_ROUTING\n'
        '            if routing_value:\n'
        '                self.send_header("routing", routing_value)',
        st,
        count=1,
    )
    st = re.sub(
        r'"free":\s*\{[^}]*"routing":\s*False',
        '"free": {\n        "title": "SatkaVPN Free",\n'
        '        "announce": "@satkavpnsupport — бесплатные VPN",\n'
        '        "routing": True',
        st,
        count=1,
    )
    SERVER.write_text(st)
    print("happ-merge-server v3 OK")
