#!/usr/bin/env python3
"""Configure Beeline CDN XHTTP inbound + host for Bee-HE origin node."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

PANEL_URL = os.environ.get("REMNAWAVE_PANEL_URL", "https://panel.satkaconnect.xyz").rstrip("/")
API_TOKEN = os.environ.get("REMNAWAVE_API_TOKEN", "").strip()
PROFILE_UUID = "00000000-0000-0000-0000-000000000000"
NODE_UUID = os.environ.get("BEELINE_NODE_UUID", "61a0208e-b8b5-4efb-ac41-298df7ace92d")
WHITELIST_SQUAD_UUID = "28a5e0f5-4188-4ec8-aaf6-e8b20ec019e8"

ORIGIN_DOMAIN = os.environ.get("BEELINE_ORIGIN_DOMAIN", "bee-he.satkaconnect.xyz")
TECH_DOMAIN = os.environ.get("BEELINE_TECH_DOMAIN", "noe0mevhvk.a.trbcdn.net")
TUNNEL_PATH = os.environ.get("BEELINE_TUNNEL_PATH", "/files/feed/v2/d00cf0.aspx")
HOST_REMARK = "Лучшие белые списки! | ВСЕ ОПЕРАТОРЫ"
INBOUND_TAG = "Bee-CDN-XHTTP-HE"
HOST_UUID = os.environ.get("BEELINE_HOST_UUID", "9c209086-3c43-44d5-87e1-f625d7bd8adf")


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
                    "xmux": {"maxConcurrency": "8"},
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
                    "scMinPostsIntervalMs": "2-4",
                    "serverMaxHeaderBytes": 32768,
                },
                "noSSEHeader": True,
                "noGRPCHeader": True,
                "scMaxBufferedPosts": 100,
                "scMaxEachPostBytes": 3000000,
                "scMaxConcurrentPosts": 30,
                "scMinPostsIntervalMs": 2,
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
    updated = False
    for idx, ib in enumerate(inbounds):
        if ib.get("tag") == INBOUND_TAG:
            inbounds[idx] = bee_inbound()
            updated = True
            break
    if not updated:
        inbounds.append(bee_inbound())
    config["inbounds"] = inbounds
    api(
        "PATCH",
        "/api/config-profiles",
        {"uuid": PROFILE_UUID, "name": profile["name"], "config": config},
    )
    print(f"{'updated' if updated else 'added'} inbound {INBOUND_TAG}")

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
                "activeInbounds": [bee_uuid],
            },
        },
    )
    print("node Bee-HE inbounds updated")

    squad = api("GET", f"/api/internal-squads/{WHITELIST_SQUAD_UUID}")["response"]
    inbound_uuids = [ib["uuid"] for ib in squad.get("inbounds", [])]
    if bee_uuid not in inbound_uuids:
        inbound_uuids.append(bee_uuid)
        api(
            "PATCH",
            "/api/internal-squads",
            {"uuid": WHITELIST_SQUAD_UUID, "inbounds": inbound_uuids},
        )
        print("whitelist squad: Bee inbound added")
    else:
        print("whitelist squad: already has Bee inbound")

    host_payload = {
        "uuid": HOST_UUID,
        "remark": HOST_REMARK,
        "address": TECH_DOMAIN,
        "port": 443,
        "path": TUNNEL_PATH,
        # SNI to origin through CDN; HTTP Host must be tech CDN domain (bee-he Host → 403)
        "sni": ORIGIN_DOMAIN,
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
    api("PATCH", "/api/hosts", host_payload)
    print(f"updated host {HOST_UUID} with node {NODE_UUID}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
