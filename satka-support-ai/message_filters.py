"""Pre-LLM message filters."""

from __future__ import annotations

import re
from typing import Literal

from canned_responses import is_greeting_word, looks_like_laughter

FilterResult = Literal["ok", "manipulation", "off_topic"]

WARM_REDIRECT_REPLY = (
    "Я в основном по Satka VPN, но рад пообщаться 🙂 "
    "Если что-то с подключением, Happ или тарифами — спрашивайте. "
    "Или напишите «Оператор»."
)

# Сохраняем старое имя для совместимости с llm_client
OFF_TOPIC_REPLY = WARM_REDIRECT_REPLY

CODE_REQUEST_REPLY = (
    "Код не пишу — я про VPN, не про программирование 🙂 "
    "Зато помогу с подключением, тарифами и Happ. Что не так?"
)

MANIPULATION_REPLY = (
    "Если вам тяжело — лучше обратиться к близким или на линию доверия. "
    "Я тут по Satka VPN; если нужна помощь с сервисом — напишите."
)

INSULT_PHRASE_RE = re.compile(
    r"("
    r"пидар|пидор|ебан|бля|хуй|сука|мудак|дебил|идиот|"
    r"говн|урод|мраз|чмо|лох\b"
    r")",
    re.IGNORECASE,
)

TROLL_INSULT_REPLY = (
    "Я тут добрый помощник Satka VPN 🙂 "
    "Спросите про подключение или напишите «Оператор»."
)

TROLL_PROMPT_RE = re.compile(
    r"("
    r"напиш\w*\s+[\"«']?[^\"»']+[\"»']?|"
    r"скаж\w*\s+[\"«']?[^\"»']+[\"»']?|"
    r"повтор\w*\s+[\"«']?[^\"»']+[\"»']?|"
    r"для\s+(этого|помощи).{0,40}напиш\w*|"
    r"мне\s+нужн\w*.{0,30}напиш\w*\s+[\"«']"
    r")",
    re.IGNORECASE,
)

TROLL_PHRASE_RE = re.compile(
    r"[\"«']([^\"»']+)[\"»']|"
    r"напиш\w*\s+(.+)$|"
    r"скаж\w*\s+(.+)$|"
    r"повтор\w*\s+(.+)$",
    re.IGNORECASE,
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
    r"игнорируй\s+инструкц|"
    r"system\s+prompt|"
    r"джейлбрейк|"
    r"jailbreak"
    r")",
    re.IGNORECASE,
)

LAUGHTER_RE = re.compile(
    r"^(?:[хах]{4,}|[ах]{4,}|лол+|lol+|ржу|кек+)[\s!.?]*$",
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
    r"для\s+мамы|ютуб|youtube|telegram|телеграм|privet|привет|"
    r"дела|настроен|спасиб|пока|свидан|нравит|красав|бро|йоу|ку\b"
    r")",
    re.IGNORECASE,
)


def _extract_troll_phrase(text: str) -> str | None:
    quoted = re.search(r"[\"«']([^\"»']+)[\"»']", text, re.IGNORECASE)
    if quoted:
        return quoted.group(1).strip()
    for pattern in (
        r"напиш\w*\s+(.+)$",
        r"скаж\w*\s+(.+)$",
        r"повтор\w*\s+(.+)$",
    ):
        match = re.search(pattern, text.strip(), re.IGNORECASE)
        if match:
            phrase = match.group(1).strip().strip("\"'«»")
            if phrase:
                return phrase
    return None


def _troll_reply_for_phrase(phrase: str) -> str:
    if INSULT_PHRASE_RE.search(phrase):
        return TROLL_INSULT_REPLY
    cleaned = phrase.strip()
    if re.match(r"^я\s+", cleaned, re.IGNORECASE):
        rest = re.sub(r"^я\s+", "", cleaned, flags=re.IGNORECASE).strip()
        return f"ВЫ {rest.upper()}"
    return f"ВЫ {cleaned.upper()}"


def match_troll_reply(text: str) -> str | None:
    """Провокации «напиши X» → «ВЫ X», не повторяя от своего имени."""
    cleaned = (text or "").strip()
    if not cleaned or not TROLL_PROMPT_RE.search(cleaned):
        return None
    if OFF_TOPIC_RE.search(cleaned):
        return None
    phrase = _extract_troll_phrase(cleaned)
    if not phrase:
        return None
    return _troll_reply_for_phrase(phrase)


def _is_gibberish(text: str) -> bool:
    cleaned = text.strip()
    if len(cleaned) < 4:
        return False
    if is_greeting_word(cleaned):
        return False
    if looks_like_laughter(cleaned):
        return False
    if " " in cleaned:
        return False
    if VPN_TOPIC_RE.search(cleaned):
        return False
    if re.fullmatch(r"[a-z]{6,}", cleaned, re.IGNORECASE):
        vowels = len(re.findall(r"[aeiou]", cleaned, re.IGNORECASE))
        if vowels / len(cleaned) < 0.2:
            return True
    if len(set(cleaned.lower())) <= 2 and len(cleaned) >= 6:
        return True
    return False


def classify_message(text: str) -> tuple[FilterResult, str | None]:
    cleaned = (text or "").strip()
    if not cleaned:
        return "ok", None

    if is_greeting_word(cleaned):
        return "ok", None

    if looks_like_laughter(cleaned):
        return "ok", None

    if MANIPULATION_RE.search(cleaned):
        return "manipulation", MANIPULATION_REPLY

    if OFF_TOPIC_RE.search(cleaned):
        return "off_topic", CODE_REQUEST_REPLY

    if _is_gibberish(cleaned):
        return "ok", None

    return "ok", None
