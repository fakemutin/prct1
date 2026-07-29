#!/usr/bin/env python3
"""Satka VPN — support userbot (Telethon + DeepSeek)."""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

import httpx
from telethon import TelegramClient, events
from telethon.tl.types import User

from config import Settings
from llm_client import LlmSupportClient, user_requests_operator

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("satka-support-ai")


@dataclass
class UserSession:
    history: deque = field(default_factory=lambda: deque(maxlen=24))
    last_escalation_ts: float = 0.0
    unclear_streak: int = 0


class SupportUserbot:
    def __init__(self, settings: Settings, client: TelegramClient) -> None:
        self.settings = settings
        self.client = client
        self.ai = LlmSupportClient(settings)
        self.sessions: dict[int, UserSession] = defaultdict(UserSession)
        self._escalation_cooldown_sec = 300
        self._me_id: int | None = None
        self._ai_sent_ids: set[int] = set()
        self._human_chats_until: dict[int, float] = {}
        self._global_ai_paused_until: float = 0.0
        self._ai_enabled: bool = settings.ai_globally_enabled

    def _session(self, user_id: int) -> UserSession:
        return self.sessions[user_id]

    def _chat_is_human(self, chat_id: int) -> bool:
        if not self._ai_enabled:
            return True
        if time.time() < self._global_ai_paused_until:
            return True
        return self._human_chats_until.get(chat_id, 0) > time.time()

    def _mark_human_chat(self, chat_id: int) -> None:
        self._human_chats_until[chat_id] = time.time() + self.settings.human_takeover_sec
        if self.settings.global_pause_on_manual_sec > 0:
            self._global_ai_paused_until = time.time() + self.settings.global_pause_on_manual_sec
            logger.info(
                "Operator replied in chat %s — AI paused globally for %ss",
                chat_id,
                self.settings.global_pause_on_manual_sec,
            )
        else:
            logger.info("Operator replied in chat %s — AI paused for this chat", chat_id)

    def _track_ai_message(self, message_id: int) -> None:
        self._ai_sent_ids.add(message_id)
        if len(self._ai_sent_ids) > 500:
            self._ai_sent_ids = set(list(self._ai_sent_ids)[-300:])

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

    async def _reply(self, event: events.NewMessage.Event, text: str) -> None:
        sent = await event.respond(text, link_preview=False)
        if sent:
            self._track_ai_message(sent.id)

    async def handle_outgoing(self, event: events.NewMessage.Event) -> None:
        if not event.out or not event.is_private or not event.message:
            return

        text = (event.message.text or "").strip()
        low = text.lower()

        # Operator control commands (from support account, e.g. Saved Messages)
        if low == "/ai off":
            self._ai_enabled = False
            self._global_ai_paused_until = time.time() + 10 * 365 * 86400
            logger.info("AI disabled globally by operator")
            return
        if low == "/ai on":
            self._ai_enabled = True
            self._global_ai_paused_until = 0
            self._human_chats_until.clear()
            logger.info("AI enabled globally by operator")
            return
        if low == "/ai status":
            paused = not self._ai_enabled or time.time() < self._global_ai_paused_until
            await event.edit(
                f"AI: {'ВЫКЛ' if paused else 'ВКЛ'}\n"
                f"Чатов на паузе: {sum(1 for t in self._human_chats_until.values() if t > time.time())}"
            )
            return

        if event.message.id in self._ai_sent_ids:
            return

        if text:
            self._mark_human_chat(event.chat_id)

    async def handle_message(self, event: events.NewMessage.Event) -> None:
        if not event.is_private or not event.message or not event.message.text:
            return

        sender = await event.get_sender()
        if not isinstance(sender, User) or sender.bot or sender.id == self._me_id:
            return

        if self.settings.allowed_chat_ids and event.chat_id not in self.settings.allowed_chat_ids:
            return

        if self._chat_is_human(event.chat_id):
            logger.debug("Skipping AI for chat %s — operator mode", event.chat_id)
            return

        text = event.message.text.strip()
        if not text:
            return

        user_id = sender.id
        username = sender.username
        display_name = (sender.first_name or "") + (" " + sender.last_name if sender.last_name else "")
        display_name = display_name.strip() or None
        session = self._session(user_id)

        low = text.lower()
        if low in {"/start", "start"}:
            await self._reply(
                event,
                "Привет! Поддержка Satka VPN 🤍\n\n"
                "Помогу с Happ, подпиской, оплатой и кабинетом.\n"
                "Опишите проблему своими словами.\n\n"
                "Нужен живой человек — напишите «Оператор».",
            )
            return

        if low in {"/help", "help"}:
            await self._reply(
                event,
                "Satka VPN: Happ, подписка, оплата, кабинет.\n"
                "Бот: @satkavpn_bot · Кабинет: node.satkaconnect.xyz\n\n"
                "Живой оператор: напишите «Оператор»",
            )
            return

        if low in {"/reset", "reset"}:
            self.sessions.pop(user_id, None)
            self._human_chats_until.pop(event.chat_id, None)
            await self._reply(event, "Диалог сброшен. Можете описать вопрос заново.")
            return

        operator_requested = user_requests_operator(text)
        if operator_requested:
            await self._reply(
                event,
                "Передаю оператору. Кратко опишите проблему и приложите скрин из Happ, "
                "если есть — скоро ответим.",
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
            ai = await asyncio.to_thread(
                self.ai.reply,
                text,
                history=history,
                username=username,
                user_id=user_id,
                display_name=display_name,
            )

        if self._chat_is_human(event.chat_id):
            return

        session.history.append({"role": "user", "text": text})
        session.history.append({"role": "assistant", "text": ai.text})

        reply = ai.text
        if not ai.api_error:
            if ai.confidence == "low" and not ai.escalate:
                reply += "\n\nЕсли всё ещё непонятно — напишите «Оператор», подключим человека."
                session.unclear_streak += 1
            else:
                session.unclear_streak = 0

            if session.unclear_streak >= 2 and not ai.escalate:
                reply += "\n\nПохоже, сложный случай. Напишите «Оператор» — передам в поддержку."
                ai.escalate = True

        await self._reply(event, reply)

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

    def register_handlers(self) -> None:
        @self.client.on(events.NewMessage(incoming=True))
        async def on_incoming(event: events.NewMessage.Event) -> None:
            try:
                await self.handle_message(event)
            except Exception:
                logger.exception("Handler error for chat %s", event.chat_id)

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
    bot.register_handlers()

    logger.info(
        "Support userbot online as @%s (model=%s, admin=%s, human_pause=%ss, global_pause=%ss)",
        me.username,
        settings.llm_model,
        settings.admin_chat_id,
        settings.human_takeover_sec,
        settings.global_pause_on_manual_sec,
    )
    await client.run_until_disconnected()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
