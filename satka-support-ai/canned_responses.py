"""Hardcoded replies — bypass LLM for common VPN questions."""

from __future__ import annotations

import re

GREETING_WORDS = (
    "привет", "прив", "здравствуй", "здравствуйте", "hello", "hi", "hey",
    "добрый день", "добрый вечер", "доброе утро", "хай", "салам", "приветствую",
    "privet", "helo", "hola",
)

CONNECT_RE = re.compile(
    r"("
    r"как\s+подключ|"
    r"как\s+оформ|"
    r"как\s+куп|"
    r"как\s+начать|"
    r"как\s+пользов|"
    r"как\s+настро|"
    r"как\s+включ|"
    r"как\s+установ|"
    r"как\s+добав|"
    r"как\s+получ\w*\s+подписк|"
    r"как\s+работает|"
    r"инструкц|"
    r"подключ\w*\s+подписк"
    r")",
    re.IGNORECASE,
)

PRICE_RE = re.compile(
    r"(сколько\s+стоит|цена|тариф|прайс|стоимость|сколько\s+денег)",
    re.IGNORECASE,
)

NOT_WORKING_RE = re.compile(
    r"(не\s+работ|не\s+подключ|не\s+включ|не\s+груз|не\s+открыв|"
    r"ошибк|timeout|таймаут|отвал|висит|медлен)",
    re.IGNORECASE,
)

SERVICE_INFO_RE = re.compile(
    r"("
    r"расскаж|"
    r"чем\s+отлича|"
    r"что\s+такое|"
    r"что\s+умеет|"
    r"что\s+за\s+сервис|"
    r"преимущества|"
    r"почему\s+(вы|вас|satka|сатк)|"
    r"об\s+сервисе|"
    r"про\s+сервис|"
    r"про\s+satka|"
    r"про\s+сатк|"
    r"про\s+впн|"
    r"про\s+vpn"
    r")",
    re.IGNORECASE,
)

GREETING_REPLY = (
    "Здравствуйте! Поддержка Satka VPN.\n"
    "Чем помочь — подключение, тарифы, Happ, оплата, кабинет?"
)

GREETING_AGAIN_REPLY = (
    "Чем помочь по Satka VPN — подключение, тарифы, Happ, оплата, кабинет?"
)

CONNECT_REPLY = (
    "Как подключить Satka VPN:\n"
    "1. @satkavpn_bot → /start → «Подписка» (или бесплатный период 4 дня)\n"
    "2. Оплатить и скопировать ссылку подписки целиком\n"
    "3. Установить Happ → «+» → вставить ссылку\n"
    "4. Обновить список серверов → выбрать локацию → подключить\n\n"
    "Альтернатива: кабинет node.satkaconnect.xyz\n"
    "Если что-то не получается — опишите на каком шаге застряли."
)

PRICE_REPLY = (
    "Тарифы Satka VPN (безлимит):\n"
    "• Базовый (1 устр.): от 20 ₽/день, 50 ₽/30 дней\n"
    "• Расширенный (3 устр.): от 99 ₽/30 дней\n"
    "• Для мамы (обход глушилок LTE): от 69 ₽/30 дней\n"
    "• Семейный (7 устр.): от 145 ₽/30 дней\n"
    "• Бесплатный: 4 дня в @satkavpn_bot\n\n"
    "Оформить: @satkavpn_bot → Подписка"
)

NOT_WORKING_REPLY = (
    "Попробуйте по порядку:\n"
    "1. Проверить срок подписки в @satkavpn_bot\n"
    "2. Happ → обновить подписку (потянуть список вниз)\n"
    "3. Сменить локацию/сервер\n"
    "4. Перезапустить Happ и телефон\n"
    "5. Отключить другой VPN\n\n"
    "Не помогло — напишите что именно не работает (или скрин из Happ)."
)

SERVICE_INFO_REPLY = (
    "Satka VPN — VPN-сервис с тарифами от 20 ₽/день и бесплатным периодом 4 дня.\n\n"
    "• Тарифы на 1–25 устройств\n"
    "• «Для мамы» — обход глушилок LTE\n"
    "• Подключение через Happ по одной ссылке\n"
    "• Оплата: карта, СБП, Stars, крипто\n"
    "• Бот @satkavpn_bot, кабинет node.satkaconnect.xyz\n\n"
    "Что интересует — цена, устройства или обход блокировок?"
)

STICKER_REPLY = (
    "Получил стикер. Напишите текстом вопрос по Satka VPN — "
    "подключение, тарифы, Happ, оплата, кабинет."
)

OPERATOR_FIRST_HINT = (
    "\n\nЕсли не смогу помочь — напишите «Оператор», подключим специалиста."
)


def _is_greeting(text: str) -> bool:
    low = text.lower().strip().rstrip("!?.")
    if low in GREETING_WORDS:
        return True
    return any(low.startswith(w) for w in GREETING_WORDS) and len(low) < 35


def is_greeting_word(text: str) -> bool:
    return _is_greeting(text)


def with_first_hint(text: str, *, first_contact: bool) -> str:
    if not first_contact or "оператор" in text.lower():
        return text
    return text + OPERATOR_FIRST_HINT


def match_canned(text: str, *, already_greeted: bool = False) -> str | None:
    cleaned = (text or "").strip()
    if not cleaned:
        return None
    if _is_greeting(cleaned):
        return GREETING_AGAIN_REPLY if already_greeted else GREETING_REPLY
    if CONNECT_RE.search(cleaned):
        return CONNECT_REPLY
    if PRICE_RE.search(cleaned) and not NOT_WORKING_RE.search(cleaned):
        return PRICE_REPLY
    if NOT_WORKING_RE.search(cleaned):
        return NOT_WORKING_REPLY
    if SERVICE_INFO_RE.search(cleaned):
        return SERVICE_INFO_REPLY
    return None
