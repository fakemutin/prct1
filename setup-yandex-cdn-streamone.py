#!/usr/bin/env python3
"""Yandex CDN: inbound stream-one on 7444 + Caddy + panel host (Beeline untouched)."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.request

PROFILE = "00000000-0000-0000-0000-000000000000"
BEHE_NODE = "72c2928d-39e7-474e-959c-9e8762b196be"
YANDEX_HOST = "14216581-e04e-4094-ac4e-d2597feb793e"
HE_TAG = "Bee-CDN-XHTTP-HE"
YD_TAG = "Bee-CDN-XHTTP-YD"
YD_PORT = 7444
PATH = "/session/preview"
PANEL = os.environ.get(
    "REMNAWAVE_PANEL_URL", "https://panel.satkaconnect.xyz"
).rstrip("/")


def psql(sql: str) -> str:
    return subprocess.check_output(
        [
            "docker", "exec", "remnawave-db", "psql", "-U", "postgres", "-d", "postgres",
            "-t", "-A", "-c", sql,
        ],
        text=True,
    ).strip()


def api(token: str, method: str, path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{PANEL}{path}", data=data, method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def yandex_inbound_from_he(he: dict) -> dict:
    yd = json.loads(json.dumps(he))
    yd["tag"] = YD_TAG
    yd["port"] = YD_PORT
    yd["listen"] = "127.0.0.1"
    ss = yd.setdefault("streamSettings", {})
    xh = ss.setdefault("xhttpSettings", {})
    xh["mode"] = "stream-one"
    xh["path"] = PATH
    extra = xh.get("extra")
    if isinstance(extra, dict):
        extra["mode"] = "stream-one"
        extra["path"] = PATH
        extra.pop("uplinkHTTPMethod", None)
        extra.pop("uplinkDataPlacement", None)
        extra.pop("uplinkDataKey", None)
    return yd


def main() -> int:
    env_path = os.environ.get("CANDELIX_ENV", "/opt/satkavpn/candelix.env")
    token = subprocess.check_output(
        ["grep", "^REMNAWAVE_API_TOKEN=", env_path],
        text=True,
    ).split("=", 1)[1].strip()

    profile = api(token, "GET", f"/api/config-profiles/{PROFILE}")["response"]
    config = profile["config"]
    he = next(ib for ib in config["inbounds"] if ib.get("tag") == HE_TAG)
    yd = yandex_inbound_from_he(he)

    replaced = False
    for i, ib in enumerate(config["inbounds"]):
        if ib.get("tag") == YD_TAG:
            config["inbounds"][i] = yd
            replaced = True
            break
    if not replaced:
        config["inbounds"].append(yd)
    api(token, "PATCH", "/api/config-profiles", {
        "uuid": PROFILE, "name": profile["name"], "config": config,
    })
    print("config profile: inbound", YD_TAG, "port", YD_PORT)

    inbounds = api(token, "GET", f"/api/config-profiles/{PROFILE}/inbounds")["response"]["inbounds"]
    he_uuid = next(ib["uuid"] for ib in inbounds if ib["tag"] == HE_TAG)
    yd_uuid = next(ib["uuid"] for ib in inbounds if ib["tag"] == YD_TAG)

    api(token, "PATCH", "/api/nodes", {
        "uuid": BEHE_NODE,
        "configProfile": {
            "activeConfigProfileUuid": PROFILE,
            "activeInbounds": [he_uuid, yd_uuid],
        },
    })
    print("node active inbounds: HE + YD")

    psql(
        f"UPDATE hosts SET address='cdn.satkaconnect.xyz', host='cdn.satkaconnect.xyz', "
        f"sni='cdn.satkaconnect.xyz' WHERE uuid='{YANDEX_HOST}';"
    )

    api(token, "PATCH", "/api/hosts", {
        "uuid": YANDEX_HOST,
        "remark": "Yandex БС CDN",
        "address": "cdn.satkaconnect.xyz",
        "port": 443,
        "path": PATH,
        "sni": "cdn.satkaconnect.xyz",
        "host": "cdn.satkaconnect.xyz",
        "alpn": "h2",
        "fingerprint": "firefox",
        "securityLayer": "TLS",
        "overrideSniFromAddress": False,
        "keepSniBlank": False,
        "inbound": {
            "configProfileUuid": PROFILE,
            "configProfileInboundUuid": yd_uuid,
        },
        "nodes": [BEHE_NODE],
    })
    print("Yandex host -> inbound", YD_TAG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
