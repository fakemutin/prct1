#!/usr/bin/env python3
"""Relink BS CDN hosts to Be-He VPS 87.120.196.181 and sync Remnawave."""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.request

BEHE_NODE = "72c2928d-39e7-474e-959c-9e8762b196be"
BEELINE_HOST = "9c209086-3c43-44d5-87e1-f625d7bd8adf"
YANDEX_HOST = "14216581-e04e-4094-ac4e-d2597feb793e"
PROFILE = "00000000-0000-0000-0000-000000000000"
INBOUND_TAG = "Bee-CDN-XHTTP-HE"
PANEL = "http://remnawave:3000"


def psql(sql: str) -> str:
    return subprocess.check_output(
        [
            "docker",
            "exec",
            "remnawave-db",
            "psql",
            "-U",
            "postgres",
            "-d",
            "postgres",
            "-t",
            "-A",
            "-c",
            sql,
        ],
        text=True,
    ).strip()


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
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read())


def main() -> int:
    print("[db] relink CDN hosts -> Be-He 87.120.196.181")
    psql(
        f"UPDATE hosts_to_nodes SET node_uuid = '{BEHE_NODE}' "
        f"WHERE host_uuid IN ('{BEELINE_HOST}', '{YANDEX_HOST}');"
    )
    print(psql(
        "SELECT h.remark, n.name, n.address FROM hosts h "
        "JOIN hosts_to_nodes hn ON h.uuid=hn.host_uuid "
        "JOIN nodes n ON n.uuid=hn.node_uuid WHERE h.remark LIKE '%CDN%';"
    ))

    token = subprocess.check_output(
        ["grep", "^REMNAWAVE_API_TOKEN=", "/opt/satkavpn/candelix.env"],
        text=True,
    ).split("=", 1)[1].strip()

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
    print(f"[api] Be-He node inbound {INBOUND_TAG} active")

    api(
        token,
        "PATCH",
        "/api/hosts",
        {
            "uuid": BEELINE_HOST,
            "remark": "Лучший обход! БС CDN",
            "address": "lunz3cg8gz.a.trbcdn.net",
            "port": 443,
            "path": "/session/preview",
            "sni": "bee-he.satkaconnect.xyz",
            "host": "lunz3cg8gz.a.trbcdn.net",
            "alpn": "h2",
            "fingerprint": "firefox",
            "securityLayer": "TLS",
            "overrideSniFromAddress": False,
            "keepSniBlank": False,
            "inbound": {
                "configProfileUuid": PROFILE,
                "configProfileInboundUuid": bee_uuid,
            },
            "nodes": [BEHE_NODE],
        },
    )
    print("[api] Beeline host synced")

    api(
        token,
        "PATCH",
        "/api/hosts",
        {
            "uuid": YANDEX_HOST,
            "remark": "Yandex БС CDN",
            "address": "cdn.satkaconnect.xyz",
            "port": 443,
            "path": "/session/preview",
            "sni": "cdn.satkaconnect.xyz",
            "host": "cdn.satkaconnect.xyz",
            "alpn": "h2",
            "fingerprint": "firefox",
            "securityLayer": "TLS",
            "overrideSniFromAddress": False,
            "keepSniBlank": False,
            "inbound": {
                "configProfileUuid": PROFILE,
                "configProfileInboundUuid": bee_uuid,
            },
            "nodes": [BEHE_NODE],
        },
    )
    print("[api] Yandex host synced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
