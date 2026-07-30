from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from config import Settings
from database import Chat, Database
from userbot import UserbotManager

logger = logging.getLogger(__name__)


class AdScheduler:
    def __init__(
        self,
        settings: Settings,
        db: Database,
        userbots: UserbotManager,
    ) -> None:
        self.settings = settings
        self.db = db
        self.userbots = userbots
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._running = False
        self._last_results: list[str] = []

    @property
    def running(self) -> bool:
        return self._running

    @property
    def last_results(self) -> list[str]:
        return list(self._last_results[-30:])

    async def start(self) -> tuple[bool, str]:
        if self._running:
            return True, "Планировщик уже работает"

        enabled = await self.db.count_enabled_chats()
        if enabled == 0:
            return False, "Нет активных чатов. Дождитесь синхронизации или добавьте чаты."

        if not await self.db.has_ad_message():
            return False, "Сначала задайте рекламное сообщение (📨 Сообщение)."

        await self.userbots.start_all(auto_sync=False)
        self._stop_event.clear()
        self._running = True
        await self.db.set_scheduler_running(True)
        self._task = asyncio.create_task(self._loop(), name="ad-scheduler")
        return True, f"Запущен. Активных чатов: {enabled}, интервал: {int(self.settings.default_interval_minutes)} мин"

    async def stop(self) -> str:
        if not self._running:
            await self.db.set_scheduler_running(False)
            return "Планировщик уже остановлен"

        self._running = False
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self.db.set_scheduler_running(False)
        return "Планировщик остановлен"

    async def auto_resume(self) -> str | None:
        if await self.db.is_scheduler_running():
            ok, msg = await self.start()
            return msg if ok else f"Автовозобновление не удалось: {msg}"

        if self.settings.auto_start_scheduler:
            if await self.db.count_enabled_chats() > 0 and await self.db.has_ad_message():
                ok, msg = await self.start()
                return f"Автостарт: {msg}" if ok else f"Автостарт не удался: {msg}"
        return None

    async def post_now(self, chat_row_id: int) -> tuple[bool, str]:
        chat = await self.db.get_chat(chat_row_id)
        if not chat:
            return False, "Чат не найден"
        return await self._post_to_chat(chat, force=True)

    async def _loop(self) -> None:
        logger.info("Scheduler loop started (tick=%ss)", self.settings.scheduler_tick_seconds)
        while self._running and not self._stop_event.is_set():
            try:
                await self._tick()
            except Exception:
                logger.exception("Scheduler tick failed")
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.settings.scheduler_tick_seconds,
                )
            except asyncio.TimeoutError:
                continue
        logger.info("Scheduler loop stopped")

    async def _tick(self) -> None:
        chats = await self.db.get_chats(only_enabled=True)
        if not chats:
            return

        now = datetime.utcnow()
        due = [c for c in chats if self._is_due(c, now)]
        if not due:
            return

        for chat in due:
            if not self._running:
                break
            ok, msg = await self._post_to_chat(chat)
            stamp = datetime.utcnow().strftime("%H:%M:%S")
            line = f"[{stamp}] {chat.title}: {'✅' if ok else '❌'} {msg}"
            self._last_results.append(line)
            await self.db.log_post(chat.id, ok, msg)
            logger.info(line)
            await asyncio.sleep(self.settings.post_delay_seconds)

    def _is_due(self, chat: Chat, now: datetime) -> bool:
        if not chat.last_posted_at:
            return True
        try:
            last = datetime.fromisoformat(chat.last_posted_at)
        except ValueError:
            return True
        return now - last >= timedelta(minutes=chat.interval_minutes)

    async def _post_to_chat(self, chat: Chat, force: bool = False) -> tuple[bool, str]:
        if not force:
            now = datetime.utcnow()
            if not self._is_due(chat, now):
                return False, "Ещё не время"

        ad = await self.db.get_ad_message(chat.account_id)
        if not ad:
            return False, "Нет рекламного сообщения"

        ok, msg = await self.userbots.send_ad(
            account_id=chat.account_id,
            target_chat_id=chat.chat_id,
            from_chat_id=ad.from_chat_id,
            message_id=ad.message_id,
        )
        if ok:
            await self.db.update_last_posted(chat.id)
        return ok, msg
