#!/usr/bin/env python3
"""Satka VPN — support userbot."""

from __future__ import annotations

import asyncio
import logging
import re
import sys
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

import httpx
from telethon import TelegramClient, events
from telethon.tl.functions.account import UpdateStatusRequest
from telethon.tl.types import User

from canned_responses import STICKER_REPLY, match_canned, with_first_hint
from config import Settings
from llm_client import LlmSupportClient, user_requests_operator
from message_filters import classify_message

BOT_VERSION = "2026-07-30-v5"

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("satka-support-ai")

AI_USER_CMD = re.compile(r"^/ai\s+@?([A-Za-z0-9_]{3,32})\s+(block|unblock)\s*$", re.IGNORECASE)


@dataclass
class UserSession:
    history: deque = field(default_factory=lambda: deque(maxlen=24))
    last_escalation_ts: float = 0.0
    unclear_streak: int = 0
    greeted: bool = False


class SupportUserbot:
    def __init__(self, settings: Settings, client: TelegramClient) -> None:
        self.settings = settings
        self.client = client
        self.ai = LlmSupportClient(settings)
        self.sessions: dict[int, UserSession] = defaultdict(UserSession)
        self._escalation_cooldown_sec = 300
        self._me_id: int | None = None
        self._blocked_chats_until: dict[int, float] = {}
        self._ai_enabled: bool = settings.ai_globally_enabled
        self._chat_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._llm_sem = asyncio.Semaphore(settings.max_concurrent_replies)
        self._active_tasks: set[asyncio.Task] = set()

    async def _keep_online_loop(self) -> None:
        while True:
            try:
                await self.client(UpdateStatusRequest(offline=False))
            except Exception:
                logger.debug("Online status update failed", exc_info=True)
            await asyncio.sleep(self.settings.online_keepalive_sec)

    def _session(self, user_id: int) -> UserSession:
        return self.sessions[user_id]

    def _chat_is_blocked(self, chat_id: int) -> bool:
        if not self._ai_enabled:
            return True
        return self._blocked_chats_until.get(chat_id, 0) > time.time()

    def _block_chat(self, chat_id: int, seconds: int) -> None:
        self._blocked_chats_until[chat_id] = time.time() + seconds

    def _unblock_chat(self, chat_id: int) -> None:
        self._blocked_chats_until.pop(chat_id, None)

    async def _saved_messages_reply(self, event: events.NewMessage.Event, text: str) -> None:
        if self._me_id and event.chat_id == self._me_id:
            await self.client.send_message(self._me_id, text, link_preview=False)

    async def _handle_saved_commands(self, event: events.NewMessage.Event, text: str) -> bool:
        if not self._me_id or event.chat_id != self._me_id:
            return False

        match = AI_USER_CMD.match(text.strip())
        if match:
            username = match.group(1)
            action = match.group(2).lower()
            try:
                entity = await self.client.get_entity(username)
                if not isinstance(entity, User):
                    await self._saved_messages_reply(event, f"@{username} — не пользователь Telegram.")
                    return True
                chat_id = entity.id
                if action == "block":
                    secs = self.settings.ai_block_sec
                    self._block_chat(chat_id, secs)
                    hours = secs / 3600
                    label = f"{int(hours)} ч." if secs % 3600 == 0 else f"{secs // 60} мин."
                    await self._saved_messages_reply(
                        event,
                        f"AI заблокирован для @{username} (id {chat_id}) на {label}",
                    )
                    logger.info("Operator blocked AI for @%s (%s) for %ss", username, chat_id, secs)
                else:
                    self._unblock_chat(chat_id)
                    await self._saved_messages_reply(
                        event,
                        f"AI разблокирован для @{username} (id {chat_id})",
                    )
                    logger.info("Operator unblocked AI for @%s (%s)", username, chat_id)
            except Exception:
                logger.exception("Failed to resolve @%s", username)
                await self._saved_messages_reply(event, f"Не нашёл @{username}. Проверьте username.")
            return True

        low = text.lower()
        if low == "/ai off":
            self._ai_enabled = False
            await self._saved_messages_reply(event, "AI выключен глобально.")
            logger.info("AI disabled globally by operator")
            return True
        if low == "/ai on":
            self._ai_enabled = True
            self._blocked_chats_until.clear()
            await self._saved_messages_reply(event, "AI включён. Все блокировки сброшены.")
            logger.info("AI enabled globally by operator")
            return True
        if low in {"/ai resume", "/ai reset"}:
            self._blocked_chats_until.clear()
            await self._saved_messages_reply(event, "Все блокировки по чатам сброшены.")
            logger.info("All per-chat AI blocks cleared by operator")
            return True
        if low == "/ai status":
            blocked = sum(1 for t in self._blocked_chats_until.values() if t > time.time())
            await self._saved_messages_reply(
                event,
                f"AI: {'ВЫКЛ' if not self._ai_enabled else 'ВКЛ'}\nЗаблокированных чатов: {blocked}",
            )
            return True
        if low == "/ai help":
            await self._saved_messages_reply(
                event,
                "Команды (только в Избранное):\n"
                "/ai @username block — ИИ не отвечает 1 час\n"
                "/ai @username unblock — снять блок\n"
                "/ai on — включить ИИ\n"
                "/ai off — выключить ИИ\n"
                "/ai resume — сбросить все блокировки\n"
                "/ai status — статус",
            )
            return True

        return False

    async def _mark_read(self, event: events.NewMessage.Event) -> None:
        try:
            await self.client.send_read_acknowledge(event.chat_id, max_id=event.message.id)
        except Exception:
            logger.debug("mark_read failed for chat %s", event.chat_id, exc_info=True)

    async def _reply(
        self,
        event: events.NewMessage.Event,
        text: str,
        *,
        session: UserSession | None = None,
    ) -> str:
        await self._mark_read(event)
        if session is not None:
            text = with_first_hint(text, first_contact=len(session.history) == 0)
        await event.respond(text, link_preview=False)
        return text

    async def handle_outgoing(self, event: events.NewMessage.Event) -> None:
        # Только команды /ai в Избранном. Ответы оператору в чатах пользователей — игнорируем.
        if not event.out or not event.is_private or not event.message:
            return
        if not self._me_id or event.chat_id != self._me_id:
            return

        text = (event.message.text or "").strip()
        if not text:
            return

        await self._handle_saved_commands(event, text)

    async def _send_admin_alerts(
        self,
        *,
        user_id: int,
        username: str | None,
        display_name: str | None,
        reason: str,
        last_message: str,
    ) -> None:
        uname = f"@{username}" if username else "без username"
        name = display_name or "—"
        header = (
            f"🚨🚨🚨 СРОЧНО ЗАЙДИТЕ В ПОДДЕРЖКУ 🚨🚨🚨\n\n"
            f"👤 {uname} ({name})\n"
            f"🆔 `{user_id}`\n"
            f"📌 {reason}\n\n"
            f"💬 Последнее сообщение:\n{last_message[:1200]}"
        )

        url = f"https://api.telegram.org/bot{self.settings.alert_bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=30) as http:
            for i in range(self.settings.alert_repeat_count):
                text = header if i == 0 else f"🔁 Повтор {i + 1}/{self.settings.alert_repeat_count}\n\n{header}"
                try:
                    await http.post(
                        url,
                        json={
                            "chat_id": self.settings.admin_chat_id,
                            "text": text,
                            "parse_mode": "Markdown",
                        },
                    )
                except Exception:
                    logger.exception("Failed admin alert %s/%s", i + 1, self.settings.alert_repeat_count)
                if i + 1 < self.settings.alert_repeat_count:
                    await asyncio.sleep(self.settings.alert_repeat_delay_sec)

            try:
                await http.post(
                    url,
                    json={
                        "chat_id": self.settings.admin_chat_id,
                        "text": f"@{self.settings.admin_username} — нужен оператор в поддержке!",
                    },
                )
            except Exception:
                logger.debug("Admin username ping skipped")

    async def _maybe_escalate(
        self,
        session: UserSession,
        *,
        user_id: int,
        username: str | None,
        display_name: str | None,
        reason: str,
        last_message: str,
        force: bool = False,
    ) -> None:
        now = time.time()
        if not force and now - session.last_escalation_ts < self._escalation_cooldown_sec:
            return
        session.last_escalation_ts = now
        await self._send_admin_alerts(
            user_id=user_id,
            username=username,
            display_name=display_name,
            reason=reason,
            last_message=last_message,
        )

    async def handle_message(self, event: events.NewMessage.Event) -> None:
        if not event.is_private or not event.message:
            return

        sender = await event.get_sender()
        if not isinstance(sender, User) or sender.bot or sender.id == self._me_id:
            return

        if self.settings.allowed_chat_ids and event.chat_id not in self.settings.allowed_chat_ids:
            return

        if self._chat_is_blocked(event.chat_id):
            until = self._blocked_chats_until.get(event.chat_id, 0)
            logger.info(
                "Skipping AI for chat %s — manually blocked until %s (use /ai @user unblock)",
                event.chat_id,
                time.strftime("%H:%M:%S", time.localtime(until)) if until else "?",
            )
            return

        text = (event.message.text or "").strip()
        if not text:
            if event.message.sticker:
                text = "[стикер]"
            else:
                return

        user_id = sender.id
        username = sender.username
        display_name = (sender.first_name or "") + (" " + sender.last_name if sender.last_name else "")
        display_name = display_name.strip() or None
        session = self._session(user_id)

        low = text.lower()
        if low in {"/start", "start"}:
            welcome = (
                "Привет! Поддержка Satka VPN 🤍\n\n"
                "Помогу с подключением, тарифами, Happ, оплатой, кабинетом, "
                "скоростью, устройствами, рефералкой и любым вопросом по сервису.\n"
                "Опишите проблему своими словами."
            )
            sent = await self._reply(event, welcome, session=session)
            session.history.append({"role": "user", "text": text})
            session.history.append({"role": "assistant", "text": sent})
            return

        if low in {"/help", "help"}:
            await self._reply(
                event,
                "Satka VPN — полная поддержка по сервису:\n"
                "подключение, тарифы, Happ, оплата, кабинет, скорость, устройства, рефералка.\n"
                "Бот: @satkavpn_bot · Кабинет: node.satkaconnect.xyz",
                session=session,
            )
            return

        if low in {"/reset", "reset"}:
            self.sessions.pop(user_id, None)
            self._blocked_chats_until.pop(event.chat_id, None)
            await self._reply(event, "Диалог сброшен. Можете описать вопрос заново.")
            return

        operator_requested = user_requests_operator(text)

        # 1) Готовые ответы и приветствия — до фильтров
        if text == "[стикер]":
            sent = await self._reply(event, STICKER_REPLY, session=session)
            session.history.append({"role": "user", "text": text})
            session.history.append({"role": "assistant", "text": sent})
            return

        canned = match_canned(text, already_greeted=session.greeted)
        if canned:
            sent = await self._reply(event, canned, session=session)
            session.history.append({"role": "user", "text": text})
            session.history.append({"role": "assistant", "text": sent})
            session.greeted = True
            return

        # 2) Оффтоп и провокации
        filter_kind, filter_reply = classify_message(text)
        if filter_kind in {"manipulation", "off_topic"} and filter_reply:
            logger.info("Filtered %s message from user %s", filter_kind, user_id)
            await self._reply(event, filter_reply, session=session)
            session.history.append({"role": "user", "text": text})
            session.history.append({"role": "assistant", "text": filter_reply})
            return

        if operator_requested:
            await self._reply(
                event,
                "Передаю оператору. Кратко опишите проблему и приложите скрин из Happ, "
                "если есть — скоро ответим.",
                session=session,
            )
            await self._maybe_escalate(
                session,
                user_id=user_id,
                username=username,
                display_name=display_name,
                reason="Пользователь запросил оператора",
                last_message=text,
                force=True,
            )
            return

        async with self.client.action(event.chat_id, "typing"):
            history = [{"role": t["role"], "text": t["text"]} for t in session.history]
            async with self._llm_sem:
                ai = await asyncio.to_thread(
                    self.ai.reply,
                    text,
                    history=history,
                    username=username,
                    user_id=user_id,
                    display_name=display_name,
                    has_history=bool(session.history),
                )

        if self._chat_is_blocked(event.chat_id):
            return

        reply = ai.text
        if not ai.api_error and session.unclear_streak >= 3 and not ai.escalate:
            reply += "\n\nЕсли не помогло — напишите «Оператор», подключим специалиста."
            ai.escalate = True

        if not ai.api_error and ai.confidence == "low":
            session.unclear_streak += 1
        elif not ai.api_error:
            session.unclear_streak = 0

        sent = await self._reply(event, reply, session=session)
        session.history.append({"role": "user", "text": text})
        session.history.append({"role": "assistant", "text": sent})
        session.greeted = True

        if ai.escalate and not ai.api_error:
            await self._maybe_escalate(
                session,
                user_id=user_id,
                username=username,
                display_name=display_name,
                reason=f"Эскалация AI (confidence={ai.confidence})",
                last_message=text,
                force=operator_requested,
            )

    async def _handle_message_safe(self, event: events.NewMessage.Event) -> None:
        chat_id = event.chat_id
        async with self._chat_locks[chat_id]:
            try:
                await self.handle_message(event)
            except Exception:
                logger.exception("Handler error for chat %s", chat_id)

    def _spawn_task(self, coro) -> None:
        task = asyncio.create_task(coro)
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)

    def register_handlers(self) -> None:
        @self.client.on(events.NewMessage(incoming=True))
        async def on_incoming(event: events.NewMessage.Event) -> None:
            self._spawn_task(self._handle_message_safe(event))

        @self.client.on(events.NewMessage(outgoing=True))
        async def on_outgoing(event: events.NewMessage.Event) -> None:
            try:
                await self.handle_outgoing(event)
            except Exception:
                logger.exception("Outgoing handler error for chat %s", event.chat_id)


async def run() -> None:
    settings = Settings.from_env()
    settings.validate()
    logging.getLogger().setLevel(settings.log_level)

    client = TelegramClient(settings.session_path, settings.telegram_api_id, settings.telegram_api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        logger.error("Session not authorized. Run: python auth_session.py")
        sys.exit(1)

    me = await client.get_me()
    bot = SupportUserbot(settings, client)
    bot._me_id = me.id
    bot._blocked_chats_until.clear()
    bot.register_handlers()

    await client(UpdateStatusRequest(offline=False))
    asyncio.create_task(bot._keep_online_loop())

    logger.info(
        "Support userbot v%s online as @%s (model=%s, concurrent=%s, keepalive=%ss)",
        BOT_VERSION,
        me.username,
        settings.llm_model,
        settings.max_concurrent_replies,
        settings.online_keepalive_sec,
    )
    await client.run_until_disconnected()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
