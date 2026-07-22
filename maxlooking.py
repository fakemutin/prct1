#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAXLOOKING PRO — всё в одном файле.
Запуск: python3 maxlooking.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from telethon import TelegramClient, connection, functions, types
from telethon.errors import (
    ChannelPrivateError,
    ChatAdminRequiredError,
    FloodWaitError,
    RPCError,
    SessionPasswordNeededError,
    UserAlreadyParticipantError,
)

# ─────────────────────────── paths ───────────────────────────

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "maxlooking_data.json"
LOG_FILE = BASE_DIR / "maxlooking.log"
SESSION_DIR = BASE_DIR / "sessions"

console = Console()

# ─────────────────────────── search queries for RU channels ───

CHANNEL_SEARCH_QUERIES = [
    "москва чат", "мск чат", "москва общение", "москва беседа", "москва знакомства",
    "спб чат", "питер чат", "петербург чат", "спб знакомства", "питер общение",
    "екатеринбург чат", "екб чат", "казань чат", "новосибирск чат", "нск чат",
    "краснодар чат", "сочи чат", "ростов чат", "самара чат", "уфа чат",
    "воронеж чат", "пермь чат", "волгоград чат", "красноярск чат", "тюмень чат",
    "омск чат", "челябинск чат", "нижний новгород чат", "хабаровск чат",
    "владивосток чат", "калининград чат", "тула чат", "ярославль чат", "барнаул чат",
    "иркутск чат", "знакомства россия", "знакомства мск", "знакомства спб",
    "общение россия", "чат россия", "русский чат", "беседа москва", "беседа спб",
    "dating moscow", "dating russia", "девушки москва", "девушки спб",
    "парни москва", "ищу друзей", "новые знакомства", "общение без границ",
    "москва live", "спб live", "чатик москва", "чатик спб", "тиндер чат",
    "meet moscow", "meet spb", "вписка москва", "тусовка москва", "тусовка спб",
    "молодежь москва", "молодежь спб", "студенты москва", "студенты спб",
    "общалка", "болталка", "разговоры", "интим чат", "флирт чат",
    "love chat", "singles russia", "moscow friends", "piter friends",
    "чат знакомств", "знакомства чат", "ищу парня", "ищу девушку",
    "москва группа", "спб группа", "екатеринбург знакомства", "казань знакомства",
    "краснодар знакомства", "новосибирск знакомства", "ростов знакомства",
    "самара знакомства", "уфа знакомства", "воронеж знакомства", "пермь знакомства",
    "тверь чат", "рязань чат", "курск чат", "брянск чат", "липецк чат",
    "пенза чат", "астрахань чат", "махачкала чат", "ставрополь чат",
    "сургут чат", "томск чат", "кемерово чат", "оренбург чат", "киров чат",
    "чебоксары чат", "калуга чат", "смоленск чат", "владимир чат", "чита чат",
    "белгород чат", "архангельск чат", "мурманск чат", "симферополь чат",
    "севастополь чат", "махачкала общение", "дагестан чат", "татарстан чат",
    "bash chat", "сибирь чат", "урал чат", "юг россии чат", "дальний восток чат",
    "москва 24 чат", "спб 24 чат", "ночной чат", "вечерний чат", "утренний чат",
    "работа москва чат", "фриланс чат", "it чат москва", "бизнес чат москва",
    "авто чат москва", "спорт чат", "музыка чат", "кино чат", "игры чат",
    "anime chat ru", "cosplay ru", "tiktok чат", "insta чат", "блогеры чат",
    "путешествия чат", "отдых сочи", "отдых крым", "море чат", "горы чат",
    "рыбалка чат", "охота чат", "дача чат", "сад чат", "животные чат",
    "кошки чат", "собаки чат", "мамы чат", "папы чат", "беременность чат",
    "свадьба чат", "развод чат", "психология чат", "отношения чат",
    "сексология чат", "lgbt чат", "queer russia", "trans чат",
]

TARGET_OPEN_CHANNELS = 200
DEFAULT_SEED_CHANNELS = ["rian_rub"]

# Предзаполненный конфиг (acc1) — создаёт maxlooking_data.json при первом запуске
BOOTSTRAP_API_ID = 35493327
BOOTSTRAP_API_HASH = "244ecb059d907aba6997462f481640d2"
BOOTSTRAP_ACCOUNTS = [
    {"name": "acc1", "phone": "+13257390879"},
]


# ─────────────────────────── data models ─────────────────────

@dataclass
class Account:
    name: str
    phone: str


