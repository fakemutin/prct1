#!/usr/bin/env python3
"""Repair BS CDN: relink hosts to Germany node, fix Beeline CDN address, DNS bee-he."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request

BEELINE_HOST_UUID = "9c209086-3c43-44d5-87e1-f625d7bd8adf"
YANDEX_HOST_UUID = "14216581-e04e-4094-ac4e-d2597feb793e"
GERMANY_NODE_UUID = "85017be3-bb00-4331-8bd4-9a1424966ce0"
OLD_NODE_UUID = "72c2928d-39e7-474e-959c-9e8762b196be"
BEELINE_TECH = "lunz3cg8gz.a.trbcdn.net"
BEELINE_ORIGIN = "bee-he.satkaconnect.xyz"
GERMANY_IP = "81.90.25.134"
PROFILE_UUID = "00000000-0000-0000-0000-000000000000"
INBOUND_TAG = "Bee-CDN-XHTTP-HE"


def api(panel: str, token: str, method: str, path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{panel.rstrip('/')}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode())


def psql(sql: str) -> str:
    cmd = [
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
    ]
    return subprocess.check_output(cmd, text=True).strip()


def fix_db() -> None:
    print("[db] relink CDN hosts to Germany node")
    psql(
        f"UPDATE hosts_to_nodes SET node_uuid = '{GERMANY_NODE_UUID}' "
        f"WHERE host_uuid IN ('{BEELINE_HOST_UUID}', '{YANDEX_HOST_UUID}');"
    )
    print("[db] fix Beeline CDN address -> trbcdn + origin SNI")
    psql(
        f"UPDATE hosts SET address = '{BEELINE_TECH}', host = '{BEELINE_TECH}', "
        f"sni = '{BEELINE_ORIGIN}' "
        f"WHERE uuid = '{BEELINE_HOST_UUID}';"
    )
    nodes = psql(
        "SELECT h.remark, n.name, n.address FROM hosts h "
        "JOIN hosts_to_nodes hn ON h.uuid=hn.host_uuid "
        "JOIN nodes n ON n.uuid=hn.node_uuid "
        "WHERE h.remark LIKE '%CDN%';"
    )
    print(nodes)


def fix_api(panel: str, token: str) -> None:
    profile = api(panel, token, "GET", f"/api/config-profiles/{PROFILE_UUID}")["response"]
    inbound_list = api(panel, token, "GET", f"/api/config-profiles/{PROFILE_UUID}/inbounds")[
        "response"
    ]["inbounds"]
    bee_uuid = next(ib["uuid"] for ib in inbound_list if ib["tag"] == INBOUND_TAG)

    api(
        panel,
        token,
        "PATCH",
        "/api/nodes",
        {
            "uuid": GERMANY_NODE_UUID,
            "configProfile": {
                "activeConfigProfileUuid": PROFILE_UUID,
                "activeInbounds": [bee_uuid],
            },
        },
    )
    print(f"[api] Germany node inbound {INBOUND_TAG} active")

    api(
        panel,
        token,
        "PATCH",
        "/api/hosts",
        {
            "uuid": BEELINE_HOST_UUID,
            "remark": "Лучший обход! БС CDN",
            "address": BEELINE_TECH,
            "port": 443,
            "path": "/session/preview",
            "sni": BEELINE_ORIGIN,
            "host": BEELINE_TECH,
            "alpn": "h2",
            "fingerprint": "firefox",
            "securityLayer": "TLS",
            "overrideSniFromAddress": False,
            "keepSniBlank": False,
            "inbound": {
                "configProfileUuid": PROFILE_UUID,
                "configProfileInboundUuid": bee_uuid,
            },
            "nodes": [GERMANY_NODE_UUID],
        },
    )
    print("[api] Beeline host patched")

    api(
        panel,
        token,
        "PATCH",
        "/api/hosts",
        {
            "uuid": YANDEX_HOST_UUID,
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
                "configProfileUuid": PROFILE_UUID,
                "configProfileInboundUuid": bee_uuid,
            },
            "nodes": [GERMANY_NODE_UUID],
        },
    )
    print("[api] Yandex host patched -> Germany node")


def fix_cloudflare(token: str) -> None:
    zone_req = urllib.request.Request(
        "https://api.cloudflare.com/client/v4/zones?name=satkaconnect.xyz",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(zone_req, timeout=30) as resp:
        zones = json.loads(resp.read())["result"]
    if not zones:
        print("[cf] zone not found")
        return
    zone_id = zones[0]["id"]

    rec_req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?name=bee-he.satkaconnect.xyz",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(rec_req, timeout=30) as resp:
        records = json.loads(resp.read())["result"]

    payload = {
        "type": "A",
        "name": "bee-he",
        "content": GERMANY_IP,
        "proxied": False,
        "ttl": 120,
    }
    if records:
        rec_id = records[0]["id"]
        upd = urllib.request.Request(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{rec_id}",
            data=json.dumps(payload).encode(),
            method="PATCH",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(upd, timeout=30) as resp:
            body = json.loads(resp.read())
        print(f"[cf] bee-he A -> {GERMANY_IP}: {body.get('success')}")
    else:
        ins = urllib.request.Request(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
            data=json.dumps(payload).encode(),
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(ins, timeout=30) as resp:
            body = json.loads(resp.read())
        print(f"[cf] bee-he A created -> {GERMANY_IP}: {body.get('success')}")


def main() -> int:
    fix_db()
    panel = os.environ.get("REMNAWAVE_PANEL_URL", "http://remnawave:3000")
    token = os.environ.get("REMNAWAVE_API_TOKEN", "").strip()
    if token:
        try:
            fix_api(panel, token)
        except Exception as exc:
            print(f"[api] warn: {exc}")
    cf = os.environ.get("CLOUDFLARE_TOKEN", "").strip()
    if cf and not cf.endswith("..."):
        try:
            fix_cloudflare(cf)
        except Exception as exc:
            print(f"[cf] warn: {exc}")
    else:
        cf_from_docker = subprocess.check_output(
            ["docker", "exec", "remnawave", "printenv", "CLOUDFLARE_TOKEN"],
            text=True,
        ).strip()
        if cf_from_docker and not cf_from_docker.endswith("..."):
            try:
                fix_cloudflare(cf_from_docker)
            except Exception as exc:
                print(f"[cf] warn: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
