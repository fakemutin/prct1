"""Environment configuration for Satka Support AI bot."""

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
    support_bot_token: str
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
        support_token = _env("SUPPORT_AI_BOT_TOKEN")
        alert_token = _env("ALERT_BOT_TOKEN") or support_token
        deepseek_key = _env("DEEPSEEK_API_KEY") or _env("GEMINI_API_KEY")

        allowed_raw = _env("ALLOWED_CHAT_IDS")
        allowed: set[int] | None = None
        if allowed_raw:
            allowed = {int(x.strip()) for x in allowed_raw.split(",") if x.strip()}

        return cls(
            support_bot_token=support_token,
            alert_bot_token=alert_token,
            deepseek_api_key=deepseek_key,
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
        if not self.support_bot_token:
            missing.append("SUPPORT_AI_BOT_TOKEN")
        if not self.deepseek_api_key:
            missing.append("DEEPSEEK_API_KEY")
        if missing:
            raise RuntimeError("Missing required env: " + ", ".join(missing))
