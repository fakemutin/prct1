#!/usr/bin/env python3
"""Merged subscription: json / mihomo / clash / v2ray base64."""

from __future__ import annotations

import base64
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from happ_merge import (
    NativeSubscriptionError,
    is_clash_client,
    is_happ_client,
    merge_free_mihomo_yaml,
    merge_free_subscription,
    merge_free_vless_base64,
    merge_mihomo_yaml,
    merge_mom_subscription,
    merge_mom_vless_base64,
    merge_subscription,
    merge_subscription_vless_base64,
    merge_whitelist_subscription,
    merge_whitelist_vless_base64,
    pick_hwid_request_headers,
    resolve_client_hwid,
    resolve_effective_plan,
)

HOST = "0.0.0.0"
PORT = 3020
PING_CHECK_URL = os.environ.get(
    "PING_CHECK_URL",
    "http://127.0.0.1:9180/generate_204",
)
PING_TYPE = os.environ.get("PING_TYPE", "proxy")
TOKEN_PATH = re.compile(
    r"^/([A-Za-z0-9_-]+)(?:/(whitelist|free|mom))?(?:/(json|happ|mihomo|clash))?/?$"
)

PLAN_META = {
    None: {
        "title": "SatkaVPN",
        "announce": "@satkavpnsupport — поддержка SatkaVPN",
        "routing": True,
    },
    "whitelist": {
        "title": "SatkaVPN Whitelist",
        "announce": "@satkavpnsupport — платная подписка «Белые списки»",
        "routing": False,
    },
    "free": {
        "title": "SatkaVPN Free",
        "announce": "@satkavpnsupport — бесплатные VPN SatkaVPN",
        "routing": False,
    },
    "mom": {
        "title": "SatkaVPN — Для мамы",
        "announce": "@satkavpnsupport — тариф «Для мамы»: глушилки, Telegram и YouTube",
        "routing": True,
    },
}


