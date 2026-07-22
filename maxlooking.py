#!/usr/bin/env python3
"""
Telegram MaxLooking — мультиаккаунтный лайкер историй.

Парсит активные истории из ленты аккаунта (контакты + подписки) через
stories.getAllStories и ставит реакцию-сердечко.

Запуск:
  pip install -r requirements.txt
  cp accounts.example.json accounts.json   # заполнить api_id, api_hash, phone
  cp config.example.json config.json       # при необходимости поправить лимиты
  python3 maxlooking.py login              # первый вход (код из Telegram)
  python3 maxlooking.py run                # парсинг + лайки
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from telethon import TelegramClient, functions, types
from telethon.errors import (
    AuthKeyUnregisteredError,
    FloodWaitError,
    RPCError,
    SessionPasswordNeededError,
    UserDeactivatedBanError,
)
from telethon.tl.types import PeerChannel, PeerUser

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
ACCOUNTS_PATH = BASE_DIR / "accounts.json"


@dataclass
class AppConfig:
    reaction: str = "❤️"
    min_delay_sec: float = 25.0
    max_delay_sec: float = 75.0
    max_likes_per_account_per_hour: int = 20
    max_likes_per_account_per_day: int = 80
    include_channels: bool = False
    whitelist_file: str = "whitelist.txt"
    blacklist_file: str = "blacklist.txt"
    use_whitelist_only: bool = False
    mark_as_read: bool = True
    shuffle_targets: bool = True
    session_dir: str = "sessions"
    log_file: str = "maxlooking.log"

    @classmethod
    def load(cls, path: Path) -> "AppConfig":
        if not path.exists():
            raise FileNotFoundError(
                f"Нет {path.name}. Скопируйте config.example.json -> config.json"
            )
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


@dataclass
class AccountConfig:
    name: str
    api_id: int
    api_hash: str
    phone: str


@dataclass
class StoryTarget:
    account_name: str
    peer: Any
    peer_id: int
    story_id: int
    username: str | None = None
    display_name: str | None = None


@dataclass
class AccountStats:
    likes_hour: int = 0
    likes_day: int = 0
    hour_started_at: float = field(default_factory=time.time)
    day_started_at: float = field(default_factory=time.time)


def setup_logging(log_file: str) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(BASE_DIR / log_file, encoding="utf-8"),
        ],
    )


def load_accounts(path: Path) -> list[AccountConfig]:
    if not path.exists():
        raise FileNotFoundError(
            f"Нет {path.name}. Скопируйте accounts.example.json -> accounts.json"
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    accounts: list[AccountConfig] = []
    for item in raw:
        accounts.append(
            AccountConfig(
                name=item["name"],
                api_id=int(item["api_id"]),
                api_hash=item["api_hash"],
                phone=item["phone"],
            )
        )
    return accounts


def load_username_list(path: Path) -> set[str]:
    if not path.exists():
        return set()
    result: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip().lstrip("@").lower()
        if line and not line.startswith("#"):
            result.add(line)
    return result


def session_path(cfg: AppConfig, account: AccountConfig) -> Path:
    session_dir = BASE_DIR / cfg.session_dir
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir / account.name


def build_user_map(users: list[Any]) -> dict[int, Any]:
    mapping: dict[int, Any] = {}
    for user in users:
        mapping[user.id] = user
    return mapping


def build_chat_map(chats: list[Any]) -> dict[int, Any]:
    mapping: dict[int, Any] = {}
    for chat in chats:
        mapping[chat.id] = chat
    return mapping


def peer_key(peer: Any) -> int | None:
    if isinstance(peer, PeerUser):
        return peer.user_id
    if isinstance(peer, PeerChannel):
        return peer.channel_id
    return None


def is_user_peer(peer: Any) -> bool:
    return isinstance(peer, PeerUser)


def username_of(entity: Any) -> str | None:
    username = getattr(entity, "username", None)
    return username.lower() if username else None


def display_name_of(entity: Any) -> str:
    first = getattr(entity, "first_name", None) or ""
    last = getattr(entity, "last_name", None) or ""
    title = getattr(entity, "title", None)
    if title:
        return title
    return (first + " " + last).strip() or "unknown"


def story_is_active(story: Any) -> bool:
    if getattr(story, "out", False):
        return False
    expire_date = getattr(story, "expire_date", 0) or 0
    if expire_date and expire_date < int(time.time()):
        return False
    if getattr(story, "sent_reaction", None):
        return False
    return True


def reset_stats_if_needed(stats: AccountStats) -> None:
    now = time.time()
    if now - stats.hour_started_at >= 3600:
        stats.likes_hour = 0
        stats.hour_started_at = now
    if now - stats.day_started_at >= 86400:
        stats.likes_day = 0
        stats.day_started_at = now


def can_like_more(stats: AccountStats, cfg: AppConfig) -> bool:
    reset_stats_if_needed(stats)
    return (
        stats.likes_hour < cfg.max_likes_per_account_per_hour
        and stats.likes_day < cfg.max_likes_per_account_per_day
    )


def seconds_until_hour_reset(stats: AccountStats) -> float:
    return max(0.0, 3600 - (time.time() - stats.hour_started_at))


def seconds_until_day_reset(stats: AccountStats) -> float:
    return max(0.0, 86400 - (time.time() - stats.day_started_at))


def passes_lists(
    username: str | None,
    whitelist: set[str],
    blacklist: set[str],
    use_whitelist_only: bool,
) -> bool:
    if username and username in blacklist:
        return False
    if use_whitelist_only:
        return bool(username and username in whitelist)
    return True


async def human_delay(cfg: AppConfig) -> None:
    delay = random.uniform(cfg.min_delay_sec, cfg.max_delay_sec)
    logging.debug("Пауза %.1f сек", delay)
    await asyncio.sleep(delay)


async def login_account(account: AccountConfig, cfg: AppConfig) -> None:
    client = TelegramClient(
        str(session_path(cfg, account)),
        account.api_id,
        account.api_hash,
        device_model="MaxLooking",
        system_version="1.0",
        app_version="1.0",
    )
    await client.connect()
    if await client.is_user_authorized():
        me = await client.get_me()
        logging.info("[%s] Уже авторизован: %s", account.name, me.username or me.id)
        await client.disconnect()
        return

    await client.send_code_request(account.phone)
    code = input(f"[{account.name}] Введите код из Telegram для {account.phone}: ").strip()
    try:
        await client.sign_in(account.phone, code)
    except SessionPasswordNeededError:
        password = input(f"[{account.name}] Введите облачный пароль 2FA: ").strip()
        await client.sign_in(password=password)

    me = await client.get_me()
    logging.info("[%s] Вход выполнен: %s", account.name, me.username or me.id)
    await client.disconnect()


async def fetch_story_targets(
    client: TelegramClient,
    account_name: str,
    cfg: AppConfig,
    whitelist: set[str],
    blacklist: set[str],
) -> list[StoryTarget]:
    targets: list[StoryTarget] = []
    state: str | None = None

    while True:
        result = await client(
            functions.stories.GetAllStoriesRequest(
                state=state,
                next=bool(state),
            )
        )

        users = build_user_map(result.users)
        chats = build_chat_map(result.chats)

        for peer_stories in result.peer_stories:
            peer = peer_stories.peer
            key = peer_key(peer)
            if key is None:
                continue

            entity = None
            username = None
            display_name = None

            if is_user_peer(peer):
                entity = users.get(key)
                if entity is None:
                    continue
                if getattr(entity, "bot", False):
                    continue
                username = username_of(entity)
                display_name = display_name_of(entity)
            else:
                if not cfg.include_channels:
                    continue
                entity = chats.get(key)
                if entity is None:
                    continue
                username = username_of(entity)
                display_name = display_name_of(entity)

            if not passes_lists(username, whitelist, blacklist, cfg.use_whitelist_only):
                continue

            input_peer = await client.get_input_entity(entity)
            active_ids: list[int] = []

            for story in peer_stories.stories:
                if story_is_active(story):
                    active_ids.append(story.id)
                    targets.append(
                        StoryTarget(
                            account_name=account_name,
                            peer=input_peer,
                            peer_id=key,
                            story_id=story.id,
                            username=username,
                            display_name=display_name,
                        )
                    )

            if cfg.mark_as_read and active_ids:
                max_id = max(active_ids)
                try:
                    await client(
                        functions.stories.ReadStoriesRequest(
                            peer=input_peer,
                            max_id=max_id,
                        )
                    )
                except RPCError as exc:
                    logging.warning(
                        "[%s] readStories %s: %s",
                        account_name,
                        username or key,
                        exc,
                    )

        if not getattr(result, "has_more", False):
            break
        state = result.state

    return targets


async def send_heart(
    client: TelegramClient,
    target: StoryTarget,
    cfg: AppConfig,
) -> bool:
    await client(
        functions.stories.SendReactionRequest(
            peer=target.peer,
            story_id=target.story_id,
            reaction=types.ReactionEmoji(emoticon=cfg.reaction),
            add_to_recent=False,
        )
    )
    return True


async def process_account(
    account: AccountConfig,
    cfg: AppConfig,
    whitelist: set[str],
    blacklist: set[str],
    stats: AccountStats,
) -> list[StoryTarget]:
    client = TelegramClient(
        str(session_path(cfg, account)),
        account.api_id,
        account.api_hash,
        device_model="MaxLooking",
        system_version="1.0",
        app_version="1.0",
    )

    await client.connect()
    if not await client.is_user_authorized():
        logging.error("[%s] Сессия не авторизована. Запустите: python3 maxlooking.py login", account.name)
        await client.disconnect()
        return []

    me = await client.get_me()
    logging.info("[%s] Аккаунт: @%s", account.name, me.username or me.id)

    try:
        targets = await fetch_story_targets(
            client, account.name, cfg, whitelist, blacklist
        )
        logging.info("[%s] Найдено историй для лайка: %d", account.name, len(targets))

        liked: list[StoryTarget] = []

        for target in targets:
            if not can_like_more(stats, cfg):
                wait_hour = seconds_until_hour_reset(stats)
                wait_day = seconds_until_day_reset(stats)
                wait_for = min(wait_hour if stats.likes_hour >= cfg.max_likes_per_account_per_hour else wait_day, 3600)
                logging.warning(
                    "[%s] Лимит достигнут (час: %d/%d, день: %d/%d). Ждём %.0f сек",
                    account.name,
                    stats.likes_hour,
                    cfg.max_likes_per_account_per_hour,
                    stats.likes_day,
                    cfg.max_likes_per_account_per_day,
                    wait_for,
                )
                await asyncio.sleep(wait_for)
                reset_stats_if_needed(stats)

            await human_delay(cfg)

            try:
                await send_heart(client, target, cfg)
                stats.likes_hour += 1
                stats.likes_day += 1
                liked.append(target)
                logging.info(
                    "[%s] ❤️ @%s | story_id=%s | час %d/%d | день %d/%d",
                    account.name,
                    target.username or target.peer_id,
                    target.story_id,
                    stats.likes_hour,
                    cfg.max_likes_per_account_per_hour,
                    stats.likes_day,
                    cfg.max_likes_per_account_per_day,
                )
            except FloodWaitError as exc:
                extra = random.randint(5, 20)
                total = exc.seconds + extra
                logging.warning(
                    "[%s] FLOOD_WAIT %d сек (+ %d). Ждём...",
                    account.name,
                    exc.seconds,
                    extra,
                )
                await asyncio.sleep(total)
            except RPCError as exc:
                logging.warning(
                    "[%s] Ошибка лайка @%s story=%s: %s",
                    account.name,
                    target.username or target.peer_id,
                    target.story_id,
                    exc,
                )

        return liked

    except (AuthKeyUnregisteredError, UserDeactivatedBanError) as exc:
        logging.error("[%s] Аккаунт недоступен: %s", account.name, exc)
        return []
    finally:
        await client.disconnect()


async def run_maxlooking(cfg: AppConfig, accounts: list[AccountConfig]) -> None:
    whitelist = load_username_list(BASE_DIR / cfg.whitelist_file)
    blacklist = load_username_list(BASE_DIR / cfg.blacklist_file)

    all_targets: list[StoryTarget] = []
    account_stats: dict[str, AccountStats] = {a.name: AccountStats() for a in accounts}

    # 1) Собираем цели со всех аккаунтов
    for account in accounts:
        client = TelegramClient(
            str(session_path(cfg, account)),
            account.api_id,
            account.api_hash,
        )
        await client.connect()
        if not await client.is_user_authorized():
            logging.error("[%s] Не авторизован", account.name)
            await client.disconnect()
            continue
        try:
            targets = await fetch_story_targets(
                client, account.name, cfg, whitelist, blacklist
            )
            all_targets.extend(targets)
            logging.info("[%s] Спарсено историй: %d", account.name, len(targets))
        finally:
            await client.disconnect()

    if not all_targets:
        logging.info("Нет доступных историй в ленте.")
        return

    # Убираем дубли (peer_id + story_id)
    unique: dict[tuple[int, int], StoryTarget] = {}
    for t in all_targets:
        unique[(t.peer_id, t.story_id)] = t
    all_targets = list(unique.values())

    if cfg.shuffle_targets:
        random.shuffle(all_targets)

    logging.info("Уникальных историй к обработке: %d", len(all_targets))

    # 2) Ротация аккаунтов — каждый лайк следующим аккаунтом по кругу
    ready_accounts = [
        a for a in accounts if session_path(cfg, a).with_suffix(".session").exists()
    ]
    if not ready_accounts:
        logging.error("Нет сессий. Сначала: python3 maxlooking.py login")
        return

    account_clients: dict[str, TelegramClient] = {}
    for account in ready_accounts:
        client = TelegramClient(
            str(session_path(cfg, account)),
            account.api_id,
            account.api_hash,
            device_model="MaxLooking",
            system_version="1.0",
            app_version="1.0",
        )
        await client.connect()
        if await client.is_user_authorized():
            account_clients[account.name] = client
        else:
            await client.disconnect()

    if not account_clients:
        logging.error("Ни один аккаунт не авторизован.")
        return

    account_names = list(account_clients.keys())
    idx = 0
    processed = 0

    for target in all_targets:
        # Ищем аккаунт, у которого ещё есть лимит
        attempts = 0
        while attempts < len(account_names):
            account_name = account_names[idx % len(account_names)]
            idx += 1
            attempts += 1
            stats = account_stats[account_name]

            if can_like_more(stats, cfg):
                break
        else:
            wait_for = min(
                min(seconds_until_hour_reset(s) for s in account_stats.values()),
                1800,
            )
            logging.warning("Все аккаунты в лимите. Ждём %.0f сек", wait_for)
            await asyncio.sleep(wait_for)
            for s in account_stats.values():
                reset_stats_if_needed(s)
            account_name = account_names[0]

        client = account_clients[account_name]
        stats = account_stats[account_name]
        target.account_name = account_name

        await human_delay(cfg)

        try:
            input_peer = await client.get_input_entity(target.peer_id)
            await client(
                functions.stories.SendReactionRequest(
                    peer=input_peer,
                    story_id=target.story_id,
                    reaction=types.ReactionEmoji(emoticon=cfg.reaction),
                    add_to_recent=False,
                )
            )
            stats.likes_hour += 1
            stats.likes_day += 1
            processed += 1
            logging.info(
                "[%s] ❤️ @%s | story=%s | всего %d",
                account_name,
                target.username or target.peer_id,
                target.story_id,
                processed,
            )
        except FloodWaitError as exc:
            extra = random.randint(5, 20)
            logging.warning("[%s] FLOOD_WAIT %d сек", account_name, exc.seconds)
            await asyncio.sleep(exc.seconds + extra)
        except RPCError as exc:
            logging.warning(
                "[%s] Пропуск @%s: %s",
                account_name,
                target.username or target.peer_id,
                exc,
            )

    for client in account_clients.values():
        await client.disconnect()

    logging.info("Готово. Поставлено лайков: %d", processed)


async def check_spambot(accounts: list[AccountConfig], cfg: AppConfig) -> None:
    for account in accounts:
        client = TelegramClient(
            str(session_path(cfg, account)),
            account.api_id,
            account.api_hash,
        )
        await client.connect()
        if not await client.is_user_authorized():
            logging.warning("[%s] Не авторизован", account.name)
            await client.disconnect()
            continue
        async for msg in client.iter_messages("SpamBot", limit=1):
            logging.info("[%s] SpamBot: %s", account.name, msg.text.replace("\n", " | "))
        await client.disconnect()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Telegram MaxLooking")
    parser.add_argument(
        "command",
        choices=["login", "run", "check"],
        help="login — авторизация аккаунтов, run — парсинг+лайки, check — статус SpamBot",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    cfg = AppConfig.load(CONFIG_PATH)
    accounts = load_accounts(ACCOUNTS_PATH)
    setup_logging(cfg.log_file)

    if args.command == "login":
        for account in accounts:
            await login_account(account, cfg)
        logging.info("Авторизация завершена.")
        return

    if args.command == "check":
        await check_spambot(accounts, cfg)
        return

    await run_maxlooking(cfg, accounts)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nОстановлено пользователем.")
