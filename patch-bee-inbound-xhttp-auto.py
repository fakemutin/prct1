#!/usr/bin/env python3
"""Inbound Bee-CDN-XHTTP-HE: uplinkDataPlacement=auto (POST Beeline + GET Yandex)."""

from __future__ import annotations

import json
import subprocess
import urllib.request

PROFILE = "00000000-0000-0000-0000-000000000000"
INBOUND_TAG = "Bee-CDN-XHTTP-HE"
PANEL = "http://remnawave:3000"
BEHE_NODE = "72c2928d-39e7-474e-959c-9e8762b196be"


def api(token: str, method: str, path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{PANEL}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def main() -> int:
    token = subprocess.check_output(
        ["grep", "^REMNAWAVE_API_TOKEN=", "/app/candelix.env"],
        text=True,
    ).split("=", 1)[1].strip()

    profile = api(token, "GET", f"/api/config-profiles/{PROFILE}")["response"]
    config = profile["config"]
    updated = False
    for ib in config.get("inbounds", []):
        if ib.get("tag") != INBOUND_TAG:
            continue
        ss = ib.setdefault("streamSettings", {})
        xh = ss.setdefault("xhttpSettings", {})
        extra = xh.get("extra")
        if not isinstance(extra, dict):
            extra = {}
            xh["extra"] = extra
        if extra.get("uplinkDataPlacement") != "auto":
            extra["uplinkDataPlacement"] = "auto"
            updated = True
        xh["mode"] = "packet-up"
        extra.setdefault("mode", "packet-up")
        extra.setdefault("uplinkHTTPMethod", "POST")
        print("inbound extra uplinkDataPlacement:", extra.get("uplinkDataPlacement"))
        print("inbound extra uplinkHTTPMethod:", extra.get("uplinkHTTPMethod"))
        break
    else:
        print("inbound not found")
        return 1

    if updated:
        api(
            token,
            "PATCH",
            "/api/config-profiles",
            {"uuid": PROFILE, "name": profile["name"], "config": config},
        )
        print("config profile patched")
    else:
        print("already auto")

    inbounds = api(token, "GET", f"/api/config-profiles/{PROFILE}/inbounds")[
        "response"
    ]["inbounds"]
    bee_uuid = next(ib["uuid"] for ib in inbounds if ib["tag"] == INBOUND_TAG)
    api(
        token,
        "PATCH",
        "/api/nodes",
        {
            "uuid": BEHE_NODE,
            "configProfile": {
                "activeConfigProfileUuid": PROFILE,
                "activeInbounds": [bee_uuid],
            },
        },
    )
    print("Be-He node config push triggered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
