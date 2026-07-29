#!/usr/bin/env python3
"""Satka VPN — Telegram support bot powered by Gemini Flash."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from config import Settings
from gemini_client import GeminiSupportClient, user_requests_operator

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


class SupportBot:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.gemini = GeminiSupportClient(settings)
        self.alert_bot = Bot(token=settings.alert_bot_token)
        self.sessions: dict[int, UserSession] = defaultdict(UserSession)
        self._escalation_cooldown_sec = 300

    def _session(self, user_id: int) -> UserSession:
        return self.sessions[user_id]

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_chat or not update.message:
            return
        await update.message.reply_text(
            "Привет! Я ассистент **Satka VPN** 🤍\n\n"
            "Помогу с подключением Happ, подпиской, оплатой и кабинетом.\n"
            "Опишите проблему своими словами.\n\n"
            "Если нужен живой человек — напишите **Оператор**.",
            parse_mode=ParseMode.MARKDOWN,
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        await update.message.reply_text(
            "Я отвечаю по Satka VPN: Happ, подписка, оплата, кабинет.\n"
            "Бот: @satkavpn_bot · Кабинет: node.satkaconnect.xyz\n\n"
            "Живой оператор: напишите **Оператор**",
            parse_mode=ParseMode.MARKDOWN,
        )

    async def cmd_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if user:
            self.sessions.pop(user.id, None)
        if update.message:
            await update.message.reply_text("Диалог сброшен. Можете описать вопрос заново.")

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

        for i in range(self.settings.alert_repeat_count):
            try:
                await self.alert_bot.send_message(
                    chat_id=self.settings.admin_chat_id,
                    text=header if i == 0 else f"🔁 Повтор {i + 1}/{self.settings.alert_repeat_count}\n\n{header}",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                logger.exception("Failed admin alert %s/%s", i + 1, self.settings.alert_repeat_count)
            if i + 1 < self.settings.alert_repeat_count:
                await asyncio.sleep(self.settings.alert_repeat_delay_sec)

        try:
            await self.alert_bot.send_message(
                chat_id=self.settings.admin_chat_id,
                text=f"@{self.settings.admin_username} — нужен оператор в поддержке!",
            )
        except Exception:
            logger.debug("Admin username ping skipped")

    async def _maybe_escalate(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        session: UserSession,
        *,
        reason: str,
        force: bool = False,
    ) -> bool:
        user = update.effective_user
        if not user or not update.message:
            return False

        now = time.time()
        if not force and now - session.last_escalation_ts < self._escalation_cooldown_sec:
            return False

        session.last_escalation_ts = now
        await self._send_admin_alerts(
            user_id=user.id,
            username=user.username,
            display_name=user.full_name,
            reason=reason,
            last_message=update.message.text or "",
        )
        return True

    async def on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_user or not update.message or not update.message.text:
            return

        user = update.effective_user
        chat = update.effective_chat
        if not chat:
            return

        if self.settings.allowed_chat_ids and chat.id not in self.settings.allowed_chat_ids:
            await update.message.reply_text("Бот работает только в разрешённых чатах.")
            return

        text = update.message.text.strip()
        if not text:
            return

        session = self._session(user.id)
        operator_requested = user_requests_operator(text)

        if operator_requested:
            await update.message.reply_text(
                "Передаю в живую поддержку. Опишите проблему в 1–2 предложениях "
                "и приложите скрин из Happ, если есть — оператор скоро ответит в @satkavpnsupport.",
            )
            await self._maybe_escalate(
                update,
                context,
                session,
                reason="Пользователь запросил оператора",
                force=True,
            )
            return

        await context.bot.send_chat_action(chat_id=chat.id, action="typing")

        history = [{"role": t["role"], "text": t["text"]} for t in session.history]
        ai = self.gemini.reply(
            text,
            history=history,
            username=user.username,
            user_id=user.id,
            display_name=user.full_name,
        )

        session.history.append({"role": "user", "text": text})
        session.history.append({"role": "assistant", "text": ai.text})

        reply = ai.text
        if ai.confidence == "low" and not ai.escalate:
            reply += "\n\nЕсли всё ещё непонятно — напишите **Оператор**, подключим человека."
            session.unclear_streak += 1
        else:
            session.unclear_streak = 0

        if session.unclear_streak >= 2 and not ai.escalate:
            reply += "\n\nПохоже, сложный случай. Напишите **Оператор** — передам в поддержку."
            ai.escalate = True

        await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)

        if ai.escalate:
            await self._maybe_escalate(
                update,
                context,
                session,
                reason=f"Эскалация AI (confidence={ai.confidence})",
                force=operator_requested,
            )


def main() -> None:
    settings = Settings.from_env()
    settings.validate()
    logging.getLogger().setLevel(settings.log_level)

    bot = SupportBot(settings)
    app = Application.builder().token(settings.support_bot_token).build()

    app.add_handler(CommandHandler("start", bot.cmd_start))
    app.add_handler(CommandHandler("help", bot.cmd_help))
    app.add_handler(CommandHandler("reset", bot.cmd_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.on_message))

    logger.info(
        "Starting Satka Support AI (model=%s, admin=%s)",
        settings.gemini_model,
        settings.admin_chat_id,
    )
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
