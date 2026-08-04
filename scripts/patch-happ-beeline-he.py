#!/usr/bin/env python3
"""Patch happ_merge.py for Bee-HE Beeline CDN."""
from pathlib import Path

path = Path("/opt/satkavpn/happ_merge.py")
text = path.read_text()

# BEELINE_TEMPLATE_TOKEN env
if "BEELINE_TEMPLATE_TOKEN" not in text:
    text = text.replace(
        'BEELINE_IN_SUBSCRIPTION = os.environ.get(\n    "BEELINE_IN_SUBSCRIPTION", "false"\n).lower() in ("1", "true", "yes")',
        'BEELINE_IN_SUBSCRIPTION = os.environ.get(\n    "BEELINE_IN_SUBSCRIPTION", "false"\n).lower() in ("1", "true", "yes")\nBEELINE_TEMPLATE_TOKEN = os.environ.get("BEELINE_TEMPLATE_TOKEN", "").strip()',
    )

# Update markers
old_markers = '''    markers = (
        BEELINE_NATIVE_KEY,
        BEELINE_WHITELIST_REMARK,
        "wr6wsz097v.a.trbcdn.net",
        "/files/sync/v1/72a9d4.aspx",
    )'''
new_markers = '''    markers = (
        BEELINE_NATIVE_KEY,
        BEELINE_WHITELIST_REMARK,
        "noe0mevhvk.a.trbcdn.net",
        "bee-he.satkaconnect.xyz",
        "wr6wsz097v.a.trbcdn.net",
        "/files/feed/v2/d00cf0.aspx",
        "/files/sync/v1/72a9d4.aspx",
    )'''
if old_markers in text:
    text = text.replace(old_markers, new_markers)
elif new_markers not in text:
    raise SystemExit("markers block not found")

# resolve_beeline_native helper
helper = '''

def resolve_beeline_native(natives: dict[str, dict]) -> dict | None:
    """Beeline host is on whitelist squad only; paid users need template fallback."""
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
'''

if "def resolve_beeline_native" not in text:
    text = text.replace(
        "def append_beeline_whitelist(result: list, natives: dict[str, dict]) -> None:",
        helper + "\ndef append_beeline_whitelist(result: list, natives: dict[str, dict]) -> None:",
    )

old_append = '''def append_beeline_whitelist(result: list, natives: dict[str, dict]) -> None:
    if not BEELINE_IN_SUBSCRIPTION:
        return
    native = natives.get(BEELINE_NATIVE_KEY)
    if not native:
        return
    result.append(prepare_beeline_whitelist_cfg(native))'''

new_append = '''def append_beeline_whitelist(result: list, natives: dict[str, dict]) -> None:
    if not BEELINE_IN_SUBSCRIPTION:
        return
    native = resolve_beeline_native(natives)
    if not native:
        return
    result.append(prepare_beeline_whitelist_cfg(native))'''

if old_append in text:
    text = text.replace(old_append, new_append)

path.write_text(text)
print("happ_merge.py patched OK")