@dataclass
class Settings:
    reaction: str = "❤️"
    min_delay_sec: float = 150.0
    max_delay_sec: float = 250.0
    likes_per_hour: int = 18
    likes_per_day: int = 200
    max_participants_per_channel: int = 300
    max_channels_per_run: int = 200
    skip_contacts: bool = True
    russian_filter: bool = True
    auto_join: bool = True
    delay_between_users: float = 2.0
    delay_between_channels: float = 5.0
    # реакции на сообщения в чатах (лимиты выше, чем у историй)
    react_messages: bool = True
    messages_per_chat: int = 80
    msg_reactions_per_hour: int = 120
    msg_reactions_per_day: int = 1000
    msg_min_delay_sec: float = 20.0
    msg_max_delay_sec: float = 60.0


@dataclass
class AppData:
    api_id: int = 0
    api_hash: str = ""
    accounts: list[Account] = field(default_factory=list)
    channels: list[str] = field(default_factory=list)
    settings: Settings = field(default_factory=Settings)

    def save(self) -> None:
        payload = {
            "api_id": self.api_id,
            "api_hash": self.api_hash,
            "accounts": [asdict(a) for a in self.accounts],
            "channels": self.channels,
            "settings": asdict(self.settings),
            "updated_at": datetime.now().isoformat(),
        }
        DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls) -> "AppData":
        if not DATA_FILE.exists():
            return cls()
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        accounts = [Account(**a) for a in raw.get("accounts", [])]
        settings = Settings(**{k: raw["settings"][k] for k in Settings.__dataclass_fields__ if k in raw.get("settings", {})})
        return cls(
            api_id=int(raw.get("api_id", 0)),
            api_hash=raw.get("api_hash", ""),
            accounts=accounts,
            channels=raw.get("channels", []),
            settings=settings,
        )


def ensure_config() -> AppData:
    """Загрузить конфиг или создать из встроенных данных acc1."""
    data = AppData.load()
    if data.api_id and data.accounts:
        return data
    data = AppData(
        api_id=BOOTSTRAP_API_ID,
        api_hash=BOOTSTRAP_API_HASH,
        accounts=[Account(**a) for a in BOOTSTRAP_ACCOUNTS],
        channels=list(DEFAULT_SEED_CHANNELS),
    )
    data.save()
    return data


@dataclass
class StoryTarget:
    peer_id: int
    story_id: int
    peer: Any = None
    username: str | None = None
    display_name: str | None = None
    source: str = ""


@dataclass
class MessageTarget:
    chat_peer: Any
    msg_id: int
    chat_username: str
    sender_id: int | None = None
    sender_username: str | None = None
    preview: str = ""


@dataclass
class AccountStats:
    likes_hour: int = 0
    likes_day: int = 0
    hour_at: float = field(default_factory=time.time)
    day_at: float = field(default_factory=time.time)


@dataclass
class MessageStats:
    reactions_hour: int = 0
    reactions_day: int = 0
    hour_at: float = field(default_factory=time.time)
    day_at: float = field(default_factory=time.time)


# ─────────────────────────── logging ───────────────────────────

def setup_log() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
        ],
    )


# ─────────────────────────── helpers ─────────────────────────

def session_path(name: str) -> Path:
    SESSION_DIR.mkdir(exist_ok=True)
    return SESSION_DIR / name


def make_client(data: AppData, account: Account) -> TelegramClient:
    """Прямое MTProto-подключение без VPN (Telegram DC, не прокси)."""
    return TelegramClient(
        str(session_path(account.name)),
        data.api_id,
        data.api_hash,
        connection=connection.ConnectionTcpFull,
        connection_retries=10,
        retry_delay=5,
        timeout=60,
        auto_reconnect=True,
        use_ipv6=False,
        device_model="TrubaSatka",
        system_version="Android 13",
        app_version="1.0",
        lang_code="ru",
        system_lang_code="ru-RU",
    )


def display_name(entity: Any) -> str:
    t = getattr(entity, "title", None)
    if t:
        return t
    return f"{getattr(entity, 'first_name', '')} {getattr(entity, 'last_name', '')}".strip() or "?"


def username_of(entity: Any) -> str | None:
    u = getattr(entity, "username", None)
    return u.lower() if u else None


def story_active(story: Any) -> bool:
    if getattr(story, "out", False) or getattr(story, "sent_reaction", None):
        return False
    exp = getattr(story, "expire_date", 0) or 0
    return not exp or exp >= int(time.time())


def is_russian(user: Any, enabled: bool) -> bool:
    if not enabled:
        return True
    lang = (getattr(user, "lang_code", None) or "").lower()
    if lang in ("ru", "uk", "be", "kk"):
        return True
    phone = (getattr(user, "phone", None) or "").strip()
    if phone.startswith("7") or phone.startswith("+7"):
        return True
    name = display_name(user)
    return any("\u0400" <= c <= "\u04ff" for c in name)


