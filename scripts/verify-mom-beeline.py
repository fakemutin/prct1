#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, "/app")
os.chdir("/app")
from happ_merge import (
    merge_mom_subscription,
    BEELINE_WHITELIST_REMARK,
    TARIFF_MOM_ID,
    remnawave_api_request,
)

users_raw = remnawave_api_request("/api/users?size=200")
users = users_raw.get("response", users_raw)
if isinstance(users, dict):
    users = users.get("users", users.get("items", []))
if not isinstance(users, list):
    users = []

mom_tokens = []
for u in users:
    if not isinstance(u, dict):
        continue
    tid = u.get("tariffId") or u.get("tariff_id")
    if tid == TARIFF_MOM_ID:
        url = u.get("subscriptionUrl") or ""
        tok = url.rstrip("/").split("/")[-1]
        if tok:
            mom_tokens.append(tok)
        if len(mom_tokens) >= 5:
            break

if not mom_tokens:
    from happ_merge import BEELINE_TEMPLATE_TOKEN
    print("no mom users in API, testing with template token")
    mom_tokens = [BEELINE_TEMPLATE_TOKEN]

print("mom tokens found", len(mom_tokens))
ok = 0
for tok in mom_tokens:
    merged, _ = merge_mom_subscription(tok)
    remarks = [c.get("remarks", "") for c in merged]
    has = any(
        BEELINE_WHITELIST_REMARK in r
        or ("Лучшие белые" in r and "ОПЕРАТОР" in r)
        for r in remarks
    )
    print("token", tok[:10], "configs", len(merged), "has_beeline", has)
    if has:
        ok += 1
        for r in remarks:
            if "белые" in r.lower() and "оператор" in r.lower():
                print(" ", r)

print("beeline_ok", ok, "/", len(mom_tokens))
