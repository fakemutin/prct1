from __future__ import annotations

import logging
from typing import Any

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.keyboards import (
    account_detail_kb,
    accounts_kb,
    add_chat_accounts_kb,
    cancel_kb,
    chat_detail_kb,
    chats_kb,
    main_menu_kb,
    sync_accounts_kb,
)
from database import Database
from scheduler import AdScheduler
from userbot import UserbotManager

logger = logging.getLogger(__name__)

router = Router()


class AddAccount(StatesGroup):
    name = State()
    phone = State()
    api_id = State()
    api_hash = State()
    code = State()
    password = State()


class AddChat(StatesGroup):
    account_id = State()
    chat_ref = State()
    invite_link = State()


class SetMessage(StatesGroup):
    waiting = State()


class AdminState:
    def __init__(self, admin_ids: list[int]) -> None:
        self.admin_ids = set(admin_ids)

    def check(self, user_id: int) -> bool:
        return user_id in self.admin_ids


def setup_handlers(
    db: Database,
    userbots: UserbotManager,
    scheduler: AdScheduler,
    admins: AdminState,
) -> Router:
    ctx = {"db": db, "userbots": userbots, "scheduler": scheduler, "admins": admins}

    @router.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        if not ctx["admins"].check(message.from_user.id):
            await message.answer("⛔ Доступ запрещён")
            return
        await message.answer(
            "📢 <b>Планировщик рекламы</b>\n\n"
            "Постинг только в чаты, где реклама разрешена.\n"
            "Используйте меню для управления.",
            parse_mode="HTML",
            reply_markup=main_menu_kb(),
        )

    @router.message(Command("help"))
    @router.message(F.text == "❓ Помощь")
    async def cmd_help(message: Message) -> None:
        if not ctx["admins"].check(message.from_user.id):
            return
        await message.answer(
            "<b>Как пользоваться</b>\n\n"
            "1. <b>Аккаунты</b> — добавьте Telegram-аккаунт (api_id/api_hash с my.telegram.org)\n"
            "2. <b>Синхронизация</b> — подтянуть чаты, в которых уже состоите\n"
            "3. <b>Добавить чат</b> — @username, ID или invite-ссылка\n"
            "4. <b>Сообщение</b> — перешлите боту рекламный пост\n"
            "5. <b>Старт</b> — запуск рассылки раз в N часов\n\n"
            "Прокси SOCKS5 настраивается в .env\n"
            "При перезапуске рассылка возобновится, если была включена.",
            parse_mode="HTML",
        )

    @router.message(F.text == "📊 Статус")
    async def status_btn(message: Message) -> None:
        if not ctx["admins"].check(message.from_user.id):
            return
        db: Database = ctx["db"]
        scheduler: AdScheduler = ctx["scheduler"]
        accounts = await db.get_accounts()
        chats = await db.get_chats()
        enabled_chats = [c for c in chats if c.enabled]
        ad = await db.list_ad_messages()

        lines = [
            f"Планировщик: {'🟢 работает' if scheduler.running else '🔴 остановлен'}",
            f"Аккаунтов: {len(accounts)} (активных: {sum(1 for a in accounts if a.enabled)})",
            f"Чатов: {len(chats)} (активных: {len(enabled_chats)})",
            f"Сообщений: {len(ad)}",
            "",
            "<b>Последние действия:</b>",
        ]
        results = scheduler.last_results
        if results:
            lines.extend(f"• {r}" for r in results[-8:])
        else:
            lines.append("• пока пусто")

        await message.answer("\n".join(lines), parse_mode="HTML")

    @router.message(F.text == "▶️ Старт")
    async def start_btn(message: Message) -> None:
        if not ctx["admins"].check(message.from_user.id):
            return
        ok, msg = await ctx["scheduler"].start()
        await message.answer(("✅ " if ok else "❌ ") + msg)

    @router.message(F.text == "⏹ Стоп")
    async def stop_btn(message: Message) -> None:
        if not ctx["admins"].check(message.from_user.id):
            return
        msg = await ctx["scheduler"].stop()
        await message.answer("✅ " + msg)

    # --- Accounts ---

    @router.message(F.text == "👤 Аккаунты")
    async def accounts_btn(message: Message) -> None:
        if not ctx["admins"].check(message.from_user.id):
            return
        accounts = await ctx["db"].get_accounts()
        if not accounts:
            await message.answer(
                "Аккаунтов нет. Нажмите «➕ Добавить аккаунт».",
                reply_markup=accounts_kb([]),
            )
            return
        await message.answer("👤 Аккаунты:", reply_markup=accounts_kb(accounts))

    @router.callback_query(F.data == "acc:list")
    async def accounts_list_cb(call: CallbackQuery) -> None:
        if not ctx["admins"].check(call.from_user.id):
            return
        accounts = await ctx["db"].get_accounts()
        await call.message.edit_text("👤 Аккаунты:", reply_markup=accounts_kb(accounts))
        await call.answer()

    @router.callback_query(F.data == "acc:add")
    async def account_add_cb(call: CallbackQuery, state: FSMContext) -> None:
        if not ctx["admins"].check(call.from_user.id):
            return
        await state.set_state(AddAccount.name)
        await call.message.answer(
            "Введите имя аккаунта (для удобства, например «Основной»):",
            reply_markup=cancel_kb(),
        )
        await call.answer()

    @router.message(AddAccount.name)
    async def account_name(message: Message, state: FSMContext) -> None:
        if message.text == "❌ Отмена":
            await _cancel(message, state)
            return
        await state.update_data(name=message.text.strip())
        await state.set_state(AddAccount.phone)
        await message.answer("Введите номер телефона (+79...):", reply_markup=cancel_kb())

    @router.message(AddAccount.phone)
    async def account_phone(message: Message, state: FSMContext) -> None:
        if message.text == "❌ Отмена":
            await _cancel(message, state)
            return
        await state.update_data(phone=message.text.strip())
        await state.set_state(AddAccount.api_id)
        await message.answer(
            "Введите api_id (с https://my.telegram.org):",
            reply_markup=cancel_kb(),
        )

    @router.message(AddAccount.api_id)
    async def account_api_id(message: Message, state: FSMContext) -> None:
        if message.text == "❌ Отмена":
            await _cancel(message, state)
            return
        if not message.text.strip().isdigit():
            await message.answer("api_id должен быть числом")
            return
        await state.update_data(api_id=int(message.text.strip()))
        await state.set_state(AddAccount.api_hash)
        await message.answer("Введите api_hash:", reply_markup=cancel_kb())

    @router.message(AddAccount.api_hash)
    async def account_api_hash(message: Message, state: FSMContext) -> None:
        if message.text == "❌ Отмена":
            await _cancel(message, state)
            return
        data = await state.get_data()
        ok, msg = await ctx["userbots"].begin_auth(
            admin_id=message.from_user.id,
            name=data["name"],
            phone=data["phone"],
            api_id=data["api_id"],
            api_hash=message.text.strip(),
        )
        if not ok:
            await state.clear()
            await message.answer("❌ " + msg, reply_markup=main_menu_kb())
            return
        await state.set_state(AddAccount.code)
        await message.answer("✅ " + msg, reply_markup=cancel_kb())

    @router.message(AddAccount.code)
    async def account_code(message: Message, state: FSMContext) -> None:
        if message.text == "❌ Отмена":
            await ctx["userbots"].cancel_auth(message.from_user.id)
            await _cancel(message, state)
            return
        ok, msg = await ctx["userbots"].submit_code(message.from_user.id, message.text)
        if msg.startswith("Нужен пароль"):
            await state.set_state(AddAccount.password)
            await message.answer(msg, reply_markup=cancel_kb())
            return
        await state.clear()
        await message.answer(("✅ " if ok else "❌ ") + msg, reply_markup=main_menu_kb())

    @router.message(AddAccount.password)
    async def account_password(message: Message, state: FSMContext) -> None:
        if message.text == "❌ Отмена":
            await ctx["userbots"].cancel_auth(message.from_user.id)
            await _cancel(message, state)
            return
        ok, msg = await ctx["userbots"].submit_password(message.from_user.id, message.text)
        await state.clear()
        await message.answer(("✅ " if ok else "❌ ") + msg, reply_markup=main_menu_kb())

    @router.callback_query(F.data.startswith("acc:"))
    async def account_detail_cb(call: CallbackQuery) -> None:
        if not ctx["admins"].check(call.from_user.id):
            return
        part = call.data.split(":", 1)[1]
        if part == "add":
            return
        account = await ctx["db"].get_account(int(part))
        if not account:
            await call.answer("Не найден", show_alert=True)
            return
        connected = await ctx["userbots"].is_connected(account.id)
        text = (
            f"<b>{account.name}</b>\n"
            f"Телефон: {account.phone}\n"
            f"Статус: {'🟢 онлайн' if connected else '🔴 офлайн'}\n"
            f"Включён: {'да' if account.enabled else 'нет'}"
        )
        await call.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=account_detail_kb(account.id, account.enabled),
        )
        await call.answer()

    @router.callback_query(F.data.startswith("acc_toggle:"))
    async def account_toggle_cb(call: CallbackQuery) -> None:
        if not ctx["admins"].check(call.from_user.id):
            return
        account_id = int(call.data.split(":")[1])
        account = await ctx["db"].get_account(account_id)
        if not account:
            await call.answer("Не найден", show_alert=True)
            return
        new_state = not account.enabled
        await ctx["db"].toggle_account(account_id, new_state)
        if new_state:
            await ctx["userbots"].start_account(account_id)
        else:
            await ctx["userbots"].stop_account(account_id)
        account = await ctx["db"].get_account(account_id)
        connected = await ctx["userbots"].is_connected(account_id)
        text = (
            f"<b>{account.name}</b>\n"
            f"Телефон: {account.phone}\n"
            f"Статус: {'🟢 онлайн' if connected else '🔴 офлайн'}\n"
            f"Включён: {'да' if account.enabled else 'нет'}"
        )
        await call.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=account_detail_kb(account.id, account.enabled),
        )
        await call.answer("Обновлено")

    @router.callback_query(F.data.startswith("acc_del:"))
    async def account_del_cb(call: CallbackQuery) -> None:
        if not ctx["admins"].check(call.from_user.id):
            return
        account_id = int(call.data.split(":")[1])
        await ctx["userbots"].stop_account(account_id)
        await ctx["db"].delete_account(account_id)
        accounts = await ctx["db"].get_accounts()
        await call.message.edit_text("👤 Аккаунты:", reply_markup=accounts_kb(accounts))
        await call.answer("Удалён")

    # --- Chats ---

    @router.message(F.text == "📋 Чаты")
    async def chats_btn(message: Message) -> None:
        if not ctx["admins"].check(message.from_user.id):
            return
        chats = await ctx["db"].get_chats()
        if not chats:
            await message.answer("Чатов нет. Синхронизируйте или добавьте вручную.")
            return
        await message.answer(
            f"📋 Чаты ({len(chats)}):",
            reply_markup=chats_kb(chats, page=0),
        )

    @router.callback_query(F.data == "chats:list")
    async def chats_list_cb(call: CallbackQuery) -> None:
        if not ctx["admins"].check(call.from_user.id):
            return
        chats = await ctx["db"].get_chats()
        await call.message.edit_text(
            f"📋 Чаты ({len(chats)}):",
            reply_markup=chats_kb(chats, page=0),
        )
        await call.answer()

    @router.callback_query(F.data.startswith("chats_page:"))
    async def chats_page_cb(call: CallbackQuery) -> None:
        if not ctx["admins"].check(call.from_user.id):
            return
        page = int(call.data.split(":")[1])
        chats = await ctx["db"].get_chats()
        await call.message.edit_text(
            f"📋 Чаты ({len(chats)}):",
            reply_markup=chats_kb(chats, page=page),
        )
        await call.answer()

    @router.callback_query(F.data.startswith("chat:"))
    async def chat_detail_cb(call: CallbackQuery) -> None:
        if not ctx["admins"].check(call.from_user.id):
            return
        chat_id = int(call.data.split(":")[1])
        chat = await ctx["db"].get_chat(chat_id)
        if not chat:
            await call.answer("Не найден", show_alert=True)
            return
        uname = f"@{chat.username}" if chat.username else "—"
        last = chat.last_posted_at or "никогда"
        text = (
            f"<b>{chat.title}</b>\n"
            f"ID: <code>{chat.chat_id}</code>\n"
            f"Username: {uname}\n"
            f"Тип: {chat.chat_type}\n"
            f"Интервал: {chat.interval_hours} ч\n"
            f"Последний пост: {last}\n"
            f"Статус: {'🟢 активен' if chat.enabled else '🔴 выкл'}"
        )
        await call.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=chat_detail_kb(chat.id, chat.enabled),
        )
        await call.answer()

    @router.callback_query(F.data.startswith("chat_toggle:"))
    async def chat_toggle_cb(call: CallbackQuery) -> None:
        if not ctx["admins"].check(call.from_user.id):
            return
        row_id = int(call.data.split(":")[1])
        chat = await ctx["db"].get_chat(row_id)
        if not chat:
            await call.answer("Не найден", show_alert=True)
            return
        await ctx["db"].toggle_chat(row_id, not chat.enabled)
        chat = await ctx["db"].get_chat(row_id)
        uname = f"@{chat.username}" if chat.username else "—"
        last = chat.last_posted_at or "никогда"
        text = (
            f"<b>{chat.title}</b>\n"
            f"ID: <code>{chat.chat_id}</code>\n"
            f"Username: {uname}\n"
            f"Тип: {chat.chat_type}\n"
            f"Интервал: {chat.interval_hours} ч\n"
            f"Последний пост: {last}\n"
            f"Статус: {'🟢 активен' if chat.enabled else '🔴 выкл'}"
        )
        await call.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=chat_detail_kb(chat.id, chat.enabled),
        )
        await call.answer("Обновлено")

    @router.callback_query(F.data.startswith("chat_int:"))
    async def chat_interval_cb(call: CallbackQuery) -> None:
        if not ctx["admins"].check(call.from_user.id):
            return
        _, row_id, hours = call.data.split(":")
        await ctx["db"].set_chat_interval(int(row_id), float(hours))
        await call.answer(f"Интервал: {hours} ч")

    @router.callback_query(F.data.startswith("chat_post:"))
    async def chat_post_cb(call: CallbackQuery) -> None:
        if not ctx["admins"].check(call.from_user.id):
            return
        row_id = int(call.data.split(":")[1])
        ok, msg = await ctx["scheduler"].post_now(row_id)
        await call.answer(("✅ " if ok else "❌ ") + msg, show_alert=not ok)

    @router.callback_query(F.data.startswith("chat_del:"))
    async def chat_del_cb(call: CallbackQuery) -> None:
        if not ctx["admins"].check(call.from_user.id):
            return
        row_id = int(call.data.split(":")[1])
        await ctx["db"].delete_chat(row_id)
        chats = await ctx["db"].get_chats()
        await call.message.edit_text(
            f"📋 Чаты ({len(chats)}):",
            reply_markup=chats_kb(chats, page=0),
        )
        await call.answer("Удалён")

    # --- Sync ---

    @router.message(F.text == "🔄 Синхронизация")
    async def sync_btn(message: Message) -> None:
        if not ctx["admins"].check(message.from_user.id):
            return
        accounts = await ctx["db"].get_accounts(only_enabled=True)
        if not accounts:
            await message.answer("Сначала добавьте аккаунт.")
            return
        await message.answer("Выберите аккаунт:", reply_markup=sync_accounts_kb(accounts))

    @router.callback_query(F.data.startswith("acc_sync:"))
    async def sync_one_cb(call: CallbackQuery) -> None:
        if not ctx["admins"].check(call.from_user.id):
            return
        account_id = int(call.data.split(":")[1])
        await call.answer("Синхронизация...")
        added, updated, msg = await ctx["userbots"].sync_dialogs(account_id)
        await call.message.answer(f"✅ {msg}")

    @router.callback_query(F.data == "sync:all")
    async def sync_all_cb(call: CallbackQuery) -> None:
        if not ctx["admins"].check(call.from_user.id):
            return
        accounts = await ctx["db"].get_accounts(only_enabled=True)
        await call.answer("Синхронизация всех...")
        lines = []
        for acc in accounts:
            added, updated, msg = await ctx["userbots"].sync_dialogs(acc.id)
            lines.append(f"{acc.name}: {msg}")
        await call.message.answer("✅\n" + "\n".join(lines))

    # --- Add chat ---

    @router.message(F.text == "➕ Добавить чат")
    async def add_chat_btn(message: Message, state: FSMContext) -> None:
        if not ctx["admins"].check(message.from_user.id):
            return
        accounts = await ctx["db"].get_accounts(only_enabled=True)
        if not accounts:
            await message.answer("Сначала добавьте аккаунт.")
            return
        await message.answer(
            "Выберите аккаунт для добавления чата:",
            reply_markup=add_chat_accounts_kb(accounts),
        )

    @router.callback_query(F.data.startswith("addchat_acc:"))
    async def add_chat_acc_cb(call: CallbackQuery, state: FSMContext) -> None:
        if not ctx["admins"].check(call.from_user.id):
            return
        account_id = int(call.data.split(":")[1])
        await state.set_state(AddChat.chat_ref)
        await state.update_data(account_id=account_id)
        await call.message.answer(
            "Отправьте @username, chat_id или invite-ссылку (t.me/+...):",
            reply_markup=cancel_kb(),
        )
        await call.answer()

    @router.message(AddChat.chat_ref)
    async def add_chat_ref(message: Message, state: FSMContext) -> None:
        if message.text == "❌ Отмена":
            await _cancel(message, state)
            return
        data = await state.get_data()
        account_id = data["account_id"]
        ref = message.text.strip()

        if "t.me/" in ref or ref.startswith("+"):
            ok, msg = await ctx["userbots"].join_chat(account_id, ref)
        else:
            ok, msg, _ = await ctx["userbots"].resolve_chat(account_id, ref)

        await state.clear()
        await message.answer(("✅ " if ok else "❌ ") + msg, reply_markup=main_menu_kb())

    # --- Message ---

    @router.message(F.text == "📨 Сообщение")
    async def set_message_btn(message: Message, state: FSMContext) -> None:
        if not ctx["admins"].check(message.from_user.id):
            return
        await state.set_state(SetMessage.waiting)
        await message.answer(
            "Перешлите боту сообщение, которое нужно рассылать.\n"
            "Поддерживаются текст, фото, видео и другие типы.",
            reply_markup=cancel_kb(),
        )

    @router.message(SetMessage.waiting)
    async def set_message_forward(message: Message, state: FSMContext) -> None:
        if message.text == "❌ Отмена":
            await _cancel(message, state)
            return
        if not message.forward_from_chat or not message.forward_from_message_id:
            await message.answer("Нужно переслать сообщение из канала/чата.")
            return

        await ctx["db"].set_ad_message(
            from_chat_id=message.forward_from_chat.id,
            message_id=message.forward_from_message_id,
            account_id=None,
            label="Основное",
        )
        await state.clear()
        await message.answer(
            "✅ Рекламное сообщение сохранено (глобальное для всех аккаунтов).",
            reply_markup=main_menu_kb(),
        )

    @router.callback_query(F.data == "back:main")
    async def back_main_cb(call: CallbackQuery) -> None:
        await call.message.delete()
        await call.answer()

    async def _cancel(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_kb())

    return router
