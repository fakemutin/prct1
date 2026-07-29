"""Pre-LLM message filters."""

from __future__ import annotations

import re
from typing import Literal

from canned_responses import is_greeting_word

FilterResult = Literal["ok", "manipulation", "off_topic"]

OFF_TOPIC_REPLY = (
    "Работаем только по Satka VPN: подключение, тарифы, Happ, оплата, кабинет. "
    "Напишите вопрос по сервису."
)

MANIPULATION_REPLY = (
    "Работаем только по Satka VPN. Не надо меня обманывать. "
    "Если есть вопрос по сервису — напишите."
)

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

OFF_TOPIC_RE = re.compile(
    r"("
    r"напиш\w*\s+(мне\s+)?(код|скрипт)|"
    r"написать\s+скрипт|"
    r"напиши\s+код|"
    r"сделай\s+(мне\s+)?(код|скрипт|бот)|"
    r"код\s+на\s+(python|питон|js|javascript|java|c\+\+)|"
    r"скрипт\s+для|"
    r"hello\s*world|"
    r"print\s*\(|"
    r"def\s+\w+\s*\(|"
    r"import\s+\w+|"
    r"telethon|"
    r"userbot|"
    r"юзербот|"
    r"автоматиз|"
    r"без\s+ui|"
    r"нету\s+ui|"
    r"программир|"
    r"помоги\s+с\s+(python|кодом|программ)|"
    r"расскажи\s+анекдот|"
    r"поиграем|"
    r"игнорируй\s+инструкц|"
    r"system\s+prompt|"
    r"джейлбрейк|"
    r"jailbreak|"
    r"ты\s+(бот|ии|нейросет\w*)|"
    r"кто\s+((твой|ваш)\s+)?создател\w*|"
    r"кто\s+тебя\s+(сделал|создал|написал)"
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
    r"приложен|настро|включ|выключ|переустанов|"
    r"для\s+мамы|ютуб|youtube|telegram|телеграм|privet|привет"
    r")",
    re.IGNORECASE,
)


def _is_gibberish(text: str) -> bool:
    cleaned = text.strip()
    if len(cleaned) < 4:
        return False
    if is_greeting_word(cleaned):
        return False
    if " " in cleaned:
        return False
    if VPN_TOPIC_RE.search(cleaned):
        return False
    # только латиница 6+ символов без гласных слов — клавиатурный мусор
    if re.fullmatch(r"[a-z]{6,}", cleaned, re.IGNORECASE):
        vowels = len(re.findall(r"[aeiou]", cleaned, re.IGNORECASE))
        if vowels / len(cleaned) < 0.2:
            return True
    # повтор одной буквы: цццц, аааа
    if len(set(cleaned.lower())) <= 2 and len(cleaned) >= 4:
        return True
    return False


def classify_message(text: str) -> tuple[FilterResult, str | None]:
    cleaned = (text or "").strip()
    if not cleaned:
        return "ok", None

    if is_greeting_word(cleaned):
        return "ok", None

    if MANIPULATION_RE.search(cleaned):
        return "manipulation", MANIPULATION_REPLY

    # Код/скрипты — всегда оффтоп, даже если упомянут VPN
    if OFF_TOPIC_RE.search(cleaned):
        return "off_topic", OFF_TOPIC_REPLY

    if _is_gibberish(cleaned):
        return "off_topic", OFF_TOPIC_REPLY

    # Длинный текст без VPN-темы
    if len(cleaned) > 80 and not VPN_TOPIC_RE.search(cleaned):
        return "off_topic", OFF_TOPIC_REPLY

    return "ok", None
