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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = load_settings()
    settings.sessions_dir.mkdir(parents=True, exist_ok=True)
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)

    db = Database(settings.database_path)
    await db.connect()

    userbots = UserbotManager(settings, db)
    scheduler = AdScheduler(db, userbots, settings.default_interval_hours)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    admins = AdminState(settings.admin_ids)
    dp.include_router(setup_handlers(db, userbots, scheduler, admins))

    # Подключаем аккаунты и возобновляем рассылку, если была включена
    reports = await userbots.start_all()
    for line in reports:
        logger.info("Account start: %s", line)

    resume_msg = await scheduler.auto_resume()
    if resume_msg:
        logger.info("Auto-resume: %s", resume_msg)

    try:
        logger.info("Management bot started")
        await dp.start_polling(bot)
    finally:
        await scheduler.stop()
        await userbots.stop_all()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
