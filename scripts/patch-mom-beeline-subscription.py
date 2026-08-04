#!/usr/bin/env python3
"""Ensure Beeline «Лучшие белые списки | ВСЕ ОПЕРАТОРЫ» in mom tariff subscription."""
from pathlib import Path

path = Path("/opt/satkavpn/happ_merge.py")
text = path.read_text()

# 1) find_beeline_native: current CDN domain
if "noe0mevhvk.a.trbcdn.net" not in text.split("def find_beeline_native")[1].split("def ")[0]:
    text = text.replace(
        '"Лучшие белые списки!",\n        "wr6wsz097v.a.trbcdn.net",',
        '"Лучшие белые списки!",\n        "noe0mevhvk.a.trbcdn.net",\n        "wr6wsz097v.a.trbcdn.net",',
        1,
    )
    print("find_beeline_native: +noe0mevhvk")

# 2) UUID helpers
helper = '''

def subscription_vless_uuid_from_satka(satka: list) -> str | None:
    """Subscriber VLESS UUID from native servers (not the shared beeline template)."""
    for item in satka:
        remark = item.get("remarks") or ""
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
        1,
    )
    print("uuid helpers added")

# 3) append_beeline_whitelist + ensure
old_append = """def append_beeline_whitelist(result: list, natives: dict[str, dict]) -> None:
    if not BEELINE_IN_SUBSCRIPTION:
        return
    native = resolve_beeline_native(natives)
    if not native:
        return
    result.append(prepare_beeline_whitelist_cfg(native))"""

new_append = """def append_beeline_whitelist(
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
    result.append(cfg)


def ensure_beeline_whitelist_entry(
    result: list,
    natives: dict[str, dict],
    *,
    satka: list | None = None,
) -> None:
    """Добавить Beeline CDN, если ещё не в списке (тариф «Для мамы» и др.)."""
    if any(is_beeline_cfg(cfg) for cfg in result):
        return
    append_beeline_whitelist(result, natives, satka=satka)"""

if old_append in text:
    text = text.replace(old_append, new_append)
    print("append_beeline_whitelist updated")
elif "def ensure_beeline_whitelist_entry" not in text:
  # already has satka signature variant
    if "def append_beeline_whitelist(" in text and "ensure_beeline_whitelist_entry" not in text:
        text = text.replace(
            "    result.append(cfg)\n\n\ndef prepare_native_lte_exit",
            "    result.append(cfg)\n\n\ndef ensure_beeline_whitelist_entry(\n"
            "    result: list,\n    natives: dict[str, dict],\n    *,\n    satka: list | None = None,\n"
            ") -> None:\n    if any(is_beeline_cfg(cfg) for cfg in result):\n        return\n"
            "    append_beeline_whitelist(result, natives, satka=satka)\n\n\ndef prepare_native_lte_exit",
            1,
        )
        print("ensure_beeline_whitelist_entry added")

# 4) append_whitelist_subset: satka param + beeline call
if "satka: list | None = None,\n    remark_formatter=None," not in text:
    text = text.replace(
        "    natives: dict[str, dict] | None = None,\n    remark_formatter=None,\n) -> int:\n"
        "    \"\"\"Подмножество белых списков с автовыбором.\"\"\"",
        "    natives: dict[str, dict] | None = None,\n    satka: list | None = None,\n"
        "    remark_formatter=None,\n) -> int:\n    \"\"\"Подмножество белых списков с автовыбором.\"\"\"",
        1,
    )
    print("append_whitelist_subset: +satka param")

text = text.replace(
    "    append_beeline_whitelist(result, natives)\n\n    for number in numbers:",
    "    append_beeline_whitelist(result, natives or {}, satka=satka)\n\n    for number in numbers:",
    1,
)

# 5) append_whitelist_paid satka
if "satka: list | None = None,\n) -> int:\n    \"\"\"Белые списки в платной подписке" not in text:
    text = text.replace(
        "    natives: dict[str, dict] | None = None,\n) -> int:\n    \"\"\"Белые списки в платной подписке",
        "    natives: dict[str, dict] | None = None,\n    satka: list | None = None,\n) -> int:\n"
        "    \"\"\"Белые списки в платной подписке",
        1,
    )
text = text.replace(
    "    append_beeline_whitelist(result, natives)\n\n    for number in WHITELIST_NUMBERS:",
    "    append_beeline_whitelist(result, natives or {}, satka=satka)\n\n    for number in WHITELIST_NUMBERS:",
    1,
)

# 6) merge_subscription
text = text.replace(
    "    server_no = append_whitelist_paid(result, server_no, natives=natives)",
    "    server_no = append_whitelist_paid(result, server_no, natives=natives, satka=satka)",
    1,
)

# 7) merge_mom_subscription
mom_block = """    server_no = append_whitelist_subset(
        result,
        server_no,
        numbers=MOM_WHITELIST_NUMBERS,
        auto_pool=MOM_WHITELIST_NUMBERS,
        natives=natives,
        remark_formatter=format_mom_whitelist_remark,
    )"""
mom_fixed = """    server_no = append_whitelist_subset(
        result,
        server_no,
        numbers=MOM_WHITELIST_NUMBERS,
        auto_pool=MOM_WHITELIST_NUMBERS,
        natives=natives,
        satka=satka,
        remark_formatter=format_mom_whitelist_remark,
    )
    ensure_beeline_whitelist_entry(result, natives, satka=satka)"""

if mom_block in text:
    text = text.replace(mom_block, mom_fixed)
    print("merge_mom: satka + ensure_beeline")
elif "ensure_beeline_whitelist_entry(result, natives, satka=satka)" not in text:
    text = text.replace(
        "        natives=natives,\n        satka=satka,\n        remark_formatter=format_mom_whitelist_remark,\n    )\n\n    stable,",
        "        natives=natives,\n        satka=satka,\n        remark_formatter=format_mom_whitelist_remark,\n    )\n"
        "    ensure_beeline_whitelist_entry(result, natives, satka=satka)\n\n    stable,",
        1,
    )
    print("merge_mom: ensure_beeline added")

# revert v4 mistake if present
text = text.replace(
    "numbers=WHITELIST_NUMBERS,\n        auto_pool=WHITELIST_AUTO_POOL,\n        natives=natives,\n"
    "        remark_formatter=format_mom_whitelist_remark,",
    "numbers=MOM_WHITELIST_NUMBERS,\n        auto_pool=MOM_WHITELIST_NUMBERS,\n        natives=natives,\n"
    "        satka=satka,\n        remark_formatter=format_mom_whitelist_remark,",
    1,
)

path.write_text(text)
print("patch-mom-beeline-subscription OK")