def reset_stats(s: AccountStats) -> None:
    now = time.time()
    if now - s.hour_at >= 3600:
        s.likes_hour = 0
        s.hour_at = now
    if now - s.day_at >= 86400:
        s.likes_day = 0
        s.day_at = now


def can_like(s: AccountStats, cfg: Settings) -> bool:
    reset_stats(s)
    return s.likes_hour < cfg.likes_per_hour and s.likes_day < cfg.likes_per_day


def reset_msg_stats(s: MessageStats) -> None:
    now = time.time()
    if now - s.hour_at >= 3600:
        s.reactions_hour = 0
        s.hour_at = now
    if now - s.day_at >= 86400:
        s.reactions_day = 0
        s.day_at = now


def can_react_msg(s: MessageStats, cfg: Settings) -> bool:
    reset_msg_stats(s)
    return (
        s.reactions_hour < cfg.msg_reactions_per_hour
        and s.reactions_day < cfg.msg_reactions_per_day
    )


def ensure_seed_channels(data: AppData) -> None:
    merged = list(DEFAULT_SEED_CHANNELS)
    for ch in data.channels:
        if ch.lower() not in {c.lower() for c in merged}:
            merged.append(ch)
    if merged != data.channels:
        data.channels = merged
        data.save()


# ─────────────────────────── UI ────────────────────────────────

def banner() -> None:
    console.clear()
    console.print(
        Panel.fit(
            "[bold magenta]MAXLOOKING PRO[/] [dim]v2.1[/]\n"
            "[cyan]Каналы → истории ❤️ + реакции на сообщения 💬[/]",
            border_style="magenta",
            box=box.DOUBLE,
        )
    )


def show_status(data: AppData) -> None:
    t = Table(box=box.ROUNDED, show_header=False, padding=(0, 1))
    t.add_column(style="dim")
    t.add_column(style="bold green")
    t.add_row("API", "✅ настроен" if data.api_id else "❌ не настроен")
    t.add_row("Аккаунты", str(len(data.accounts)))
    t.add_row("Каналы (открытые)", str(len(data.channels)))
    t.add_row("Истории/час", str(data.settings.likes_per_hour))
    t.add_row("Реакции/час", str(data.settings.msg_reactions_per_hour))
    t.add_row("Пауза истории", f"{data.settings.min_delay_sec:.0f}–{data.settings.max_delay_sec:.0f}с")
    t.add_row("Пауза реакции", f"{data.settings.msg_min_delay_sec:.0f}–{data.settings.msg_max_delay_sec:.0f}с")
    console.print(t)


def main_menu() -> str:
    banner()
    show_status(ensure_config())
    console.print()
    console.print("  [bold cyan]1[/]  🚀  [bold]БЫСТРЫЙ СТАРТ[/] — всё автоматически")
    console.print("  [bold cyan]2[/]  🔑  Настроить API и аккаунты")
    console.print("  [bold cyan]3[/]  📡  Найти 200 открытых каналов")
    console.print("  [bold cyan]4[/]  ❤️   Истории + реакции в чатах")
    console.print("  [bold cyan]5[/]  💬  Только реакции на сообщения")
    console.print("  [bold cyan]6[/]  🔍  Только поиск (без лайков)")
    console.print("  [bold cyan]7[/]  ⚙️   Настройки лимитов")
    console.print("  [bold cyan]8[/]  📊  Статус @SpamBot")
    console.print("  [bold cyan]0[/]  🚪  Выход")
    console.print()
    return Prompt.ask("[bold]Выберите[/]", choices=["0", "1", "2", "3", "4", "5", "6", "7", "8"], default="1")


# ─────────────────────────── setup wizard ────────────────────

def setup_api(data: AppData) -> None:
    banner()
    console.print(Panel("Настройка API с [link=https://my.telegram.org]my.telegram.org[/link]", style="cyan"))
    if not data.api_id:
        data.api_id = IntPrompt.ask("api_id")
    if not data.api_hash:
        data.api_hash = Prompt.ask("api_hash").strip()

    console.print("\n[bold]Аккаунты[/] (пустой телефон = стоп)")
    idx = len(data.accounts) + 1
    while True:
        phone = Prompt.ask(f"Телефон аккаунта #{idx} (+7...)", default="").strip()
        if not phone:
            break
        name = f"acc{idx}"
        data.accounts.append(Account(name=name, phone=phone))
        idx += 1

    data.save()
    console.print("\n[green]✅ Сохранено в maxlooking_data.json[/]")
    Prompt.ask("Enter")


# ─────────────────────────── auth ──────────────────────────────

