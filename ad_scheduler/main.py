from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import AdminState, setup_handlers
from config import load_settings
from database import Database
from scheduler import AdScheduler
from userbot import UserbotManager
from utils import format_interval

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def notify_admins(bot: Bot, admin_ids: list[int], text: str) -> None:
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, text, parse_mode=ParseMode.HTML)
        except Exception:
            logger.exception("Failed to notify admin %s", admin_id)


async def main() -> None:
    settings = load_settings()
    settings.sessions_dir.mkdir(parents=True, exist_ok=True)
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)

    db = Database(settings.database_path, settings.default_interval_minutes)
    await db.connect()

    userbots = UserbotManager(settings, db)
    scheduler = AdScheduler(settings, db, userbots)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    admins = AdminState(settings.admin_ids)
    dp.include_router(setup_handlers(settings, db, userbots, scheduler, admins))

    startup_lines = [
        "🚀 <b>Планировщик запущен</b>",
        f"Интервал: {format_interval(settings.default_interval_minutes)}",
        f"Прокси: {'✅ ' + settings.proxy.host if settings.proxy.enabled else '❌ не задан'}",
    ]

    logger.info("Starting userbot accounts...")
    reports = await userbots.start_all(auto_sync=settings.auto_sync_on_start)
    for line in reports:
        logger.info("  %s", line)
        startup_lines.append(f"• {line}")

    resume_msg = await scheduler.auto_resume()
    if resume_msg:
        logger.info("Scheduler: %s", resume_msg)
        startup_lines.append(f"• {resume_msg}")

    chat_count = await db.count_enabled_chats()
    startup_lines.append(f"\nАктивных чатов: <b>{chat_count}</b>")
    if not await db.has_ad_message():
        startup_lines.append("⚠️ Задайте рекламное сообщение: 📨 Сообщение")

    await notify_admins(bot, settings.admin_ids, "\n".join(startup_lines))

    try:
        logger.info("Management bot polling started")
        await dp.start_polling(bot)
    finally:
        await scheduler.stop()
        await userbots.stop_all()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
