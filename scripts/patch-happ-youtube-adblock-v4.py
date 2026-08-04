#!/usr/bin/env python3
"""v4: Happ-compat adblock domains, DNS hosts, mom full whitelist + beeline."""
from pathlib import Path

MERGE = Path("/opt/satkavpn/happ_merge.py")
SERVER = Path("/opt/satkavpn/happ-merge-server.py")
MARKER = "YOUTUBE_ADBLOCK_V4"

text = MERGE.read_text()
if MARKER in text:
    print("v4 already applied")
    raise SystemExit(0)

# HAPP_ROUTING_ADBLOCK_DOMAINS
if "HAPP_ROUTING_ADBLOCK_DOMAINS" not in text:
    text = text.replace(
        "REGULAR_ADBLOCK_DOMAINS = list(\n"
        "    dict.fromkeys(ADBLOCK_DOMAINS + YOUTUBE_ADBLOCK_DOMAINS + YOUTUBE_ADBLOCK_REGEXP)\n"
        ")",
        "REGULAR_ADBLOCK_DOMAINS = list(\n"
        "    dict.fromkeys(ADBLOCK_DOMAINS + YOUTUBE_ADBLOCK_DOMAINS + YOUTUBE_ADBLOCK_REGEXP)\n"
        ")\n\n"
        "# Happ routing: без regexp\n"
        "HAPP_ROUTING_ADBLOCK_DOMAINS = list(\n"
        "    dict.fromkeys(\n"
        "        [d for d in REGULAR_ADBLOCK_DOMAINS if not d.startswith(\"regexp:\")]\n"
        "    )\n"
        ")\n"
        f"# {MARKER}",
        1,
    )

text = text.replace(
    '"domain": list(REGULAR_ADBLOCK_DOMAINS),',
    '"domain": list(HAPP_ROUTING_ADBLOCK_DOMAINS),',
)
text = text.replace(
    '"domain": list(REGULAR_ADBLOCK_DOMAINS)',
    '"domain": list(HAPP_ROUTING_ADBLOCK_DOMAINS)',
)

# inject_routing chunk rules
old_inject = '''    if not has_block:
        rules.insert(
            0,
            {
                "type": "field",
                "domain": list(HAPP_ROUTING_ADBLOCK_DOMAINS),
                "outboundTag": "block",
            },
        )'''
new_inject = '''    if not has_block:
        domains = list(HAPP_ROUTING_ADBLOCK_DOMAINS)
        chunk = 24
        for i in range(0, len(domains), chunk):
            rules.insert(
                i // chunk,
                {
                    "type": "field",
                    "domain": domains[i : i + chunk],
                    "outboundTag": "block",
                },
            )'''
if old_inject in text:
    text = text.replace(old_inject, new_inject)

# DNS hosts 0.0.0.0
if "hosts[f\"domain:" not in text and "def apply_adblock_dns" in text:
    text = text.replace(
        "    dns.setdefault(\"queryStrategy\", \"UseIPv4\")\n\n\ndef finalize_adblock_layer",
        "    dns.setdefault(\"queryStrategy\", \"UseIPv4\")\n"
        "    hosts = dns.setdefault(\"hosts\", {})\n"
        "    for entry in HAPP_ROUTING_ADBLOCK_DOMAINS:\n"
        "        if entry.startswith(\"domain:\"):\n"
        "            hosts[f\"domain:{entry[7:]}\"] = [\"0.0.0.0\"]\n"
        "        elif entry.startswith(\"full:\"):\n"
        "            host = entry[5:].split(\"/\", 1)[0]\n"
        "            if host:\n"
        "                hosts[f\"domain:{host}\"] = [\"0.0.0.0\"]\n\n\ndef finalize_adblock_layer",
        1,
    )

# stamp_subscription_adblock
if "def stamp_subscription_adblock" not in text:
    text = text.replace(
        "def finalize_adblock_layer(cfg: dict) -> None:",
        "def stamp_subscription_adblock(configs: list) -> None:\n"
        "    for cfg in configs:\n"
        "        finalize_adblock_layer(cfg)\n\n\ndef finalize_adblock_layer(cfg: dict) -> None:",
        1,
    )

for needle, stamp in [
    ("    return result, hwid_headers\n\n\ndef merge_mom_subscription", "    stamp_subscription_adblock(result)\n    return result, hwid_headers\n\n\ndef merge_mom_subscription"),
    ("    return out\n\n\ndef merge_free_subscription", "    stamp_subscription_adblock(out)\n    return out\n\n\ndef merge_free_subscription"),
]:
    if stamp.split("\n")[0] not in text.split(needle)[0][-200:]:
        text = text.replace(needle, stamp, 1)

# mom: all whitelist numbers
text = text.replace(
    "numbers=MOM_WHITELIST_NUMBERS,\n        auto_pool=MOM_WHITELIST_NUMBERS,",
    "numbers=WHITELIST_NUMBERS,\n        auto_pool=WHITELIST_AUTO_POOL,",
)

# resolve_beeline_native
if "def resolve_beeline_native" not in text:
    helper = '''

def resolve_beeline_native(natives: dict[str, dict]) -> dict | None:
    native = natives.get(BEELINE_NATIVE_KEY)
    if native:
        return native
    beeline = find_beeline_native(list(natives.values()))
    if beeline:
        return beeline
    token = BEELINE_TEMPLATE_TOKEN
    if not token:
        return None
    try:
        satka = fetch_native_json_via_api(token)
        return find_beeline_native(satka)
    except Exception as exc:
        print(f"beeline template fetch failed: {exc}")
        return None


def finalize_beeline_cfg(cfg: dict, *, ping_seed: str | None = None) -> None:
    fn = globals().get("finalize_beeline_tunnel_cfg")
    if fn is not None:
        fn(cfg, ping_seed=ping_seed)
    else:
        finalize_beeline_whitelist_cfg(cfg, ping_seed=ping_seed)
'''
    text = text.replace(
        "def prepare_beeline_whitelist_cfg(native_cfg: dict) -> dict:",
        helper + "\ndef prepare_beeline_whitelist_cfg(native_cfg: dict) -> dict:",
        1,
    )
    text = text.replace(
        "finalize_beeline_whitelist_cfg(cfg, ping_seed=BEELINE_WHITELIST_REMARK)",
        "finalize_beeline_cfg(cfg, ping_seed=BEELINE_WHITELIST_REMARK)",
        1,
    )
    text = text.replace(
        "native = natives.get(BEELINE_NATIVE_KEY)",
        "native = resolve_beeline_native(natives)",
        1,
    )

if "BEELINE_TEMPLATE_TOKEN" not in text:
    text = text.replace(
        ').lower() in ("1", "true", "yes")\n# Telegram',
        ').lower() in ("1", "true", "yes")\nBEELINE_TEMPLATE_TOKEN = os.environ.get("BEELINE_TEMPLATE_TOKEN", "").strip()\n# Telegram',
        1,
    )

MERGE.write_text(text)
print("happ_merge v4 OK")

if SERVER.exists():
    st = SERVER.read_text()
    st = st.replace(
        "@satkavpnsupport — поддержка SatkaVPN",
        "Включите routing-профиль (YouTube без рекламы) · @satkavpnsupport",
        1,
    )
    st = st.replace(
        "тариф «Для мамы»: глушилки, Telegram и YouTube",
        "тариф «Для мамы»: белые списки + Beeline + YouTube",
        1,
    )
    SERVER.write_text(st)
    print("happ-merge-server v4 OK")
