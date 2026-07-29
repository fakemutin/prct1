"""Hardcoded replies for common questions — bypass LLM for reliability."""

from __future__ import annotations

import re

GREETING_WORDS = (
    "привет", "прив", "здравствуй", "здравствуйте", "hello", "hi", "hey",
    "добрый день", "добрый вечер", "доброе утро", "хай", "салам", "приветствую",
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
    r"про\s+vpn|"
    r"всё\s+о\s+сервис|"
    r"все\s+о\s+сервис"
    r")",
    re.IGNORECASE,
)

GREETING_REPLY = (
    "Привет! Я из поддержки Satka VPN 🤍\n\n"
    "Могу рассказать про сервис и тарифы, помочь подключить Happ, "
    "разобраться с оплатой, кабинетом, скоростью, устройствами и рефералкой.\n"
    "Что вас интересует?"
)

SERVICE_INFO_REPLY = (
    "Satka VPN — VPN-сервис с доступными тарифами от 20 ₽/день и бесплатным периодом 4 дня.\n\n"
    "Что есть у нас:\n"
    "• Тарифы на 1–25 устройств — Базовый, Расширенный, Семейный, Бизнес\n"
    "• «Для мамы» — отдельный тариф для обхода глушилок LTE\n"
    "• Подключение через Happ — одна ссылка, без сложных настроек\n"
    "• Оплата: карта, СБП, Telegram Stars, криптовалюта\n"
    "• Бот @satkavpn_bot и кабинет node.satkaconnect.xyz\n"
    "• Реферальная программа с бонусами\n"
    "• Поддержка работает круглосуточно\n\n"
    "Сравнивать все VPN не буду, но если важны цена, простота и гибкие тарифы — "
    "это наши сильные стороны.\n"
    "Что для вас важнее — цена, несколько устройств или обход блокировок?"
)

OPERATOR_FIRST_HINT = (
    "\n\nЕсли не смогу помочь — напишите «Оператор», подключим специалиста."
)


def _is_greeting(text: str) -> bool:
    low = text.lower().strip().rstrip("!?.")
    if low in GREETING_WORDS:
        return True
    return any(low.startswith(w) for w in GREETING_WORDS) and len(low) < 35


def with_first_hint(text: str, *, first_contact: bool) -> str:
    if not first_contact or "оператор" in text.lower():
        return text
    return text + OPERATOR_FIRST_HINT


def match_canned(text: str) -> str | None:
    cleaned = (text or "").strip()
    if not cleaned:
        return None
    if _is_greeting(cleaned):
        return GREETING_REPLY
    if SERVICE_INFO_RE.search(cleaned):
        return SERVICE_INFO_REPLY
    return None