async def login_all(data: AppData, ui: Console = console) -> bool:
    ok = True
    for acc in data.accounts:
        client = make_client(data, acc)
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            ui.print(f"  [green]✓[/] {acc.name}: @{me.username or me.id}")
            await client.disconnect()
            continue

        ui.print(f"\n[yellow]Вход:[/] {acc.phone}")
        await client.send_code_request(acc.phone)
        code = Prompt.ask("Код из Telegram")
        try:
            await client.sign_in(acc.phone, code)
        except SessionPasswordNeededError:
            pwd = Prompt.ask("Пароль 2FA", password=True)
            await client.sign_in(password=pwd)

        me = await client.get_me()
        ui.print(f"  [green]✓[/] Вошли: @{me.username or me.id}")
        await client.disconnect()
    return ok


# ─────────────────────────── channel discovery ─────────────────

async def test_open_participants(client: TelegramClient, entity: Any) -> tuple[bool, int]:
    if not getattr(entity, "username", None):
        return False, 0

    try:
        full = await client(functions.channels.GetFullChannelRequest(entity))
        if getattr(full.full_chat, "participants_hidden", False):
            return False, 0
    except RPCError:
        pass

    try:
        count = 0
        async for _ in client.iter_participants(entity, limit=10):
            count += 1
        return count >= 3, count
    except (ChatAdminRequiredError, ChannelPrivateError, RPCError):
        return False, 0


async def search_channels_query(
    client: TelegramClient,
    query: str,
    seen: set[int],
) -> list[Any]:
    found: list[Any] = []
    try:
        result = await client(
            functions.contacts.SearchRequest(q=query, limit=50)
        )
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 5)
        return []
    except RPCError:
        return []

    for chat in result.chats:
        if chat.id in seen:
            continue
        if not getattr(chat, "username", None):
            continue
        if getattr(chat, "megagroup", False) or getattr(chat, "broadcast", False):
            found.append(chat)
            seen.add(chat.id)
    return found


async def discover_open_channels(
    data: AppData,
    target: int = TARGET_OPEN_CHANNELS,
    on_progress: Callable[[str], None] | None = None,
) -> list[str]:
    if not data.accounts:
        raise RuntimeError("Нет аккаунтов")

    acc = data.accounts[0]
    client = make_client(data, acc)
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        raise RuntimeError("Аккаунт не авторизован — сначала войдите")

    open_channels: dict[str, dict] = {u: {"title": u} for u in data.channels}
    seen_ids: set[int] = set()
    queries = list(CHANNEL_SEARCH_QUERIES)
    random.shuffle(queries)

    checked = 0
    for query in queries:
        if len(open_channels) >= target:
            break

        if on_progress:
            on_progress(f"Поиск: «{query}» | найдено {len(open_channels)}/{target}")

        candidates = await search_channels_query(client, query, seen_ids)
        await asyncio.sleep(1.5)

        for entity in candidates:
            if len(open_channels) >= target:
                break

            username = entity.username.lower()
            if username in open_channels:
                continue

            checked += 1
            if on_progress:
                on_progress(f"Проверка @{username} ({checked}) | открытых: {len(open_channels)}")

            is_open, pcount = await test_open_participants(client, entity)
            if is_open:
                open_channels[username] = {
                    "title": display_name(entity),
                    "members": getattr(entity, "participants_count", pcount),
                }
                data.channels = list(open_channels.keys())
                data.save()
                if on_progress:
                    on_progress(f"✓ @{username} | {len(open_channels)}/{target}")
            await asyncio.sleep(0.8)

    # joined public channels
    if len(open_channels) < target:
        async for dialog in client.iter_dialogs():
            if len(open_channels) >= target:
                break
            entity = dialog.entity
            if not dialog.is_channel or not getattr(entity, "username", None):
                continue
            username = entity.username.lower()
            if username in open_channels:
                continue
            is_open, pcount = await test_open_participants(client, entity)
            if is_open:
                open_channels[username] = {"title": display_name(entity), "members": pcount}
                data.channels = list(open_channels.keys())
                data.save()

    await client.disconnect()

    data.channels = list(open_channels.keys())
    data.save()
    return data.channels


