#!/usr/bin/env python3
from pathlib import Path

path = Path("/opt/satkavpn/happ_merge.py")
text = path.read_text()

helper = '''

def subscription_vless_uuid_from_satka(satka: list) -> str | None:
    """Subscriber VLESS UUID from native servers (not the shared beeline template)."""
    for item in satka:
        remark = (item.get("remarks") or "")
        blob = remark + json.dumps(item, ensure_ascii=False)
        if BEELINE_WHITELIST_REMARK in remark or "trbcdn.net" in blob:
            continue
        ob = get_user_vless_outbound(item) or get_vless_outbound(item)
        if not ob:
            continue
        users = ob.get("settings", {}).get("vnext", [{}])[0].get("users", [])
        if users and users[0].get("id"):
            return users[0]["id"]
    return None


def patch_cfg_vless_uuid(cfg: dict, vless_uuid: str) -> None:
    ob = get_vless_outbound(cfg) or get_user_vless_outbound(cfg)
    if not ob or not vless_uuid:
        return
    vnext = ob.setdefault("settings", {}).setdefault("vnext", [{}])[0]
    users = vnext.setdefault("users", [{}])
    if users:
        users[0]["id"] = vless_uuid
        users[0].setdefault("encryption", "none")
'''

if "def subscription_vless_uuid_from_satka" not in text:
    text = text.replace(
        "def resolve_beeline_native(natives: dict[str, dict]) -> dict | None:",
        helper + "\ndef resolve_beeline_native(natives: dict[str, dict]) -> dict | None:",
    )

old_append = '''def append_beeline_whitelist(result: list, natives: dict[str, dict]) -> None:
    if not BEELINE_IN_SUBSCRIPTION:
        return
    native = resolve_beeline_native(natives)
    if not native:
        return
    result.append(prepare_beeline_whitelist_cfg(native))'''

new_append = '''def append_beeline_whitelist(
    result: list,
    natives: dict[str, dict],
    *,
    satka: list | None = None,
) -> None:
    if not BEELINE_IN_SUBSCRIPTION:
        return
    native = resolve_beeline_native(natives)
    if not native:
        return
    cfg = prepare_beeline_whitelist_cfg(native)
    if satka:
        uid = subscription_vless_uuid_from_satka(satka)
        if uid:
            patch_cfg_vless_uuid(cfg, uid)
    result.append(cfg)'''

if old_append not in text:
    raise SystemExit("append_beeline block missing")
text = text.replace(old_append, new_append)

# append_whitelist_paid - add satka param to function and pass through
old_paid_sig = '''def append_whitelist_paid(
    result: list,
    server_no: int,
    *,
    natives: dict[str, dict] | None = None,
) -> int:'''

new_paid_sig = '''def append_whitelist_paid(
    result: list,
    server_no: int,
    *,
    natives: dict[str, dict] | None = None,
    satka: list | None = None,
) -> int:'''

text = text.replace(old_paid_sig, new_paid_sig)
text = text.replace(
    "    append_beeline_whitelist(result, natives)\n\n    for number in WHITELIST_NUMBERS:",
    "    append_beeline_whitelist(result, natives, satka=satka)\n\n    for number in WHITELIST_NUMBERS:",
    1,
)

# merge_subscription call
text = text.replace(
    "    server_no = append_whitelist_paid(result, server_no, natives=natives)",
    "    server_no = append_whitelist_paid(result, server_no, natives=natives, satka=satka)",
    1,
)

# merge_whitelist_subscription
old_wl = '''    natives = fetch_torrent_exit_natives(token) or {}
    if token:
        try:
            satka, _ = fetch_native_json(token, None)
            natives = {**natives, **index_natives(satka)}
        except Exception as exc:
            print(f"whitelist native merge failed: {exc}")'''

new_wl = '''    natives = fetch_torrent_exit_natives(token) or {}
    beeline_satka: list | None = None
    if token:
        try:
            satka, _ = fetch_native_json(token, None)
            beeline_satka = satka
            natives = {**natives, **index_natives(satka)}
        except Exception as exc:
            print(f"whitelist native merge failed: {exc}")'''

text = text.replace(old_wl, new_wl)
text = text.replace(
    "    append_beeline_whitelist(out, natives)\n    for number in WHITELIST_NUMBERS:",
    "    append_beeline_whitelist(out, natives, satka=beeline_satka)\n    for number in WHITELIST_NUMBERS:",
    1,
)

path.write_text(text)
print("uuid patch2 OK")
