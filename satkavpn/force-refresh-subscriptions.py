#!/usr/bin/env python3
"""Touch all Remnawave users so clients pick up subscription changes."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

PANEL_URL = os.environ.get("REMNAWAVE_PANEL_URL", "https://panel.satkaconnect.xyz").rstrip("/")
API_TOKEN = os.environ.get("REMNAWAVE_API_TOKEN", "").strip()
BATCH_SIZE = int(os.environ.get("BULK_BATCH_SIZE", "100"))
MARKER = os.environ.get("SUB_REFRESH_MARKER", "candelix-removed-2026-08-03")


def api_request(method: str, path: str, payload: dict | None = None) -> dict:
    url = f"{PANEL_URL}{path}"
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def fetch_all_user_uuids() -> list[str]:
    uuids: list[str] = []
    start = 0
    page_size = 500
    while True:
        payload = api_request("GET", f"/api/users?size={page_size}&start={start}")
        response = payload.get("response", payload)
        users = response.get("users", response if isinstance(response, list) else [])
        if not users:
            break
        uuids.extend(user["uuid"] for user in users if user.get("uuid"))
        if len(users) < page_size:
            break
        start += len(users)
    return uuids


def bulk_touch(uuids: list[str]) -> int:
    affected = 0
    for offset in range(0, len(uuids), BATCH_SIZE):
        chunk = uuids[offset : offset + BATCH_SIZE]
        result = api_request(
            "POST",
            "/api/users/bulk/update",
            {
                "uuids": chunk,
                "fields": {"description": MARKER},
            },
        )
        affected += int(result.get("response", {}).get("affectedRows", 0))
        print(f"touched {offset + len(chunk)}/{len(uuids)}")
    return affected


def main() -> int:
    if not API_TOKEN:
        print("REMNAWAVE_API_TOKEN is required", file=sys.stderr)
        return 1
    uuids = fetch_all_user_uuids()
    print(f"users: {len(uuids)}")
    if not uuids:
        return 0
    affected = bulk_touch(uuids)
    print(f"affectedRows: {affected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