async def ui_discover_channels(data: AppData) -> None:
    banner()
    ensure_seed_channels(data)
    if not data.api_id or not data.accounts:
        console.print("[red]Сначала настрой API (пункт 2)[/]")
        Prompt.ask("Enter")
        return

    console.print(Panel(f"Ищем [bold]{TARGET_OPEN_CHANNELS}[/] каналов с открытым списком участников...", style="cyan"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Поиск...", total=TARGET_OPEN_CHANNELS)
        last_count = 0

        def on_progress(msg: str) -> None:
            nonlocal last_count
            progress.update(task, description=msg[:70])
            if len(data.channels) > last_count:
                last_count = len(data.channels)
                progress.update(task, completed=last_count)

        await discover_open_channels(data, on_progress=on_progress)
        progress.update(task, completed=len(data.channels), description="Готово!")

    console.print(f"\n[bold green]✅ Найдено {len(data.channels)} открытых каналов[/]")
    if data.channels[:10]:
        for u in data.channels[:10]:
            console.print(f"  • @{u}")
        if len(data.channels) > 10:
            console.print(f"  [dim]... и ещё {len(data.channels) - 10}[/]")
    Prompt.ask("Enter")


# ─────────────────────────── story engine ────────────────────

async def get_contacts(client: TelegramClient) -> set[int]:
    try:
        r = await client(functions.contacts.GetContactsRequest(hash=0))
        return {u.id for u in r.users}
    except RPCError:
        return set()


async def user_stories(
    client: TelegramClient,
    user: Any,
    channel_name: str,
    contacts: set[int],
    cfg: Settings,
) -> list[StoryTarget]:
    if getattr(user, "bot", False) or getattr(user, "deleted", False):
        return []
    if cfg.skip_contacts and user.id in contacts:
        return []
    if not is_russian(user, cfg.russian_filter):
        return []

    try:
        ps = await client(functions.stories.GetPeerStoriesRequest(peer=user))
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 3)
        return []
    except RPCError:
        return []

    stories = getattr(ps.stories, "stories", []) or []
    if not stories:
        return []

    peer = await client.get_input_entity(user)
    out: list[StoryTarget] = []
    for s in stories:
        if story_active(s):
            out.append(
                StoryTarget(
                    peer_id=user.id,
                    story_id=s.id,
                    peer=peer,
                    username=username_of(user),
                    display_name=display_name(user),
                    source=f"@{channel_name}",
                )
            )
    return out


async def scan_channels(
    client: TelegramClient,
    data: AppData,
    on_status: Callable[[str], None] | None = None,
) -> list[StoryTarget]:
    cfg = data.settings
    contacts = await get_contacts(client)
    channels = data.channels[: cfg.max_channels_per_run]
    random.shuffle(channels)

    if not channels:
        return []

    targets: list[StoryTarget] = []
    seen_users: set[int] = set()

    for i, username in enumerate(channels, 1):
        if on_status:
            on_status(f"Канал {i}/{len(channels)}: @{username}")

        try:
            entity = await client.get_entity(username)
        except (RPCError, ValueError):
            continue

        if cfg.auto_join:
            try:
                await client(functions.channels.JoinChannelRequest(entity))
            except UserAlreadyParticipantError:
                pass
            except RPCError:
                continue

        try:
            async for user in client.iter_participants(entity, limit=cfg.max_participants_per_channel):
                if user.id in seen_users:
                    continue
                seen_users.add(user.id)
                targets.extend(await user_stories(client, user, username, contacts, cfg))
                await asyncio.sleep(cfg.delay_between_users)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 10)
        except RPCError:
            pass

        await asyncio.sleep(cfg.delay_between_channels)

    return targets


async def collect_targets(
    data: AppData,
    on_status: Callable[[str], None] | None = None,
) -> list[StoryTarget]:
    all_targets: list[StoryTarget] = []
    for acc in data.accounts:
        client = make_client(data, acc)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            continue
        if on_status:
            on_status(f"Сканирую с {acc.name}...")
        all_targets.extend(await scan_channels(client, data, on_status))
        await client.disconnect()

    unique: dict[tuple[int, int], StoryTarget] = {}
    for t in all_targets:
        unique[(t.peer_id, t.story_id)] = t
    return list(unique.values())


async def scan_chat_messages(
    client: TelegramClient,
    data: AppData,
    on_status: Callable[[str], None] | None = None,
) -> list[MessageTarget]:
    cfg = data.settings
    if not cfg.react_messages:
        return []

    me = await client.get_me()
    contacts = await get_contacts(client)
    channels = data.channels[: cfg.max_channels_per_run]
    random.shuffle(channels)

    targets: list[MessageTarget] = []
    seen_msgs: set[tuple[int, int]] = set()

    for i, username in enumerate(channels, 1):
        if on_status:
            on_status(f"Сообщения {i}/{len(channels)}: @{username}")

        try:
            entity = await client.get_entity(username)
        except (RPCError, ValueError):
            continue

        if cfg.auto_join:
            try:
                await client(functions.channels.JoinChannelRequest(entity))
            except UserAlreadyParticipantError:
                pass
            except RPCError:
                continue

        chat_peer = await client.get_input_entity(entity)

        try:
            async for msg in client.iter_messages(entity, limit=cfg.messages_per_chat):
                if not msg or msg.out:
                    continue
                key = (entity.id, msg.id)
                if key in seen_msgs:
                    continue
                seen_msgs.add(key)

                sender = await msg.get_sender()
                if sender is None:
                    continue
                if getattr(sender, "bot", False) or getattr(sender, "deleted", False):
                    continue
                if cfg.skip_contacts and sender.id in contacts:
                    continue
                if sender.id == me.id:
                    continue
                if not is_russian(sender, cfg.russian_filter):
                    continue

                preview = (msg.message or "")[:60].replace("\n", " ")
                targets.append(
                    MessageTarget(
                        chat_peer=chat_peer,
                        msg_id=msg.id,
                        chat_username=username,
                        sender_id=sender.id,
                        sender_username=username_of(sender),
                        preview=preview or "[медиа]",
                    )
                )
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 10)
        except RPCError:
            pass

        await asyncio.sleep(cfg.delay_between_channels)

    return targets


