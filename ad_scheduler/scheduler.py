from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from database import Chat, Database
from userbot import UserbotManager

logger = logging.getLogger(__name__)


class AdScheduler:
    def __init__(
        self,
        db: Database,
        userbots: UserbotManager,
        default_interval_hours: float = 1.0,
    ) -> None:
        self.db = db
        self.userbots = userbots
        self.default_interval_hours = default_interval_hours
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._running = False
        self._last_results: list[str] = []

    @property
    def running(self) -> bool:
        return self._running

    @property
    def last_results(self) -> list[str]:
        return list(self._last_results[-20:])

    async def start(self) -> tuple[bool, str]:
        if self._running:
            return True, "Планировщик уже работает"

        enabled = await self.db.count_enabled_chats()
        if enabled == 0:
            return False, "Нет активных чатов для рассылки"

        await self.userbots.start_all()
        self._stop_event.clear()
        self._running = True
        await self.db.set_scheduler_running(True)
        self._task = asyncio.create_task(self._loop(), name="ad-scheduler")
        return True, f"Запущен. Активных чатов: {enabled}"

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
        if not await self.db.is_scheduler_running():
            return None
        ok, msg = await self.start()
        return msg if ok else f"Автозапуск не удался: {msg}"

    async def post_now(self, chat_row_id: int) -> tuple[bool, str]:
        chat = await self.db.get_chat(chat_row_id)
        if not chat:
            return False, "Чат не найден"
        return await self._post_to_chat(chat, force=True)

    async def _loop(self) -> None:
        logger.info("Scheduler loop started")
        while self._running and not self._stop_event.is_set():
            try:
                await self._tick()
            except Exception:
                logger.exception("Scheduler tick failed")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=30)
            except asyncio.TimeoutError:
                continue
        logger.info("Scheduler loop stopped")

    async def _tick(self) -> None:
        chats = await self.db.get_chats(only_enabled=True)
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
            logger.info(line)
            await asyncio.sleep(3)

    def _is_due(self, chat: Chat, now: datetime) -> bool:
        if not chat.last_posted_at:
            return True
        try:
            last = datetime.fromisoformat(chat.last_posted_at)
        except ValueError:
            return True
        return now - last >= timedelta(hours=chat.interval_hours)

    async def _post_to_chat(self, chat: Chat, force: bool = False) -> tuple[bool, str]:
        if not force:
            now = datetime.utcnow()
            if not self._is_due(chat, now):
                return False, "Ещё не время"

        ad = await self.db.get_ad_message(chat.account_id)
        if not ad:
            return False, "Нет рекламного сообщения"

        ok, msg = await self.userbots.forward_ad(
            account_id=chat.account_id,
            target_chat_id=chat.chat_id,
            from_chat_id=ad.from_chat_id,
            message_id=ad.message_id,
        )
        if ok:
            await self.db.update_last_posted(chat.id)
        return ok, msg
