#!/usr/bin/env python3
"""One-time Telegram session auth for Satka support userbot."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from config import Settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("auth")

STATE_FILE = Path("sessions/login_state.json")


async def main() -> int:
    settings = Settings.from_env()
    settings.validate()

    Path(settings.session_path).parent.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(settings.session_path, settings.telegram_api_id, settings.telegram_api_hash)

    await client.connect()
    if await client.is_user_authorized():
        me = await client.get_me()
        logger.info("Already authorized as @%s (%s)", me.username, me.id)
        await client.disconnect()
        return 0

    code = _env("TELEGRAM_LOGIN_CODE")
    phone = settings.telegram_phone

    if not code:
        sent = await client.send_code_request(phone)
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps({"phone_code_hash": sent.phone_code_hash}))
        logger.info("CODE_SENT to %s — set TELEGRAM_LOGIN_CODE and run again", phone)
        await client.disconnect()
        return 2

    if not STATE_FILE.exists():
        logger.error("No login state. Run without TELEGRAM_LOGIN_CODE first.")
        await client.disconnect()
        return 1

    state = json.loads(STATE_FILE.read_text())
    try:
        await client.sign_in(phone, code, phone_code_hash=state["phone_code_hash"])
    except SessionPasswordNeededError:
        if not settings.telegram_2fa_password:
            logger.error("2FA password required — set TELEGRAM_2FA_PASSWORD")
            await client.disconnect()
            return 1
        await client.sign_in(password=settings.telegram_2fa_password)

    me = await client.get_me()
    logger.info("OK — logged in as @%s (%s)", me.username, me.id)
    STATE_FILE.unlink(missing_ok=True)
    await client.disconnect()
    return 0


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
