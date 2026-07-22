#!/usr/bin/env python3
"""
Telegram MaxLooking — мультиаккаунтный лайкер историй.

Источники историй:
  1) Открытые каналы — вход + парс участников + их истории
  2) Публичный поиск — stories.searchPosts по RU-хештегам
  3) Люди рядом — contacts.getLocated
  4) Лента (опц.) — stories.getAllStories

Запуск:
  pip install -r requirements.txt
  cp accounts.example.json accounts.json
  cp config.example.json config.json
  python3 maxlooking.py login
  python3 maxlooking.py discover   # только поиск, без лайков
  python3 maxlooking.py run
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
    UserAlreadyParticipantError,
    UserDeactivatedBanError,
)
from telethon.tl.types import InputGeoPoint, PeerChannel, PeerUser

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
ACCOUNTS_PATH = BASE_DIR / "accounts.json"

DEFAULT_RU_HASHTAGS = [
    "москва", "спб", "питер", "россия", "мск", "рф",
    "екатеринбург", "казань", "новосибирск", "краснодар", "сочи",
    "самара", "ростов", "уфа", "воронеж", "пермь", "волгоград",
    "красноярск", "тюмень", "омск", "челябинск", "нижнийновгород",
    "хабаровск", "владивосток", "калининград", "тула", "ярославль",
    "барнаул", "иркутск", "москвич", "питерский", "русская",
]

DEFAULT_NEARBY_CITIES = [
    {"name": "Москва", "lat": 55.7558, "lon": 37.6173},
    {"name": "Санкт-Петербург", "lat": 59.9343, "lon": 30.3351},
    {"name": "Казань", "lat": 55.8304, "lon": 49.0661},
    {"name": "Екатеринбург", "lat": 56.8389, "lon": 60.6057},
    {"name": "Новосибирск", "lat": 55.0084, "lon": 82.9357},
    {"name": "Краснодар", "lat": 45.0355, "lon": 38.9753},
]


@dataclass
class ChannelDiscoveryConfig:
    enabled: bool = True
    channels_file: str = "channels.txt"
    auto_join: bool = True
    use_joined_public_channels: bool = True
    max_participants_per_channel: int = 300
    max_channels_per_run: int = 15
    delay_between_users_sec: float = 2.0
    delay_between_channels_sec: float = 5.0


@dataclass
class DiscoveryConfig:
    enabled: bool = True
    use_feed: bool = False
    skip_contacts: bool = True
    users_only: bool = True
    russian_filter: bool = True
    use_hashtags: bool = False
    hashtags: list[str] = field(default_factory=lambda: list(DEFAULT_RU_HASHTAGS))
    search_limit_per_page: int = 50
    max_pages_per_hashtag: int = 5
    delay_between_searches_sec: float = 3.0
    people_nearby: bool = False
    nearby_self_expires_sec: int = 3600
    nearby_locations: list[dict[str, Any]] = field(
        default_factory=lambda: list(DEFAULT_NEARBY_CITIES)
    )
    channels: ChannelDiscoveryConfig = field(default_factory=ChannelDiscoveryConfig)


@dataclass
class AppConfig:
    reaction: str = "❤️"
    min_delay_sec: float = 150.0
    max_delay_sec: float = 250.0
    max_likes_per_account_per_hour: int = 18
    max_likes_per_account_per_day: int = 200
    include_channels: bool = False
    whitelist_file: str = "whitelist.txt"
    blacklist_file: str = "blacklist.txt"
    use_whitelist_only: bool = False
    mark_as_read: bool = True
    shuffle_targets: bool = True
    session_dir: str = "sessions"
    log_file: str = "maxlooking.log"
    discovery: DiscoveryConfig = field(default_factory=DiscoveryConfig)

    @classmethod
    def load(cls, path: Path) -> "AppConfig":
        if not path.exists():
            raise FileNotFoundError(
                f"Нет {path.name}. Скопируйте config.example.json -> config.json"
            )
        data = json.loads(path.read_text(encoding="utf-8"))
        discovery_raw = data.pop("discovery", {})
        channels_raw = discovery_raw.pop("channels", {})
        channels = ChannelDiscoveryConfig(
            **{
                k: channels_raw[k]
                for k in ChannelDiscoveryConfig.__dataclass_fields__
                if k in channels_raw
            }
        )
        discovery = DiscoveryConfig(
            channels=channels,
            **{
                k: discovery_raw[k]
                for k in DiscoveryConfig.__dataclass_fields__
                if k in discovery_raw and k != "channels"
            },
        )
        base = {k: data[k] for k in cls.__dataclass_fields__ if k in data and k != "discovery"}
        return cls(discovery=discovery, **base)


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
    source: str = "feed"


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


def load_channels_list(path: Path) -> list[str]:
    if not path.exists():
        return []
    result: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip().lstrip("@")
        if line and not line.startswith("#"):
            result.append(line)
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


async def load_contact_ids(client: TelegramClient) -> set[int]:
    try:
        result = await client(functions.contacts.GetContactsRequest(hash=0))
        return {user.id for user in result.users}
    except RPCError as exc:
        logging.warning("Не удалось загрузить контакты: %s", exc)
        return set()


def is_stranger(user_id: int, contact_ids: set[int], cfg: AppConfig) -> bool:
    if not cfg.discovery.skip_contacts:
        return True
    return user_id not in contact_ids


def looks_russian_user(user: Any, cfg: AppConfig) -> bool:
    """Прокси-фильтр RU: lang_code и телефон +7. Возраст через API недоступен."""
    if not cfg.discovery.russian_filter:
        return True

    lang = (getattr(user, "lang_code", None) or "").lower()
    if lang in ("ru", "uk", "be", "kk"):
        return True

    phone = (getattr(user, "phone", None) or "").strip()
    if phone.startswith("7") or phone.startswith("+7"):
        return True

    # Кириллица в имени — слабый, но полезный сигнал для RU-аудитории
    name = display_name_of(user)
    if any("\u0400" <= ch <= "\u04ff" for ch in name):
        return True

    return False


def entity_from_peer(peer: Any, users: dict[int, Any], chats: dict[int, Any]) -> Any | None:
    key = peer_key(peer)
    if key is None:
        return None
    if is_user_peer(peer):
        return users.get(key)
    return chats.get(key)


def make_target(
    account_name: str,
    entity: Any,
    input_peer: Any,
    story_id: int,
    source: str,
) -> StoryTarget:
    key = entity.id
    return StoryTarget(
        account_name=account_name,
        peer=input_peer,
        peer_id=key,
        story_id=story_id,
        username=username_of(entity),
        display_name=display_name_of(entity),
        source=source,
    )


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


async def ensure_channel_joined(client: TelegramClient, channel: Any) -> bool:
    try:
        await client(functions.channels.JoinChannelRequest(channel))
        return True
    except UserAlreadyParticipantError:
        return True
    except RPCError as exc:
        logging.warning("Не удалось вступить в %s: %s", getattr(channel, "username", channel.id), exc)
        return False


async def resolve_channels_for_scan(
    client: TelegramClient,
    cfg: AppConfig,
) -> list[Any]:
    ch_cfg = cfg.discovery.channels
    found: dict[int, Any] = {}

    if ch_cfg.use_joined_public_channels:
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            if not dialog.is_channel:
                continue
            if getattr(entity, "username", None):
                found[entity.id] = entity

    for username in load_channels_list(BASE_DIR / ch_cfg.channels_file):
        try:
            entity = await client.get_entity(username)
            if getattr(entity, "username", None) or dialog_is_megagroup_or_channel(entity):
                found[entity.id] = entity
        except (RPCError, ValueError) as exc:
            logging.warning("Канал @%s не найден: %s", username, exc)

    channels = list(found.values())
    random.shuffle(channels)
    return channels[: ch_cfg.max_channels_per_run]


def dialog_is_megagroup_or_channel(entity: Any) -> bool:
    return getattr(entity, "megagroup", False) or getattr(entity, "broadcast", False)


async def fetch_user_stories_from_channel(
    client: TelegramClient,
    account_name: str,
    user: Any,
    channel_name: str,
    cfg: AppConfig,
    whitelist: set[str],
    blacklist: set[str],
    contact_ids: set[int],
) -> list[StoryTarget]:
    disc = cfg.discovery

    if getattr(user, "bot", False) or getattr(user, "deleted", False):
        return []

    if disc.skip_contacts and not is_stranger(user.id, contact_ids, cfg):
        return []

    if not looks_russian_user(user, cfg):
        return []

    username = username_of(user)
    if not passes_lists(username, whitelist, blacklist, cfg.use_whitelist_only):
        return []

    try:
        peer_stories = await client(functions.stories.GetPeerStoriesRequest(peer=user))
    except FloodWaitError as exc:
        logging.warning("[%s] FLOOD_WAIT getPeerStories: %d сек", account_name, exc.seconds)
        await asyncio.sleep(exc.seconds + 5)
        return []
    except RPCError:
        return []

    stories = getattr(peer_stories.stories, "stories", []) or []
    if not stories:
        return []

    input_peer = await client.get_input_entity(user)
    targets: list[StoryTarget] = []
    for story in stories:
        if not story_is_active(story):
            continue
        targets.append(
            make_target(
                account_name,
                user,
                input_peer,
                story.id,
                f"channel:{channel_name}",
            )
        )
    return targets


async def fetch_discovery_from_channels(
    client: TelegramClient,
    account_name: str,
    cfg: AppConfig,
    whitelist: set[str],
    blacklist: set[str],
    contact_ids: set[int],
) -> list[StoryTarget]:
    """Вход в открытые каналы → парс участников → истории."""
    ch_cfg = cfg.discovery.channels
    if not ch_cfg.enabled:
        return []

    channels = await resolve_channels_for_scan(client, cfg)
    if not channels:
        logging.warning(
            "[%s] Нет каналов. Добавьте username в %s",
            account_name,
            ch_cfg.channels_file,
        )
        return []

    logging.info("[%s] Каналов к сканированию: %d", account_name, len(channels))
    targets: list[StoryTarget] = []
    seen_users: set[int] = set()

    for channel in channels:
        channel_name = getattr(channel, "username", None) or str(channel.id)

        if ch_cfg.auto_join:
            joined = await ensure_channel_joined(client, channel)
            if not joined:
                continue

        logging.info("[%s] Сканируем @%s ...", account_name, channel_name)
        participants_checked = 0
        users_with_stories = 0

        try:
            async for user in client.iter_participants(
                channel,
                limit=ch_cfg.max_participants_per_channel,
            ):
                if user.id in seen_users:
                    continue
                seen_users.add(user.id)
                participants_checked += 1

                user_targets = await fetch_user_stories_from_channel(
                    client,
                    account_name,
                    user,
                    channel_name,
                    cfg,
                    whitelist,
                    blacklist,
                    contact_ids,
                )
                if user_targets:
                    users_with_stories += 1
                    targets.extend(user_targets)

                if participants_checked % 25 == 0:
                    logging.info(
                        "[%s] @%s: проверено %d, с историями %d, лайков в очереди %d",
                        account_name,
                        channel_name,
                        participants_checked,
                        users_with_stories,
                        len(targets),
                    )

                await asyncio.sleep(ch_cfg.delay_between_users_sec)

        except FloodWaitError as exc:
            logging.warning(
                "[%s] FLOOD_WAIT участники @%s: %d сек",
                account_name,
                channel_name,
                exc.seconds,
            )
            await asyncio.sleep(exc.seconds + 10)
        except RPCError as exc:
            logging.warning("[%s] Ошибка @%s: %s", account_name, channel_name, exc)

        logging.info(
            "[%s] @%s готов: участников %d, юзеров с историями %d, историй %d",
            account_name,
            channel_name,
            participants_checked,
            users_with_stories,
            len(targets),
        )
        await asyncio.sleep(ch_cfg.delay_between_channels_sec)

    return targets


async def fetch_discovery_by_hashtags(
    client: TelegramClient,
    account_name: str,
    cfg: AppConfig,
    whitelist: set[str],
    blacklist: set[str],
    contact_ids: set[int],
) -> list[StoryTarget]:
    """Глобальный поиск публичных историй незнакомцев по RU-хештегам."""
    disc = cfg.discovery
    if not disc.use_hashtags:
        return []

    targets: list[StoryTarget] = []
    hashtags = list(disc.hashtags)
    random.shuffle(hashtags)

    for hashtag in hashtags:
        offset = ""
        pages = 0

        while pages < disc.max_pages_per_hashtag:
            try:
                result = await client(
                    functions.stories.SearchPostsRequest(
                        hashtag=hashtag,
                        offset=offset,
                        limit=disc.search_limit_per_page,
                    )
                )
            except FloodWaitError as exc:
                logging.warning(
                    "[%s] FLOOD_WAIT при поиске #%s: %d сек",
                    account_name,
                    hashtag,
                    exc.seconds,
                )
                await asyncio.sleep(exc.seconds + random.randint(3, 15))
                continue
            except RPCError as exc:
                logging.warning("[%s] Поиск #%s: %s", account_name, hashtag, exc)
                break

            users = build_user_map(result.users)
            chats = build_chat_map(result.chats)
            found_on_page = 0

            for found in result.stories:
                peer = found.peer
                story = found.story
                key = peer_key(peer)
                if key is None or not story_is_active(story):
                    continue

                if disc.users_only and not is_user_peer(peer):
                    continue

                entity = entity_from_peer(peer, users, chats)
                if entity is None:
                    continue

                if getattr(entity, "bot", False):
                    continue

                if disc.skip_contacts and not is_stranger(key, contact_ids, cfg):
                    continue

                if not looks_russian_user(entity, cfg):
                    continue

                username = username_of(entity)
                if not passes_lists(username, whitelist, blacklist, cfg.use_whitelist_only):
                    continue

                try:
                    input_peer = await client.get_input_entity(entity)
                except (RPCError, ValueError) as exc:
                    logging.debug("Пропуск peer %s: %s", key, exc)
                    continue

                targets.append(
                    make_target(
                        account_name,
                        entity,
                        input_peer,
                        story.id,
                        f"hashtag:{hashtag}",
                    )
                )
                found_on_page += 1

            logging.info(
                "[%s] #%s стр.%d: +%d историй (всего %d)",
                account_name,
                hashtag,
                pages + 1,
                found_on_page,
                len(targets),
            )

            if not getattr(result, "next_offset", None):
                break
            offset = result.next_offset
            pages += 1
            await asyncio.sleep(disc.delay_between_searches_sec)

    return targets


async def fetch_discovery_nearby(
    client: TelegramClient,
    account_name: str,
    cfg: AppConfig,
    whitelist: set[str],
    blacklist: set[str],
    contact_ids: set[int],
) -> list[StoryTarget]:
    """Люди рядом (только те, кто сам включил геолокацию в Telegram)."""
    disc = cfg.discovery
    if not disc.people_nearby:
        return []

    targets: list[StoryTarget] = []
    seen_users: set[int] = set()
    locations = list(disc.nearby_locations)
    random.shuffle(locations)

    for loc in locations:
        lat = float(loc["lat"])
        lon = float(loc["lon"])
        city = loc.get("name", f"{lat},{lon}")

        try:
            updates = await client(
                functions.contacts.GetLocatedRequest(
                    geo_point=InputGeoPoint(
                        lat=lat,
                        long=lon,
                        accuracy_radius=500,
                    ),
                    self_expires=disc.nearby_self_expires_sec,
                )
            )
        except FloodWaitError as exc:
            logging.warning(
                "[%s] FLOOD_WAIT nearby %s: %d сек",
                account_name,
                city,
                exc.seconds,
            )
            await asyncio.sleep(exc.seconds + 10)
            continue
        except RPCError as exc:
            logging.warning("[%s] Nearby %s: %s", account_name, city, exc)
            continue

        nearby_users: list[Any] = []
        for user in getattr(updates, "users", []) or []:
            if user.id not in seen_users:
                seen_users.add(user.id)
                nearby_users.append(user)

        logging.info(
            "[%s] Люди рядом (%s): найдено %d",
            account_name,
            city,
            len(nearby_users),
        )

        for user in nearby_users:
            if getattr(user, "bot", False):
                continue
            if disc.skip_contacts and not is_stranger(user.id, contact_ids, cfg):
                continue
            if not looks_russian_user(user, cfg):
                continue

            username = username_of(user)
            if not passes_lists(username, whitelist, blacklist, cfg.use_whitelist_only):
                continue

            try:
                peer_stories = await client(
                    functions.stories.GetPeerStoriesRequest(peer=user)
                )
            except RPCError:
                continue

            input_peer = await client.get_input_entity(user)
            for story in peer_stories.stories.stories:
                if not story_is_active(story):
                    continue
                targets.append(
                    make_target(
                        account_name,
                        user,
                        input_peer,
                        story.id,
                        f"nearby:{city}",
                    )
                )

        await asyncio.sleep(disc.delay_between_searches_sec)

    return targets


async def collect_all_targets(
    client: TelegramClient,
    account_name: str,
    cfg: AppConfig,
    whitelist: set[str],
    blacklist: set[str],
) -> list[StoryTarget]:
    contact_ids = await load_contact_ids(client)
    targets: list[StoryTarget] = []

    if cfg.discovery.enabled:
        channel_targets = await fetch_discovery_from_channels(
            client, account_name, cfg, whitelist, blacklist, contact_ids
        )
        targets.extend(channel_targets)
        logging.info("[%s] Каналы: %d историй", account_name, len(channel_targets))

        hashtag_targets = await fetch_discovery_by_hashtags(
            client, account_name, cfg, whitelist, blacklist, contact_ids
        )
        targets.extend(hashtag_targets)
        logging.info("[%s] Поиск по хештегам: %d", account_name, len(hashtag_targets))

        nearby_targets = await fetch_discovery_nearby(
            client, account_name, cfg, whitelist, blacklist, contact_ids
        )
        targets.extend(nearby_targets)
        logging.info("[%s] Люди рядом: %d", account_name, len(nearby_targets))

    if cfg.discovery.use_feed or not cfg.discovery.enabled:
        feed_targets = await fetch_story_targets(
            client, account_name, cfg, whitelist, blacklist
        )
        if cfg.discovery.skip_contacts and cfg.discovery.enabled:
            feed_targets = [t for t in feed_targets if t.peer_id not in contact_ids]
        targets.extend(feed_targets)
        logging.info("[%s] Лента: %d", account_name, len(feed_targets))

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


async def run_maxlooking(cfg: AppConfig, accounts: list[AccountConfig], discover_only: bool = False) -> None:
    whitelist = load_username_list(BASE_DIR / cfg.whitelist_file)
    blacklist = load_username_list(BASE_DIR / cfg.blacklist_file)

    all_targets: list[StoryTarget] = []
    account_stats: dict[str, AccountStats] = {a.name: AccountStats() for a in accounts}

    for account in accounts:
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
            logging.error("[%s] Не авторизован", account.name)
            await client.disconnect()
            continue
        try:
            targets = await collect_all_targets(
                client, account.name, cfg, whitelist, blacklist
            )
            all_targets.extend(targets)
            logging.info("[%s] Итого спарсено: %d", account.name, len(targets))
        finally:
            await client.disconnect()

    unique: dict[tuple[int, int], StoryTarget] = {}
    for t in all_targets:
        unique[(t.peer_id, t.story_id)] = t
    all_targets = list(unique.values())

    if cfg.shuffle_targets:
        random.shuffle(all_targets)

    by_source: dict[str, int] = {}
    for t in all_targets:
        src = t.source.split(":")[0]
        by_source[src] = by_source.get(src, 0) + 1

    logging.info("Уникальных историй: %d | по источникам: %s", len(all_targets), by_source)

    if not all_targets:
        logging.info("Истории не найдены. Проверьте discovery.hashtags в config.json")
        return

    if discover_only:
        for t in all_targets[:30]:
            logging.info(
                "  @%s | %s | story=%s | %s",
                t.username or t.peer_id,
                t.display_name,
                t.story_id,
                t.source,
            )
        if len(all_targets) > 30:
            logging.info("  ... и ещё %d", len(all_targets) - 30)
        return

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
                "[%s] ❤️ @%s | story=%s | %s | всего %d",
                account_name,
                target.username or target.peer_id,
                target.story_id,
                target.source,
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
        choices=["login", "run", "discover", "check"],
        help="login — вход | discover — только поиск | run — поиск+лайки | check — SpamBot",
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

    if args.command == "discover":
        await run_maxlooking(cfg, accounts, discover_only=True)
        return

    await run_maxlooking(cfg, accounts, discover_only=False)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nОстановлено пользователем.")