async def collect_message_targets(
    data: AppData,
    on_status: Callable[[str], None] | None = None,
) -> list[MessageTarget]:
    all_targets: list[MessageTarget] = []
    for acc in data.accounts:
        client = make_client(data, acc)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            continue
        if on_status:
            on_status(f"Сообщения: {acc.name}...")
        all_targets.extend(await scan_chat_messages(client, data, on_status))
        await client.disconnect()

    unique: dict[tuple[str, int], MessageTarget] = {}
    for t in all_targets:
        unique[(t.chat_username, t.msg_id)] = t
    return list(unique.values())


async def like_targets(
    data: AppData,
    targets: list[StoryTarget],
    on_like: Callable[[str], None] | None = None,
) -> int:
    if not targets:
        return 0

    cfg = data.settings
    stats = {a.name: AccountStats() for a in data.accounts}
    clients: dict[str, TelegramClient] = {}

    for acc in data.accounts:
        c = make_client(data, acc)
        await c.connect()
        if await c.is_user_authorized():
            clients[acc.name] = c
        else:
            await c.disconnect()

    if not clients:
        return 0

    names = list(clients.keys())
    idx = 0
    done = 0

    for target in random.sample(targets, len(targets)):
        picked = None
        for _ in range(len(names)):
            name = names[idx % len(names)]
            idx += 1
            if can_like(stats[name], cfg):
                picked = name
                break

        if not picked:
            wait = 600
            if on_like:
                on_like(f"Лимит/час — ждём {wait // 60} мин")
            await asyncio.sleep(wait)
            for s in stats.values():
                reset_stats(s)
            picked = names[0]

        client = clients[picked]
        s = stats[picked]

        delay = random.uniform(cfg.min_delay_sec, cfg.max_delay_sec)
        await asyncio.sleep(delay)

        try:
            peer = target.peer or await client.get_input_entity(target.peer_id)
            await client(
                functions.stories.SendReactionRequest(
                    peer=peer,
                    story_id=target.story_id,
                    reaction=types.ReactionEmoji(emoticon=cfg.reaction),
                    add_to_recent=False,
                )
            )
            s.likes_hour += 1
            s.likes_day += 1
            done += 1
            msg = f"❤️ @{target.username or target.peer_id} | {picked} | {s.likes_hour}/{cfg.likes_per_hour}ч"
            if on_like:
                on_like(msg)
            logging.info(msg)
        except FloodWaitError as e:
            if on_like:
                on_like(f"FLOOD_WAIT {e.seconds}с — ждём")
            await asyncio.sleep(e.seconds + random.randint(5, 15))
        except RPCError as e:
            logging.warning("like error: %s", e)

    for c in clients.values():
        await c.disconnect()
    return done


async def react_message_targets(
    data: AppData,
    targets: list[MessageTarget],
    on_react: Callable[[str], None] | None = None,
) -> int:
    if not targets:
        return 0

    cfg = data.settings
    stats = {a.name: MessageStats() for a in data.accounts}
    clients: dict[str, TelegramClient] = {}

    for acc in data.accounts:
        c = make_client(data, acc)
        await c.connect()
        if await c.is_user_authorized():
            clients[acc.name] = c
        else:
            await c.disconnect()

    if not clients:
        return 0

    names = list(clients.keys())
    idx = 0
    done = 0

    for target in random.sample(targets, len(targets)):
        picked = None
        for _ in range(len(names)):
            name = names[idx % len(names)]
            idx += 1
            if can_react_msg(stats[name], cfg):
                picked = name
                break

        if not picked:
            wait = 300
            if on_react:
                on_react(f"Лимит реакций/час — ждём {wait // 60} мин")
            await asyncio.sleep(wait)
            for s in stats.values():
                reset_msg_stats(s)
            picked = names[0]

        client = clients[picked]
        s = stats[picked]
        delay = random.uniform(cfg.msg_min_delay_sec, cfg.msg_max_delay_sec)
        await asyncio.sleep(delay)

        try:
            await client(
                functions.messages.SendReactionRequest(
                    peer=target.chat_peer,
                    msg_id=target.msg_id,
                    reaction=[types.ReactionEmoji(emoticon=cfg.reaction)],
                    add_to_recent=False,
                )
            )
            s.reactions_hour += 1
            s.reactions_day += 1
            done += 1
            msg = (
                f"💬 @{target.sender_username or target.sender_id} "
                f"в @{target.chat_username} | {picked} | "
                f"{s.reactions_hour}/{cfg.msg_reactions_per_hour}ч"
            )
            if on_react:
                on_react(msg)
            logging.info(msg)
        except FloodWaitError as e:
            if on_react:
                on_react(f"FLOOD_WAIT {e.seconds}с — ждём")
            await asyncio.sleep(e.seconds + random.randint(3, 10))
        except RPCError as e:
            logging.warning("react error @%s #%s: %s", target.chat_username, target.msg_id, e)

    for c in clients.values():
        await c.disconnect()
    return done


