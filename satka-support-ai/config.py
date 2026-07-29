"""Environment configuration for Satka Support AI userbot."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    if not raw:
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    telegram_api_id: int
    telegram_api_hash: str
    telegram_phone: str
    telegram_2fa_password: str
    session_path: str
    alert_bot_token: str
    deepseek_api_key: str
    deepseek_base_url: str
    admin_chat_id: int
    admin_username: str
    deepseek_model: str
    max_history_turns: int
    alert_repeat_count: int
    alert_repeat_delay_sec: float
    allowed_chat_ids: set[int] | None
    log_level: str

    @classmethod
    def from_env(cls) -> "Settings":
        alert_token = _env("ALERT_BOT_TOKEN")

        allowed_raw = _env("ALLOWED_CHAT_IDS")
        allowed: set[int] | None = None
        if allowed_raw:
            allowed = {int(x.strip()) for x in allowed_raw.split(",") if x.strip()}

        phone = _env("TELEGRAM_PHONE")
        if phone and not phone.startswith("+"):
            phone = "+" + phone.replace(" ", "").replace("-", "")

        return cls(
            telegram_api_id=_env_int("TELEGRAM_API_ID", 2040),
            telegram_api_hash=_env("TELEGRAM_API_HASH", "b18441a1ff607e10a989891a546e7e"),
            telegram_phone=phone,
            telegram_2fa_password=_env("TELEGRAM_2FA_PASSWORD"),
            session_path=_env("SESSION_PATH", "sessions/support"),
            alert_bot_token=alert_token,
            deepseek_api_key=_env("DEEPSEEK_API_KEY"),
            deepseek_base_url=_env("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            admin_chat_id=_env_int("ADMIN_CHAT_ID", 8505786243),
            admin_username=_env("ADMIN_USERNAME", "hustlehapp"),
            deepseek_model=_env("DEEPSEEK_MODEL", "deepseek-chat"),
            max_history_turns=_env_int("MAX_HISTORY_TURNS", 12),
            alert_repeat_count=_env_int("ALERT_REPEAT_COUNT", 3),
            alert_repeat_delay_sec=float(_env("ALERT_REPEAT_DELAY_SEC", "1.2")),
            allowed_chat_ids=allowed,
            log_level=_env("LOG_LEVEL", "INFO").upper(),
        )

    def validate(self) -> None:
        missing = []
        if not self.telegram_phone:
            missing.append("TELEGRAM_PHONE")
        if not self.deepseek_api_key:
            missing.append("DEEPSEEK_API_KEY")
        if not self.alert_bot_token:
            missing.append("ALERT_BOT_TOKEN")
        if missing:
            raise RuntimeError("Missing required env: " + ", ".join(missing))
