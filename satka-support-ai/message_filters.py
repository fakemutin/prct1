"""Pre-LLM message filters for off-topic and manipulation attempts."""

from __future__ import annotations

import re
from typing import Literal

FilterResult = Literal["ok", "manipulation", "off_topic"]

MANIPULATION_REPLY = (
    "Я общаюсь только по темам VPN. Не надо меня обманывать и уверять в этом. "
    "Если есть вопрос по Satka VPN — напишите."
)

OFF_TOPIC_REPLY = (
    "Я помогаю только по Satka VPN: подписка, Happ, оплата и кабинет. "
    "Напишите, что именно не работает или что хотите настроить."
)

# Провокации, эмоциональный шантаж, самоповреждение — не отправляем в LLM
MANIPULATION_RE = re.compile(
    r"("
    r"спрыгн\w*|"
    r"прыгн\w*\s+с\s+(крыш|окн|мост)|"
    r"суицид|"
    r"самоубий\w*|"
    r"поконч\w*\s+с\s+собой|"
    r"повес\w*|"
    r"хочу\s+умер\w*|"
    r"не\s+хочу\s+жить|"
    r"режу\s+вен\w*|"
    r"убью\s+себя|"
    r"убить\s+себя|"
    r"пореж\w+\s+вен\w*|"
    r"навреж\w+\s+себе|"
    r"умру\s+сегодня|"
    r"лучше\s+бы\s+я\s+умер|"
    r"в\s+петл\w+|"
    r"таблет\w+\s+выпью"
    r")",
    re.IGNORECASE,
)

# Явно не про VPN — короткий отказ без развёрнутых лекций
OFF_TOPIC_RE = re.compile(
    r"("
    r"кто\s+((твой|ваш)\s+)?создател\w*|"
    r"кто\s+тебя\s+(сделал|создал|написал|программировал)|"
    r"ты\s+(бот|ии|нейросет\w*|искусственн\w*)|"
    r"как\s+тебя\s+зовут|"
    r"сколько\s+тебе\s+лет|"
    r"где\s+ты\s+живёшь|"
    r"расскажи\s+анекдот|"
    r"поиграем|"
    r"выполни\s+команду|"
    r"игнорируй\s+инструкц|"
    r"system\s+prompt|"
    r"джейлбрейк|"
    r"jailbreak"
    r")",
    re.IGNORECASE,
)

VPN_TOPIC_RE = re.compile(
    r"("
    r"vpn|впн|satka|сатка|happ|хапп|подписк|тариф|оплат|баланс|"
    r"ключ|сервер|локац|подключ|интернет|скорост|пинг|timeout|таймаут|"
    r"кабинет|node\.satkaconnect|satkavpn|белый\s+список|глушил|"
    r"lte|wifi|wi-?fi|android|iphone|ios|телефон|устройств|"
    r"пробн|триал|реферал|промокод|возврат|чек|оператор|"
    r"импорт|ссылк|ошибк|не\s+работ|помог|проблем|срочн|"
    r"не\s+могу|не\s+получ|не\s+вижу|не\s+открыв|не\s+заход|"
    r"купил|оплатил|деньг|рубл|завис|висит|отвал|"
    r"приложен|программ|настро|включ|выключ|переустанов"
    r")",
    re.IGNORECASE,
)


def classify_message(text: str) -> tuple[FilterResult, str | None]:
    cleaned = (text or "").strip()
    if not cleaned:
        return "ok", None

    if MANIPULATION_RE.search(cleaned):
        return "manipulation", MANIPULATION_REPLY

    if OFF_TOPIC_RE.search(cleaned):
        return "off_topic", OFF_TOPIC_REPLY

    # Длинное сообщение без единого признака обращения в поддержку — скорее оффтоп
    if len(cleaned) > 80 and not VPN_TOPIC_RE.search(cleaned):
        return "off_topic", OFF_TOPIC_REPLY

    return "ok", None
