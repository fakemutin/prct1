#!/usr/bin/env python3
"""Configure Beeline CDN XHTTP inbound + host for Netherlands#2 node."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

PANEL_URL = os.environ.get("REMNAWAVE_PANEL_URL", "https://panel.satkaconnect.xyz").rstrip("/")
API_TOKEN = os.environ.get("REMNAWAVE_API_TOKEN", "").strip()
PROFILE_UUID = "00000000-0000-0000-0000-000000000000"
NODE_UUID = "1b56f65b-3f1e-4e3f-805f-da2f7ea2b24d"
INTERNAL_INBOUND_UUID = "2f306d4e-f7b9-4017-a21c-2b7da84b82d5"
SQUAD_UUIDS = (
    "b4d1b0f0-62bb-496a-b1d1-2618a7374313",  # free
    "28a5e0f5-4188-4ec8-aaf6-e8b20ec019e8",  # whitelist
    "71926802-f39c-4db8-8583-0560b40f2156",  # free_lite
)

ORIGIN_DOMAIN = os.environ.get("BEELINE_ORIGIN_DOMAIN", "nl-bee.satkaconnect.xyz")
TECH_DOMAIN = os.environ.get("BEELINE_TECH_DOMAIN", "wr6wsz097v.a.trbcdn.net")
TUNNEL_PATH = os.environ.get("BEELINE_TUNNEL_PATH", "/files/sync/v1/72a9d4.aspx")
INBOUND_TAG = "Bee-CDN-XHTTP-NL"


def api(method: str, path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{PANEL_URL}{path}",
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


def bee_inbound() -> dict:
    return {
        "tag": INBOUND_TAG,
        "port": 7443,
        "listen": "127.0.0.1",
        "protocol": "vless",
        "settings": {"clients": [], "decryption": "none"},
        "sniffing": {
            "enabled": True,
            "routeOnly": True,
            "destOverride": ["http", "tls", "quic"],
        },
        "streamSettings": {
            "network": "xhttp",
            "security": "none",
            "xhttpSettings": {
                "mode": "packet-up",
                "path": TUNNEL_PATH,
                "extra": {
                    "mode": "packet-up",
                    "path": TUNNEL_PATH,
                    "xmux": {"maxConcurrency": "1"},
                    "seqKey": "chunk_id",
                    "headers": {
                        "Accept": "*/*",
                        "Cookie": "session_id=66693f41171e7ad909f9d129861935ac",
                        "Origin": f"https://{ORIGIN_DOMAIN}/",
                        "Referer": f"https://{ORIGIN_DOMAIN}/",
                        "User-Agent": "Mozilla/5.0(WindowsNT10.0;Win64;x64;rv:151.0)Gecko/20100101Firefox/151.0",
                        "Sec-Fetch-Dest": "empty",
                        "Sec-Fetch-Mode": "cors",
                        "Sec-Fetch-Site": "same-origin",
                        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                    },
                    "sessionKey": "auth",
                    "noSSEHeader": True,
                    "noGRPCHeader": True,
                    "seqPlacement": "query",
                    "sessionIDKey": "auth",
                    "xPaddingBytes": "50-150",
                    "sessionIDTable": "Base62",
                    "xPaddingHeader": "X-Api-Key",
                    "xPaddingMethod": "tokenish",
                    "sessionIDLength": "16-32",
                    "sessionPlacement": "query",
                    "uplinkHTTPMethod": "POST",
                    "xPaddingObfsMode": True,
                    "xPaddingPlacement": "header",
                    "downloadHTTPMethod": "GET",
                    "scMaxBufferedPosts": 100,
                    "scMaxEachPostBytes": 3000000,
                    "sessionIDPlacement": "query",
                    "uplinkDataPlacement": "body",
                    "scMinPostsIntervalMs": "5-10",
                    "serverMaxHeaderBytes": 32768,
                },
                "noSSEHeader": True,
                "noGRPCHeader": True,
                "scMaxBufferedPosts": 100,
                "scMaxEachPostBytes": 3000000,
                "scMaxConcurrentPosts": 10,
                "scMinPostsIntervalMs": 5,
                "serverMaxHeaderBytes": 32768,
            },
        },
    }


def main() -> int:
    if not API_TOKEN:
        print("REMNAWAVE_API_TOKEN required", file=sys.stderr)
        return 1

    profile = api("GET", f"/api/config-profiles/{PROFILE_UUID}")["response"]
    config = profile["config"]
    inbounds = config.get("inbounds", [])
    tags = {ib.get("tag") for ib in inbounds}
    if INBOUND_TAG not in tags:
        inbounds.append(bee_inbound())
        api(
            "PATCH",
            "/api/config-profiles",
            {"uuid": PROFILE_UUID, "name": profile["name"], "config": config},
        )
        print(f"added inbound {INBOUND_TAG}")
    else:
        print(f"inbound {INBOUND_TAG} already exists")

    inbound_list = api("GET", f"/api/config-profiles/{PROFILE_UUID}/inbounds")["response"]["inbounds"]
    bee_uuid = next(ib["uuid"] for ib in inbound_list if ib["tag"] == INBOUND_TAG)
    print(f"bee inbound uuid: {bee_uuid}")

    api(
        "PATCH",
        "/api/nodes",
        {
            "uuid": NODE_UUID,
            "configProfile": {
                "activeConfigProfileUuid": PROFILE_UUID,
                "activeInbounds": [INTERNAL_INBOUND_UUID, bee_uuid],
            },
        },
    )
    print("node Netherlands#2 inbounds updated")

    squads = api("GET", "/api/internal-squads")["response"]["internalSquads"]
    for squad in squads:
        if squad["uuid"] not in SQUAD_UUIDS:
            continue
        inbound_uuids = [ib["uuid"] for ib in squad.get("inbounds", [])]
        if bee_uuid in inbound_uuids:
            print(f"squad {squad['name']}: already has Bee inbound")
            continue
        inbound_uuids.append(bee_uuid)
        api(
            "PATCH",
            "/api/internal-squads",
            {"uuid": squad["uuid"], "inbounds": inbound_uuids},
        )
        print(f"squad {squad['name']}: Bee inbound added")

    hosts = api("GET", "/api/hosts")["response"]
    existing = next((h for h in hosts if h.get("address") == TECH_DOMAIN), None)
    host_payload = {
        "remark": "🇳🇱 Лучшие белые списки! | ВСЕ ОПЕРАТОРЫ",
        "address": TECH_DOMAIN,
        "port": 443,
        "path": TUNNEL_PATH,
        "sni": TECH_DOMAIN,
        "host": TECH_DOMAIN,
        "alpn": "h2",
        "fingerprint": "firefox",
        "securityLayer": "DEFAULT",
        "inbound": {
            "configProfileUuid": PROFILE_UUID,
            "configProfileInboundUuid": bee_uuid,
        },
        "nodes": [NODE_UUID],
    }
    if existing:
        api("PATCH", "/api/hosts", {"uuid": existing["uuid"], **host_payload})
        print(f"updated host {existing['uuid']}")
    else:
        created = api("POST", "/api/hosts", host_payload)["response"]
        print(f"created host {created['uuid']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