async def run_pipeline(
    data: AppData,
    discover_only: bool = False,
    stories_only: bool = False,
    messages_only: bool = False,
) -> None:
    banner()
    ensure_seed_channels(data)

    if not data.channels:
        console.print("[yellow]Каналов нет — запускаю автопоиск...[/]")
        with console.status("[cyan]Ищем открытые каналы..."):
            await discover_open_channels(data, target=min(50, TARGET_OPEN_CHANNELS))

    do_stories = not messages_only
    do_messages = not stories_only and data.settings.react_messages

    story_targets: list[StoryTarget] = []
    msg_targets: list[MessageTarget] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Сканирование...", total=None)

        def status(msg: str) -> None:
            progress.update(task, description=msg)

        if do_stories:
            story_targets = await collect_targets(data, on_status=status)
        if do_messages:
            msg_targets = await collect_message_targets(data, on_status=status)

        progress.update(
            task,
            description=f"Историй: {len(story_targets)} | Сообщений: {len(msg_targets)}",
        )

    console.print(f"\n[bold green]Историй: {len(story_targets)}[/] | [bold cyan]Сообщений: {len(msg_targets)}[/]")

    if discover_only:
        for t in story_targets[:10]:
            console.print(f"  📖 @{t.username or t.peer_id} — {t.source}")
        for t in msg_targets[:10]:
            console.print(
                f"  💬 @{t.sender_username or t.sender_id} в @{t.chat_username}: {t.preview}"
            )
        Prompt.ask("Enter")
        return

    if not story_targets and not msg_targets:
        console.print("[red]Нечего лайкать. Попробуй найти каналы (пункт 3).[/]")
        Prompt.ask("Enter")
        return

    run_stories = False
    run_msgs = False

    if story_targets and do_stories:
        run_stories = Confirm.ask(
            f"Лайкать {len(story_targets)} историй? (лимит {data.settings.likes_per_hour}/час)",
            default=True,
        )
    if msg_targets and do_messages:
        run_msgs = Confirm.ask(
            f"Реакции на {len(msg_targets)} сообщений? (лимит {data.settings.msg_reactions_per_hour}/час)",
            default=True,
        )

    total_done = 0

    if run_stories:
        console.print()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Истории...", total=None)
            done = await like_targets(
                data, story_targets, on_like=lambda m: progress.update(task, description=m)
            )
            total_done += done
        console.print(f"[green]✓ Историй: {done}[/]")

    if run_msgs:
        console.print()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Сообщения...", total=None)
            done = await react_message_targets(
                data, msg_targets, on_react=lambda m: progress.update(task, description=m)
            )
            total_done += done
        console.print(f"[green]✓ Реакций: {done}[/]")

    console.print(f"\n[bold green]✅ Готово! Всего действий: {total_done}[/]")
    Prompt.ask("Enter")


async def needs_login(data: AppData) -> bool:
    for acc in data.accounts:
        path = session_path(acc.name).with_suffix(".session")
        if not path.exists():
            return True
        client = make_client(data, acc)
        await client.connect()
        ok = await client.is_user_authorized()
        await client.disconnect()
        if not ok:
            return True
    return False


async def go_mode() -> None:
    """Только код из Telegram → сразу работа. Без меню и VPN."""
    setup_log()
    SESSION_DIR.mkdir(exist_ok=True)
    data = ensure_config()
    ensure_seed_channels(data)

    banner()
    console.print(
        Panel(
            f"[bold]Аккаунт:[/] {data.accounts[0].phone}\n"
            f"[bold]API:[/] TrubaSatka (id {data.api_id})\n"
            "[cyan]VPN не нужен — прямое подключение к серверам Telegram[/]",
            title="СТАРТ",
            style="green",
        )
    )

    if await needs_login(data):
        console.print("\n[yellow]Введи код из Telegram[/] (придёт в приложение или SMS)\n")
        await login_all(data)
    else:
        console.print("\n[green]✓ Сессия уже сохранена, вход не нужен[/]\n")

    await quick_start(data)


