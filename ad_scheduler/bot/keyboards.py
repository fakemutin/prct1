from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статус"), KeyboardButton(text="▶️ Старт")],
            [KeyboardButton(text="⏹ Стоп"), KeyboardButton(text="📋 Чаты")],
            [KeyboardButton(text="👤 Аккаунты"), KeyboardButton(text="📨 Сообщение")],
            [KeyboardButton(text="🔄 Синхронизация"), KeyboardButton(text="➕ Добавить чат")],
            [KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )


def accounts_kb(accounts: list) -> InlineKeyboardMarkup:
    rows = []
    for acc in accounts:
        status = "🟢" if acc.enabled else "🔴"
        rows.append([
            InlineKeyboardButton(
                text=f"{status} {acc.name} ({acc.phone})",
                callback_data=f"acc:{acc.id}",
            )
        ])
    rows.append([InlineKeyboardButton(text="➕ Добавить аккаунт", callback_data="acc:add")])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def account_detail_kb(account_id: int, enabled: bool) -> InlineKeyboardMarkup:
    toggle_text = "🔴 Выключить" if enabled else "🟢 Включить"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=toggle_text, callback_data=f"acc_toggle:{account_id}")],
            [InlineKeyboardButton(text="🔄 Синхронизировать чаты", callback_data=f"acc_sync:{account_id}")],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"acc_del:{account_id}")],
            [InlineKeyboardButton(text="🔙 К аккаунтам", callback_data="acc:list")],
        ]
    )


def chats_kb(chats: list, page: int = 0, per_page: int = 8) -> InlineKeyboardMarkup:
    start = page * per_page
    chunk = chats[start : start + per_page]
    rows = []
    for chat in chunk:
        status = "🟢" if chat.enabled else "🔴"
        name = chat.title[:28] + ("…" if len(chat.title) > 28 else "")
        rows.append([
            InlineKeyboardButton(
                text=f"{status} {name}",
                callback_data=f"chat:{chat.id}",
            )
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"chats_page:{page-1}"))
    if start + per_page < len(chats):
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"chats_page:{page+1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def chat_detail_kb(chat_id: int, enabled: bool) -> InlineKeyboardMarkup:
    toggle = "🔴 Выключить" if enabled else "🟢 Включить"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=toggle, callback_data=f"chat_toggle:{chat_id}")],
            [InlineKeyboardButton(text="📤 Отправить сейчас", callback_data=f"chat_post:{chat_id}")],
            [InlineKeyboardButton(text="⏱ Интервал 1ч", callback_data=f"chat_int:{chat_id}:1")],
            [InlineKeyboardButton(text="⏱ Интервал 2ч", callback_data=f"chat_int:{chat_id}:2")],
            [InlineKeyboardButton(text="⏱ Интервал 3ч", callback_data=f"chat_int:{chat_id}:3")],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"chat_del:{chat_id}")],
            [InlineKeyboardButton(text="🔙 К чатам", callback_data="chats:list")],
        ]
    )


def sync_accounts_kb(accounts: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"🔄 {a.name}", callback_data=f"acc_sync:{a.id}")]
        for a in accounts
    ]
    rows.append([InlineKeyboardButton(text="🔄 Все аккаунты", callback_data="sync:all")])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def add_chat_accounts_kb(accounts: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=a.name, callback_data=f"addchat_acc:{a.id}")]
        for a in accounts
    ]
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