def encode_happ_header_value(value: str) -> str:
    """Happ: plain ASCII or base64:… for UTF-8 (profile-title, announce)."""
    try:
        value.encode("latin-1")
        return value
    except UnicodeEncodeError:
        return "base64:" + base64.b64encode(value.encode("utf-8")).decode("ascii")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def do_HEAD(self) -> None:
        self.do_GET(send_body=False)

    def _client_hwid_headers(self) -> dict[str, str]:
        return pick_hwid_request_headers(dict(self.headers))

    def _send_subscription_headers(
        self, meta: dict, extra: dict[str, str] | None = None
    ) -> None:
        announce = "base64:" + base64.b64encode(meta["announce"].encode()).decode()
        self.send_response(200)
        self.send_header("Content-Type", self._content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{self._filename}"')
        self.send_header("Cache-Control", "no-cache")
        self.send_header("profile-title", encode_happ_header_value(meta["title"]))
        self.send_header("profile-update-interval", "12")
        self.send_header("announce", announce)
        self.send_header("support-url", "https://t.me/satkavpnsupport")
        self.send_header("profile-web-page-url", "https://t.me/satkavpn_bot")
        self.send_header("ping-type", PING_TYPE)
        self.send_header("check-url-via-proxy", PING_CHECK_URL)
        self.send_header("proxy-ping-mode", "keepalive")
        self.send_header("subscription-ping-onopen-enabled", "1")
        self.send_header("ping-result", "time")
        self.send_header("subscription-always-hwid-enable", "1")
        self.send_header("hide-settings", "1")
        if meta["routing"]:
            routing = os.environ.get("HAPP_ROUTING", "")
            if routing:
                self.send_header("routing", routing)
        if extra:
            for key, value in extra.items():
                self.send_header(key, value)
        self.end_headers()

    def do_GET(self, send_body: bool = True) -> None:
        path = self.path.split("?", 1)[0]

        m = TOKEN_PATH.match(path)
        if not m:
            self.send_error(404, "Use /{token}/json, /{token}/whitelist, /{token}/free, /{token}/mom")
            return

        token, requested_plan, suffix = m.group(1), m.group(2), m.group(3)
        plan = resolve_effective_plan(token, requested_plan)
        user_agent = self.headers.get("User-Agent", "")

        if suffix in (None, "happ") and is_happ_client(user_agent):
            fmt = "json"
        elif suffix is None and is_clash_client(user_agent):
            fmt = "clash"
        elif suffix is None:
            fmt = "base64"
        elif suffix == "happ":
            fmt = "json"
        else:
            fmt = suffix

        meta = PLAN_META.get(plan, PLAN_META[None])
        client_headers = resolve_client_hwid(
            token, self._client_hwid_headers(), user_agent
        )
        hwid_headers: dict[str, str] = {}

        if (
            plan is None
            and fmt in ("json", "mihomo", "clash")
            and is_happ_client(user_agent)
            and "x-hwid" not in self._client_hwid_headers()
        ):
            self.send_response(404)
            self.send_header("x-hwid-not-supported", "true")
            self.send_header("subscription-always-hwid-enable", "1")
            self.end_headers()
            if send_body:
                self.wfile.write(b"")
            return

        try:
            if fmt in ("mihomo", "clash"):
                if plan == "whitelist":
                    self.send_error(404, "mihomo/clash only for main or free subscription")
                    return
                if plan == "free":
                    body = merge_free_mihomo_yaml(token, client_headers).encode()
                else:
                    body = merge_mihomo_yaml(token, client_headers).encode()
                self._content_type = "text/yaml; charset=utf-8"
                self._filename = f"{fmt}.yaml"
            elif plan == "whitelist":
                if fmt == "base64":
                    body = merge_whitelist_vless_base64(token)
                    self._content_type = "text/plain; charset=utf-8"
                    self._filename = "whitelist.txt"
                else:
                    body = json.dumps(
                        merge_whitelist_subscription(token), ensure_ascii=False
                    ).encode()
                    self._content_type = "application/json; charset=utf-8"
                    self._filename = "whitelist.json"
            elif plan == "mom":
                if fmt == "base64":
                    body = merge_mom_vless_base64(token, client_headers)
                    self._content_type = "text/plain; charset=utf-8"
                    self._filename = "mom.txt"
                else:
                    merged, hwid_headers = merge_mom_subscription(token, client_headers)
                    body = json.dumps(merged, ensure_ascii=False).encode()
                    self._content_type = "application/json; charset=utf-8"
                    self._filename = "mom.json"
            elif plan == "free":
                if fmt == "base64":
                    body = merge_free_vless_base64(token, client_headers)
                    self._content_type = "text/plain; charset=utf-8"
                    self._filename = "free.txt"
                else:
                    body = json.dumps(
                        merge_free_subscription(token, client_headers),
                        ensure_ascii=False,
                    ).encode()
                    self._content_type = "application/json; charset=utf-8"
                    self._filename = "free.json"
            elif fmt == "base64":
                body, hwid_headers = merge_subscription_vless_base64(
                    token, client_headers
                )
                self._content_type = "text/plain; charset=utf-8"
                self._filename = "subscription.txt"
            else:
                merged, hwid_headers = merge_subscription(token, client_headers)
                body = json.dumps(merged, ensure_ascii=False).encode()
                self._content_type = "application/json; charset=utf-8"
                self._filename = "subscription.json"
        except NativeSubscriptionError as exc:
            self.send_response(exc.status)
            for key, value in exc.headers.items():
                self.send_header(key, value)
            self.send_header("subscription-always-hwid-enable", "1")
            self.end_headers()
            if send_body:
                self.wfile.write(b"")
            return
        except Exception as exc:
            self.send_error(502, "subscription merge failed")
            print(f"merge error: {exc}")
            return

        self._send_subscription_headers(meta, hwid_headers)
        if send_body:
            self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"subscription-merge listening on {HOST}:{PORT}")
    server.serve_forever()