async def quick_start(data: AppData) -> None:
    banner()
    console.print(Panel("[bold]БЫСТРЫЙ СТАРТ[/] — каналы → истории + реакции", style="green"))

    ensure_seed_channels(data)

    if len(data.channels) < 50:
        console.print(f"\n[cyan]Поиск открытых каналов (цель: {TARGET_OPEN_CHANNELS})...[/]")
        with console.status("[bold cyan]Ищем каналы с открытыми участниками..."):
            await discover_open_channels(data)
        console.print(f"[green]✓[/] Каналов: {len(data.channels)}")
    else:
        console.print(f"\n[green]Каналы уже есть:[/] {len(data.channels)}")

    console.print("\n[cyan]Сканирование + лайки + реакции...[/]")
    await run_pipeline(data, discover_only=False)


async def check_spambot(data: AppData) -> None:
    banner()
    for acc in data.accounts:
        client = make_client(data, acc)
        await client.connect()
        if not await client.is_user_authorized():
            console.print(f"[red]{acc.name}: не авторизован[/]")
            await client.disconnect()
            continue
        async for msg in client.iter_messages("SpamBot", limit=1):
            console.print(Panel(msg.text or "(пусто)", title=f"@{acc.name}", border_style="yellow"))
        await client.disconnect()
    Prompt.ask("Enter")


def edit_settings(data: AppData) -> None:
    banner()
    s = data.settings
    console.print(Panel("Настройки (Enter = оставить)", style="cyan"))
    s.likes_per_hour = IntPrompt.ask("Лайков/час", default=s.likes_per_hour)
    s.likes_per_day = IntPrompt.ask("Лайков/день", default=s.likes_per_day)
    s.min_delay_sec = float(Prompt.ask("Мин. пауза (сек)", default=str(int(s.min_delay_sec))))
    s.max_delay_sec = float(Prompt.ask("Макс. пауза (сек)", default=str(int(s.max_delay_sec))))
    s.max_participants_per_channel = IntPrompt.ask("Участников/канал", default=s.max_participants_per_channel)
    s.max_channels_per_run = IntPrompt.ask("Каналов за прогон", default=s.max_channels_per_run)
    console.print("\n[bold]Реакции на сообщения[/]")
    s.react_messages = Confirm.ask("Включить реакции в чатах", default=s.react_messages)
    s.msg_reactions_per_hour = IntPrompt.ask("Реакций/час", default=s.msg_reactions_per_hour)
    s.msg_reactions_per_day = IntPrompt.ask("Реакций/день", default=s.msg_reactions_per_day)
    s.messages_per_chat = IntPrompt.ask("Сообщений/чат", default=s.messages_per_chat)
    s.msg_min_delay_sec = float(Prompt.ask("Мин. пауза реакций", default=str(int(s.msg_min_delay_sec))))
    s.msg_max_delay_sec = float(Prompt.ask("Макс. пауза реакций", default=str(int(s.msg_max_delay_sec))))
    data.save()
    console.print("[green]✅ Сохранено[/]")
    Prompt.ask("Enter")


# ─────────────────────────── main loop ─────────────────────────

async def async_main() -> None:
    setup_log()
    SESSION_DIR.mkdir(exist_ok=True)

    while True:
        choice = main_menu()
        data = ensure_config()

        if choice == "0":
            console.print("[dim]Пока![/]")
            break
        elif choice == "1":
            await quick_start(data)
        elif choice == "2":
            setup_api(data)
        elif choice == "3":
            await ui_discover_channels(data)
        elif choice == "4":
            if not data.api_id:
                setup_api(data)
                data = AppData.load()
            ensure_seed_channels(data)
            await login_all(data)
            await run_pipeline(data, discover_only=False)
        elif choice == "5":
            if not data.api_id:
                setup_api(data)
                data = AppData.load()
            ensure_seed_channels(data)
            await login_all(data)
            await run_pipeline(data, messages_only=True)
        elif choice == "6":
            if not data.api_id:
                setup_api(data)
                data = AppData.load()
            ensure_seed_channels(data)
            await login_all(data)
            await run_pipeline(data, discover_only=True)
        elif choice == "7":
            edit_settings(data)
        elif choice == "8":
            await check_spambot(data)


def main() -> None:
    try:
        if len(sys.argv) > 1 and sys.argv[1] in ("go", "start"):
            asyncio.run(go_mode())
            return
        asyncio.run(async_main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Остановлено[/]")


if __name__ == "__main__":
    main()
