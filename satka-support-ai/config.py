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
    llm_api_key: str
    llm_base_url: str
    admin_chat_id: int
    admin_username: str
    llm_model: str
    max_history_turns: int
    alert_repeat_count: int
    alert_repeat_delay_sec: float
    allowed_chat_ids: set[int] | None
    log_level: str
    ai_block_sec: int
    max_concurrent_replies: int
    ai_globally_enabled: bool
    online_keepalive_sec: int

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

        llm_key = (
            _env("LLM_API_KEY")
            or _env("ODIROUTER_API_KEY")
            or _env("DEEPSEEK_API_KEY")
        )

        return cls(
            telegram_api_id=_env_int("TELEGRAM_API_ID", 2040),
            telegram_api_hash=_env("TELEGRAM_API_HASH", "b18441a1ff607e10a989891a5462e627"),
            telegram_phone=phone,
            telegram_2fa_password=_env("TELEGRAM_2FA_PASSWORD"),
            session_path=_env("SESSION_PATH", "sessions/support"),
            alert_bot_token=alert_token,
            llm_api_key=llm_key,
            llm_base_url=_env("LLM_BASE_URL", "https://odirouter.ai/v1"),
            admin_chat_id=_env_int("ADMIN_CHAT_ID", 8505786243),
            admin_username=_env("ADMIN_USERNAME", "hustlehapp"),
            llm_model=_env("LLM_MODEL", "free-gemini-3.5-flash"),
            max_history_turns=_env_int("MAX_HISTORY_TURNS", 16),
            alert_repeat_count=_env_int("ALERT_REPEAT_COUNT", 3),
            alert_repeat_delay_sec=float(_env("ALERT_REPEAT_DELAY_SEC", "1.2")),
            allowed_chat_ids=allowed,
            log_level=_env("LOG_LEVEL", "INFO").upper(),
            ai_block_sec=_env_int("AI_BLOCK_SEC", 3600),
            max_concurrent_replies=_env_int("MAX_CONCURRENT_REPLIES", 12),
            ai_globally_enabled=_env("AI_GLOBALLY_ENABLED", "true").lower() in {"1", "true", "yes", "on"},
            online_keepalive_sec=_env_int("ONLINE_KEEPALIVE_SEC", 180),
        )

    def validate(self) -> None:
        missing = []
        if not self.telegram_phone:
            missing.append("TELEGRAM_PHONE")
        if not self.llm_api_key:
            missing.append("LLM_API_KEY")
        if not self.alert_bot_token:
            missing.append("ALERT_BOT_TOKEN")
        if missing:
            raise RuntimeError("Missing required env: " + ", ".join(missing))
