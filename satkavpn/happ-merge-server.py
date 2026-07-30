#!/usr/bin/env python3
"""HTTP proxy: merged SATKAVPN subscription for Happ / Mihomo / V2Ray clients.

Клиентский HWID передаётся только в Remnawave (лимит устройств).
Candelix, sinful и другие апстримы получают запросы без идентификаторов устройств
(см. upstream_request_headers в happ_merge.py).
"""

from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import happ_merge as hm

PORT = int(os.environ.get("PORT", "8080"))
LISTEN = os.environ.get("LISTEN", "0.0.0.0")

PATH_RE = re.compile(
    r"^/(?P<token>[A-Za-z0-9_-]+)"
    r"(?:/(?P<plan>free|whitelist|mom))?"
    r"(?:/(?P<fmt>json|mihomo|vless))?/?$"
)


def client_hwid_headers(handler: BaseHTTPRequestHandler) -> dict[str, str]:
    """Заголовки устройства от VPN-клиента — только для Remnawave."""
    return {
        key: value
        for key, value in handler.headers.items()
        if key.lower() in hm.HWID_FORWARD_REQUEST_HEADERS and value
    }


def remnawave_hwid_headers(
    token: str, plan: str | None, client_headers: dict[str, str]
) -> dict[str, str]:
    """Ответные HWID-заголовки только от нашей панели Remnawave."""
    sub_token = token
    if plan == "free":
        sub_token = hm.free_subscription_token(token) or token
    try:
        _, hwid = hm.fetch_native_json(sub_token, client_headers or None)
        return hwid
    except Exception:
        return {}


def send_hwid_response_headers(
    handler: BaseHTTPRequestHandler, hwid_headers: dict[str, str]
) -> None:
    for key, value in (hwid_headers or {}).items():
        if value:
            handler.send_header(key, value)
    handler.send_header("subscription-always-hwid-enable", "1")


class SubscriptionHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.client_address[0]} - {fmt % args}")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        match = PATH_RE.match(parsed.path)
        if not match:
            self.send_error(404, "Not found")
            return

        token = match.group("token")
        explicit_plan = match.group("plan")
        fmt = match.group("fmt") or "json"
        client_headers = client_hwid_headers(self)
        plan = hm.resolve_effective_plan(token, explicit_plan)

        try:
            if fmt == "mihomo":
                body, content_type = self._render_mihomo(token, plan, client_headers)
                hwid_headers: dict[str, str] = {}
            elif fmt == "vless":
                body, hwid_headers = self._render_vless(token, plan, client_headers)
                content_type = "text/plain; charset=utf-8"
            else:
                body, hwid_headers = self._render_json(token, plan, client_headers)
                content_type = "application/json; charset=utf-8"

            if not hwid_headers and plan in (None, "free", "mom"):
                hwid_headers = remnawave_hwid_headers(token, plan, client_headers)

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            send_hwid_response_headers(self, hwid_headers)
            self.end_headers()
            self.wfile.write(body)
        except hm.NativeSubscriptionError as exc:
            self.send_response(exc.status)
            send_hwid_response_headers(self, exc.headers or {})
            self.end_headers()
        except Exception as exc:
            print(f"subscription error for {token} ({plan}/{fmt}): {exc}")
            self.send_error(500, "Subscription merge failed")

    def _render_json(
        self, token: str, plan: str | None, client_headers: dict[str, str]
    ) -> tuple[bytes, dict[str, str]]:
        if plan == "free":
            data = hm.merge_free_subscription(token, client_headers)
            return json.dumps(data, ensure_ascii=False).encode(), {}
        if plan == "whitelist":
            data = hm.merge_whitelist_subscription(token)
            return json.dumps(data, ensure_ascii=False).encode(), {}
        if plan == "mom":
            data, hwid = hm.merge_mom_subscription(token, client_headers)
            return json.dumps(data, ensure_ascii=False).encode(), hwid
        data, hwid = hm.merge_subscription(token, client_headers)
        return json.dumps(data, ensure_ascii=False).encode(), hwid

    def _render_vless(
        self, token: str, plan: str | None, client_headers: dict[str, str]
    ) -> tuple[bytes, dict[str, str]]:
        if plan == "free":
            payload = hm.merge_free_vless_base64(token, client_headers)
            return payload, {}
        if plan == "whitelist":
            return hm.merge_whitelist_vless_base64(token), {}
        if plan == "mom":
            merged, hwid = hm.merge_mom_subscription(token, client_headers)
            payload = hm.configs_to_vless_base64(merged, hwid)
            return payload, hwid
        return hm.merge_subscription_vless_base64(token, client_headers)

    def _render_mihomo(
        self, token: str, plan: str | None, client_headers: dict[str, str]
    ) -> tuple[bytes, str]:
        if plan == "free":
            text = hm.merge_free_mihomo_yaml(token, client_headers)
        else:
            text = hm.merge_mihomo_yaml(token, client_headers)
        return text.encode(), "text/yaml; charset=utf-8"


def main() -> None:
    server = ThreadingHTTPServer((LISTEN, PORT), SubscriptionHandler)
    print(
        f"happ-merge listening on {LISTEN}:{PORT} "
        f"(upstream HWID={'on' if hm.UPSTREAM_SEND_HWID else 'off'})"
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
