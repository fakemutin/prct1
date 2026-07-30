from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class ProxyConfig:
    host: str
    port: int
    username: str | None
    password: str | None

    @property
    def enabled(self) -> bool:
        return bool(self.host and self.port)

    def to_pyrogram(self) -> dict | None:
        if not self.enabled:
            return None
        proxy: dict = {
            "scheme": "socks5",
            "hostname": self.host,
            "port": self.port,
        }
        if self.username:
            proxy["username"] = self.username
        if self.password:
            proxy["password"] = self.password
        return proxy


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: list[int]
    proxy: ProxyConfig
    default_interval_minutes: float
    post_delay_seconds: float
    scheduler_tick_seconds: float
    auto_sync_on_start: bool
    auto_start_scheduler: bool
    database_path: Path
    sessions_dir: Path


def _parse_admin_ids(raw: str) -> list[int]:
    ids: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids


def _env_bool(key: str, default: bool) -> bool:
    raw = os.getenv(key, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN не задан в .env")

    admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))
    if not admin_ids:
        raise RuntimeError("ADMIN_IDS не задан в .env")

    proxy = ProxyConfig(
        host=os.getenv("PROXY_HOST", "").strip(),
        port=int(os.getenv("PROXY_PORT", "1080") or 1080),
        username=os.getenv("PROXY_USER", "").strip() or None,
        password=os.getenv("PROXY_PASS", "").strip() or None,
    )

    db_path = Path(os.getenv("DATABASE_PATH", "data/scheduler.db"))
    if not db_path.is_absolute():
        db_path = BASE_DIR / db_path

    sessions_dir = Path(os.getenv("SESSIONS_DIR", "data/sessions"))
    if not sessions_dir.is_absolute():
        sessions_dir = BASE_DIR / sessions_dir

    # Поддержка старого DEFAULT_INTERVAL_HOURS
    if os.getenv("DEFAULT_INTERVAL_MINUTES"):
        default_minutes = float(os.getenv("DEFAULT_INTERVAL_MINUTES", "15"))
    elif os.getenv("DEFAULT_INTERVAL_HOURS"):
        default_minutes = float(os.getenv("DEFAULT_INTERVAL_HOURS", "1")) * 60
    else:
        default_minutes = 15.0

    return Settings(
        bot_token=token,
        admin_ids=admin_ids,
        proxy=proxy,
        default_interval_minutes=default_minutes,
        post_delay_seconds=float(os.getenv("POST_DELAY_SECONDS", "5")),
        scheduler_tick_seconds=float(os.getenv("SCHEDULER_TICK_SECONDS", "15")),
        auto_sync_on_start=_env_bool("AUTO_SYNC_ON_START", True),
        auto_start_scheduler=_env_bool("AUTO_START_SCHEDULER", True),
        database_path=db_path,
        sessions_dir=sessions_dir,
    )
