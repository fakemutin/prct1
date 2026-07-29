"""Hardcoded replies for common questions — bypass LLM for reliability."""

from __future__ import annotations

import re

GREETING_RE = re.compile(
    r"^(привет|прив|здравствуй|здравствуйте|hello|hi|hey|добрый\s+(день|вечер|утро)|"
    r"хай|салам|доброго\s+времени|приветствую)[\s!?.]*$",
    re.IGNORECASE,
)

SERVICE_INFO_RE = re.compile(
    r"("
    r"расскаж\w*\s+(всё|все|мне)?\s*(о|про)\s+(сервис|satka|сатк|впн|vpn)|"
    r"чем\s+отлича|"
    r"что\s+такое\s+(satka|сатк|ваш\s+vpn|этот\s+vpn)|"
    r"что\s+умеет|"
    r"преимущества|"
    r"почему\s+(вы|вас|satka)|"
    r"что\s+за\s+сервис|"
    r"об\s+сервисе|"
    r"про\s+сервис"
    r")",
    re.IGNORECASE,
)

GREETING_REPLY = (
    "Привет! Я из поддержки Satka VPN 🤍\n\n"
    "Могу рассказать про сервис и тарифы, помочь подключить Happ, "
    "разобраться с оплатой, кабинетом, скоростью и устройствами.\n"
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
    "это наши сильные стороны. Что для вас важнее — цена, несколько устройств или обход блокировок?"
)


def match_canned(text: str) -> str | None:
    cleaned = (text or "").strip()
    if not cleaned:
        return None
    if GREETING_RE.match(cleaned):
        return GREETING_REPLY
    if SERVICE_INFO_RE.search(cleaned):
        return SERVICE_INFO_REPLY
    return None
