from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from pyrogram import Client
from pyrogram.enums import ChatType
from pyrogram.errors import (
    ChatWriteForbidden,
    FloodWait,
    PeerIdInvalid,
    RPCError,
    SessionPasswordNeeded,
    UserAlreadyParticipant,
)
from pyrogram.types import Chat as TgChat

from config import Settings
from database import Account, Database

logger = logging.getLogger(__name__)

GROUP_TYPES = {ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL}


class UserbotManager:
    def __init__(self, settings: Settings, db: Database) -> None:
        self.settings = settings
        self.db = db
        self.proxy = settings.proxy
        self._clients: dict[int, Client] = {}
        self._auth_pending: dict[int, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    def _session_path(self, session_name: str) -> str:
        self.settings.sessions_dir.mkdir(parents=True, exist_ok=True)
        return str(self.settings.sessions_dir / session_name)

    def _build_client(self, account: Account) -> Client:
        return Client(
            name=self._session_path(account.session_name),
            api_id=account.api_id,
            api_hash=account.api_hash,
            phone_number=account.phone,
            proxy=self.proxy.to_pyrogram(),
            workdir=str(self.settings.sessions_dir),
            in_memory=False,
        )

    async def start_all(self, *, auto_sync: bool | None = None) -> list[str]:
        reports: list[str] = []
        accounts = await self.db.get_accounts(only_enabled=True)
        do_sync = (
            self.settings.auto_sync_on_start if auto_sync is None else auto_sync
        )
        for account in accounts:
            ok, msg = await self.start_account(account.id)
            reports.append(f"{account.name}: {msg}")
            if ok and do_sync:
                added, updated, sync_msg = await self.sync_dialogs(
                    account.id, enable_all=True
                )
                reports.append(f"  ↳ {sync_msg}")
        return reports

    async def stop_all(self) -> None:
        for account_id in list(self._clients.keys()):
            await self.stop_account(account_id)

    async def start_account(self, account_id: int) -> tuple[bool, str]:
        async with self._lock:
            account = await self.db.get_account(account_id)
            if not account:
                return False, "Аккаунт не найден"
            if account_id in self._clients:
                client = self._clients[account_id]
                if client.is_connected:
                    return True, "Уже запущен"

            client = self._build_client(account)
            try:
                await client.start()
                me = await client.get_me()
                self._clients[account_id] = client
                label = f"@{me.username}" if me.username else str(me.id)
                return True, f"{label} подключён"
            except Exception as exc:
                logger.exception("Failed to start account %s", account_id)
                try:
                    await client.stop()
                except Exception:
                    pass
                return False, str(exc)

    async def stop_account(self, account_id: int) -> None:
        client = self._clients.pop(account_id, None)
        if client:
            try:
                await client.stop()
            except Exception:
                logger.exception("Error stopping account %s", account_id)

    def get_client(self, account_id: int) -> Client | None:
        return self._clients.get(account_id)

    async def is_connected(self, account_id: int) -> bool:
        client = self._clients.get(account_id)
        return bool(client and client.is_connected)

    async def ensure_client(self, account_id: int) -> tuple[Client | None, str]:
        client = self._clients.get(account_id)
        if client and client.is_connected:
            return client, "OK"
        ok, msg = await self.start_account(account_id)
        if not ok:
            return None, msg
        return self._clients.get(account_id), "OK"

    # --- Auth ---

    async def begin_auth(
        self,
        admin_id: int,
        name: str,
        phone: str,
        api_id: int,
        api_hash: str,
    ) -> tuple[bool, str]:
        phone = self._normalize_phone(phone)
        existing = await self.db.get_account_by_phone(phone)
        if existing:
            return False, "Аккаунт с этим номером уже есть"

        session_name = f"acc_{phone.replace('+', '')}"
        temp_account = Account(
            id=0,
            name=name,
            phone=phone,
            api_id=api_id,
            api_hash=api_hash,
            session_name=session_name,
            enabled=True,
            created_at="",
        )
        client = self._build_client(temp_account)
        await client.connect()
        try:
            sent = await client.send_code(phone)
        except Exception as exc:
            await client.disconnect()
            return False, f"Не удалось отправить код: {exc}"

        self._auth_pending[admin_id] = {
            "name": name,
            "phone": phone,
            "api_id": api_id,
            "api_hash": api_hash,
            "session_name": session_name,
            "client": client,
            "phone_code_hash": sent.phone_code_hash,
            "step": "code",
        }
        return True, f"Код отправлен на {phone}. Отправьте его боту."

    async def submit_code(self, admin_id: int, code: str) -> tuple[bool, str]:
        pending = self._auth_pending.get(admin_id)
        if not pending or pending.get("step") != "code":
            return False, "Нет активной авторизации. Начните заново."

        client: Client = pending["client"]
        code = re.sub(r"\s+", "", code.strip())
        try:
            await client.sign_in(
                pending["phone"],
                pending["phone_code_hash"],
                code,
            )
        except SessionPasswordNeeded:
            pending["step"] = "password"
            return False, "Нужен пароль 2FA. Отправьте пароль боту."
        except Exception as exc:
            return False, f"Ошибка кода: {exc}"

        return await self._finalize_auth(admin_id)

    async def submit_password(self, admin_id: int, password: str) -> tuple[bool, str]:
        pending = self._auth_pending.get(admin_id)
        if not pending or pending.get("step") != "password":
            return False, "2FA не ожидается."

        client: Client = pending["client"]
        try:
            await client.check_password(password)
        except Exception as exc:
            return False, f"Неверный пароль: {exc}"

        return await self._finalize_auth(admin_id)

    async def cancel_auth(self, admin_id: int) -> None:
        pending = self._auth_pending.pop(admin_id, None)
        if pending:
            client: Client = pending["client"]
            try:
                await client.disconnect()
            except Exception:
                pass

    async def _finalize_auth(self, admin_id: int) -> tuple[bool, str]:
        pending = self._auth_pending.pop(admin_id, None)
        if not pending:
            return False, "Сессия авторизации потеряна"

        client: Client = pending["client"]
        try:
            me = await client.get_me()
            account_id = await self.db.add_account(
                name=pending["name"],
                phone=pending["phone"],
                api_id=pending["api_id"],
                api_hash=pending["api_hash"],
                session_name=pending["session_name"],
            )
            await client.disconnect()

            ok, msg = await self.start_account(account_id)
            sync_msg = ""
            if ok:
                _, _, sync_msg = await self.sync_dialogs(account_id, enable_all=True)
            username = f"@{me.username}" if me.username else str(me.id)
            return ok, f"Аккаунт {username} добавлен. {msg}\n{sync_msg}"
        except Exception as exc:
            try:
                await client.disconnect()
            except Exception:
                pass
            return False, f"Ошибка сохранения: {exc}"

    # --- Chats ---

    async def sync_dialogs(
        self,
        account_id: int,
        *,
        enable_all: bool = True,
    ) -> tuple[int, int, str]:
        client, err = await self.ensure_client(account_id)
        if not client:
            return 0, 0, err

        added = 0
        updated = 0
        async for dialog in client.get_dialogs():
            chat = dialog.chat
            if chat.type not in GROUP_TYPES:
                continue
            title, username, chat_type = self._chat_meta(chat)
            existing = await self._chat_exists(account_id, chat.id)
            await self.db.upsert_chat(
                account_id=account_id,
                chat_id=chat.id,
                title=title,
                username=username,
                chat_type=chat_type,
                enabled=True if enable_all else (None if existing else True),
                interval_minutes=self.settings.default_interval_minutes,
            )
            if existing:
                updated += 1
            else:
                added += 1

        return added, updated, f"Синхронизация: +{added} новых, {updated} обновлено"

    async def _chat_exists(self, account_id: int, chat_id: int) -> bool:
        chats = await self.db.get_chats(account_id=account_id)
        return any(c.chat_id == chat_id for c in chats)

    async def resolve_chat(
        self, account_id: int, ref: str
    ) -> tuple[bool, str, int | None]:
        client, err = await self.ensure_client(account_id)
        if not client:
            return False, err, None

        ref = ref.strip()
        if ref.lstrip("-").isdigit():
            target: str | int = int(ref)
        else:
            target = ref if ref.startswith("@") else f"@{ref}"

        try:
            chat = await client.get_chat(target)
        except Exception as exc:
            return False, f"Чат не найден: {exc}", None

        title, username, chat_type = self._chat_meta(chat)
        row_id = await self.db.upsert_chat(
            account_id=account_id,
            chat_id=chat.id,
            title=title,
            username=username,
            chat_type=chat_type,
            enabled=True,
            interval_minutes=self.settings.default_interval_minutes,
        )
        return True, f"Добавлен: {title}", row_id

    async def join_chat(self, account_id: int, invite_link: str) -> tuple[bool, str]:
        client, err = await self.ensure_client(account_id)
        if not client:
            return False, err

        try:
            chat = await client.join_chat(invite_link)
        except UserAlreadyParticipant:
            try:
                chat = await client.get_chat(invite_link)
            except Exception as exc:
                return False, f"Уже в чате, но не удалось получить инфо: {exc}"
        except Exception as exc:
            return False, f"Не удалось вступить: {exc}"

        title, username, chat_type = self._chat_meta(chat)
        await self.db.upsert_chat(
            account_id=account_id,
            chat_id=chat.id,
            title=title,
            username=username,
            chat_type=chat_type,
            enabled=True,
            interval_minutes=self.settings.default_interval_minutes,
        )
        return True, f"Вступили в {title}"

    async def send_ad(
        self,
        account_id: int,
        target_chat_id: int,
        from_chat_id: int,
        message_id: int,
        *,
        _allow_flood_retry: bool = True,
    ) -> tuple[bool, str]:
        client, err = await self.ensure_client(account_id)
        if not client:
            return False, err

        try:
            await client.forward_messages(
                chat_id=target_chat_id,
                from_chat_id=from_chat_id,
                message_ids=message_id,
            )
            return True, "Переслано"
        except FloodWait as exc:
            wait = int(exc.value) + 1
            logger.warning("FloodWait %ss for chat %s", wait, target_chat_id)
            if not _allow_flood_retry:
                return False, f"FloodWait {wait}с"
            await asyncio.sleep(wait)
            return await self.send_ad(
                account_id,
                target_chat_id,
                from_chat_id,
                message_id,
                _allow_flood_retry=False,
            )
        except (ChatWriteForbidden, PeerIdInvalid) as exc:
            return False, str(exc)
        except RPCError:
            try:
                await client.copy_message(
                    chat_id=target_chat_id,
                    from_chat_id=from_chat_id,
                    message_id=message_id,
                )
                return True, "Скопировано"
            except Exception as copy_exc:
                return False, str(copy_exc)
        except Exception as exc:
            try:
                await client.copy_message(
                    chat_id=target_chat_id,
                    from_chat_id=from_chat_id,
                    message_id=message_id,
                )
                return True, "Скопировано (fallback)"
            except Exception:
                return False, str(exc)

    def _chat_meta(self, chat: TgChat) -> tuple[str, str | None, str]:
        title = chat.title or chat.first_name or str(chat.id)
        username = chat.username
        chat_type = str(chat.type.value) if hasattr(chat.type, "value") else str(chat.type)
        return title, username, chat_type

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        phone = phone.strip().replace(" ", "").replace("-", "")
        if not phone.startswith("+"):
            phone = f"+{phone}"
        return phone
