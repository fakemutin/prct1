"""Smart canned replies — основной мозг пока LLM на лимите."""

from __future__ import annotations

import re

GREETING_WORDS = (
    "привет", "прив", "приветик", "здравствуй", "здравствуйте", "hello", "hi", "hey",
    "добрый день", "добрый вечер", "доброе утро", "хай", "салам", "приветствую",
    "privet", "helo", "hola", "ку", "куку", "йоу", "йо", "yo", "сап", "здарова",
    "здаров", "дратути",
)

ACK_RE = re.compile(
    r"^(понял|понятно|ясно|ок|okay|ok|спасибо|благодарю|хорошо|ладно|угу|да|"
    r"всё\s+понял|все\s+понял|понял\s+вас|спс|thx|thanks|красавчик|класс|"
    r"супер|отлично|круто|топ|огонь)[\s!.?]*$",
    re.IGNORECASE,
)

SMALL_TALK_RE = re.compile(
    r"(как\s+дела|как\s+ты|как\s+сам|как\s+жизнь|что\s+нового|как\s+настроение|"
    r"как\s+поживаешь|чем\s+занят)",
    re.IGNORECASE,
)

FAREWELL_RE = re.compile(
    r"(досвидан|до\s+свидан|пока\b|увидимся|всего\s+(добр|хорош)|"
    r"ничего[,\s].*(досвидан|пока)|спокойной\s+ноч)",
    re.IGNORECASE,
)

COMPLIMENT_RE = re.compile(
    r"(нравит\w*\s+поддержк|классн\w*\s+поддержк|хорош\w*\s+поддержк|"
    r"вы\s+молодц|спасибо\s+за\s+помощь|благодарю\s+за)",
    re.IGNORECASE,
)

CASUAL_RE = re.compile(
    r"^(ку|йоу|йо|yo|сап|здарова|чикаго\s+бро|бро|пацаны|братан)[\s!.?]*$",
    re.IGNORECASE,
)

SLANG_ACK_RE = re.compile(
    r"^(похуй|пофиг|ну\s+похуй|да\s+похуй|норм|заебок|базару\s+нет|"
    r"ок\s+ок|пон|понял|ясно|угу|ага|аа|ну\s+ок)[\s!.?\\]*$",
    re.IGNORECASE,
)

SLANG_FRUST_RE = re.compile(
    r"^(бля|блять|бляд|сука|пиздец|ебать|фу\s+ебать|блядь|жесть|зуйня|"
    r"нихуя|не\s+интересн)[\s!.?]*$",
    re.IGNORECASE,
)

SLANG_WHAT_RE = re.compile(
    r"^(че|чё|чо|шо|чего|слышь|слуш|эй|э|а\?)[\s!.?]*$",
    re.IGNORECASE,
)

SLANG_HEAR_RE = re.compile(
    r"^(слышь|слуш|эй)\s+",
    re.IGNORECASE,
)

LAUGHTER_RE = re.compile(
    r"^(?:[хах]{4,}|[ах]{4,}|лол+|lol+|ржу|кек+)[\s!.?]*$",
    re.IGNORECASE,
)

BANTER_RE = re.compile(
    r"(шо\s+ты|фу\s+бяка|не\s+интересн|ты\s+маленьк|бяка|скучн|фигня|фигн)",
    re.IGNORECASE,
)

AFFECTION_RE = re.compile(
    r"(люблю\s+тебя|обожаю\s+тебя|ты\s+лучш|ты\s+крут|ты\s+класс)",
    re.IGNORECASE,
)

WRITE_WORD_RE = re.compile(
    r"^напиш\w*\s+([а-яёa-z0-9][а-яёa-z0-9\s\-]{0,40})$",
    re.IGNORECASE,
)

from banter_replies import match_banter, pick_casual_fallback, pick_sticker_reply
from routing import needs_llm_thinking
from slang_lexicon import match_slang_lexicon
from troll_replies import smart_troll_reply

# Подписка / подключение — приоритет выше «расскажите о сервисе»
SUBSCRIPTION_RE = re.compile(
    r"("
    r"как\s+(сделать|оформ|получ|куп|подключ|активир|взять|завести)|"
    r"как\s+работает|"
    r"сделать\s+подписк|"
    r"оформ\w*\s+подписк|"
    r"получ\w*\s+подписк|"
    r"куп\w*\s+подписк|"
    r"взять\s+подписк|"
    r"подключ\w*\s+подписк|"
    r"где\s+подписк|"
    r"где\s+куп|"
    r"где\s+оформ|"
    r"инструкц|"
    r"пошагов|"
    r"науч\w*\s+подключ"
    r")",
    re.IGNORECASE,
)

PRICE_RE = re.compile(
    r"(сколько\s+стоит|цена|тариф|прайс|стоимость|сколько\s+денег|почём)",
    re.IGNORECASE,
)

NOT_WORKING_RE = re.compile(
    r"(не\s+работ|не\s+подключ|не\s+включ|не\s+груз|не\s+открыв|"
    r"ошибк|timed?\s*out|timeout|таймаут|отвал|висит|медлен|не\s+идёт|"
    r"502|gateway|gate\s*away|отьебн|зуйн|нихуя\s+не|не\s+фурычит|"
    r"не\s+пашет|не\s+коннект|белые\s+списк|бс\s+не|глушил)",
    re.IGNORECASE,
)

SERVICE_INFO_RE = re.compile(
    r"("
    r"чем\s+отлича|"
    r"что\s+такое\s+(satka|сатк|vpn|впн)|"
    r"что\s+за\s+сервис|"
    r"преимущества|"
    r"почему\s+(вы|вас|satka|сатк)|"
    r"об\s+сервисе|"
    r"про\s+сервис$|"
    r"про\s+satka$|"
    r"про\s+vpn$"
    r")",
    re.IGNORECASE,
)

# «расскажите» только если НЕТ вопроса про подписку/подключение
TELL_ABOUT_RE = re.compile(r"расскаж\w*", re.IGNORECASE)

GREETING_REPLY = (
    "йоу, привет 👋"
    "|||SPLIT|||"
    "я по Satka VPN — подключение, тарифы, хапп, оплата. чё надо?"
)

GREETING_AGAIN_REPLY = "на связи|||SPLIT|||чё по впну?"

CASUAL_REPLY = (
    "йоу 🙂"
    "|||SPLIT|||"
    "слушаю, чем помочь — впн, хапп, тарифы?"
)

CONNECT_REPLY = (
    "смотри, по шагам:"
    "|||SPLIT|||"
    "1. @satkavpn_bot → /start → подписка (или 4 дня бесплатно)\n"
    "2. оплатить, скопировать ссылку целиком\n"
    "3. Happ → + → вставить ссылку\n"
    "4. обновить серверы → выбрать локацию → коннект"
    "|||SPLIT|||"
    "кабинет: node.satkaconnect.xyz — на каком шаге затык?"
)

PRICE_REPLY = (
    "тарифы (безлимит):"
    "|||SPLIT|||"
    "• базовый (1 устр): от 20₽/день, 50₽/30 дней\n"
    "• расширенный (3 устр): 99₽/30\n"
    "• для мамы (глушилки LTE): от 69₽/30\n"
    "• семейный (7 устр): 145₽/30\n"
    "• бесплатка: 4 дня в @satkavpn_bot"
    "|||SPLIT|||"
    "оформить: @satkavpn_bot → подписка"
)

NOT_WORKING_REPLY = (
    "понял, давай по порядку:"
    "|||SPLIT|||"
    "1. срок подписки в @satkavpn_bot глянь\n"
    "2. Happ → потяни список вниз (обновить)\n"
    "3. смени сервер/локацию\n"
    "4. перезапусти хапп и телефон\n"
    "5. другой впн выруби если есть"
    "|||SPLIT|||"
    "не взлетело — напиши айфон/андроид, вайфай или лте, и текст ошибки из хаппа"
)

SERVICE_INFO_REPLY = (
    "Satka VPN — от 20₽/день, есть 4 дня бесплатно"
    "|||SPLIT|||"
    "подключение через Happ, оплата картой/сбп/stars/крипто\n"
    "бот @satkavpn_bot, кабинет node.satkaconnect.xyz"
    "|||SPLIT|||"
    "чё интересует — подключение, цена или обход блокировок?"
)

ACK_REPLY = "пон, обращайся если чё|||SPLIT|||или «Оператор» если нужен живой чел"

SMALL_TALK_REPLY = (
    "норм, на связи 🙂"
    "|||SPLIT|||"
    "по впну чё — подключение, тарифы, хапп?"
)

FAREWELL_REPLY = "давай, удачи 👋|||SPLIT|||если чё — пиши"

COMPLIMENT_REPLY = "спс, приятно 🙌|||SPLIT|||рад помочь по впну если надо"

LAUGHTER_REPLY = "ахах 😄|||SPLIT|||чё, по впну помочь или просто поржали?"

BANTER_REPLY = "ну я стараюсь 😄|||SPLIT|||давай по делу — впн, хапп, тарифы?"

AFFECTION_REPLY = "спс, взаимно 🙌|||SPLIT|||по впну чё надо?"

CASUAL_CHAT_REPLY = pick_casual_fallback  # legacy alias; use pick_casual_fallback(text)

STICKER_REPLY = pick_sticker_reply  # legacy; call pick_sticker_reply() at runtime

BUSY_REPLY = (
    "Сейчас высокая нагрузка на ассистента. Кратко:\n"
    "• Подписка: @satkavpn_bot → /start → Подписка\n"
    "• Подключение: ссылка из бота → Happ → импорт → обновить → подключить\n"
    "• Проблема: опишите что не работает или напишите «Оператор»"
)

OPERATOR_FIRST_HINT = (
    "\n\nесли не вывезу — напиши «Оператор», подключим чела"
)

SLANG_ACK_REPLY = "ну ок 😄|||SPLIT|||по впну чё, всё норм?"
SLANG_FRUST_REPLY = "ага, понял|||SPLIT|||чё случилось, по впну затык?"
SLANG_WHAT_REPLY = "на месте|||SPLIT|||чё надо?"
SLANG_HEAR_REPLY = "слушаю|||SPLIT|||говори"


def _is_greeting(text: str) -> bool:
    low = text.lower().strip().rstrip("!?.")
    if low in GREETING_WORDS:
        return True
    return any(low.startswith(w) for w in GREETING_WORDS) and len(low) < 40


def is_greeting_word(text: str) -> bool:
    return _is_greeting(text)


def looks_like_laughter(text: str) -> bool:
    """Смех с кривой раскладкой: АХХАХПХАХА и т.п."""
    cleaned = re.sub(r"[\s!.?,]+", "", (text or "").strip())
    if len(cleaned) < 4:
        return False
    if LAUGHTER_RE.match((text or "").strip()):
        return True
    ha = sum(1 for c in cleaned.lower() if c in "аххpхa")
    return ha / len(cleaned) >= 0.55


def match_write_word_reply(text: str) -> str | None:
    """«напиши мамонт» без кавычек."""
    match = WRITE_WORD_RE.match((text or "").strip())
    if not match:
        return None
    phrase = match.group(1).strip()
    if not phrase or len(phrase) > 40:
        return None
    return smart_troll_reply(phrase)


def with_first_hint(text: str, *, first_contact: bool, already_greeted: bool = False) -> str:
    if not first_contact or already_greeted or "оператор" in text.lower():
        return text
    return text + OPERATOR_FIRST_HINT


def match_canned(text: str, *, already_greeted: bool = False) -> str | None:
    cleaned = (text or "").strip()
    if not cleaned:
        return None

    # Разговор и сложные вопросы — отдаём LLM, он думает сам
    if needs_llm_thinking(cleaned):
        return None

    # VPN: инструкции и проблемы — мгновенно
    if NOT_WORKING_RE.search(cleaned):
        return NOT_WORKING_REPLY
    if PRICE_RE.search(cleaned):
        return PRICE_REPLY
    if SUBSCRIPTION_RE.search(cleaned):
        return CONNECT_REPLY

    banter = match_banter(cleaned)
    if banter:
        return banter

    slang = match_slang_lexicon(cleaned)
    if slang:
        return slang

    if _is_greeting(cleaned):
        return GREETING_AGAIN_REPLY if already_greeted else GREETING_REPLY

    if CASUAL_RE.match(cleaned):
        return GREETING_AGAIN_REPLY if already_greeted else CASUAL_REPLY

    if SLANG_WHAT_RE.match(cleaned):
        return SLANG_WHAT_REPLY

    if SLANG_HEAR_RE.match(cleaned):
        return SLANG_HEAR_REPLY

    if SLANG_ACK_RE.match(cleaned):
        return SLANG_ACK_REPLY

    if SLANG_FRUST_RE.match(cleaned):
        return SLANG_FRUST_REPLY

    if looks_like_laughter(cleaned):
        return LAUGHTER_REPLY

    write_word = match_write_word_reply(cleaned)
    if write_word:
        return write_word

    if BANTER_RE.search(cleaned):
        return BANTER_REPLY

    if AFFECTION_RE.search(cleaned):
        return AFFECTION_REPLY

    if FAREWELL_RE.search(cleaned):
        return FAREWELL_REPLY

    if COMPLIMENT_RE.search(cleaned):
        return COMPLIMENT_REPLY

    if ACK_RE.match(cleaned):
        return ACK_REPLY

    # Короткий small talk без других тем
    if len(cleaned) < 30 and SMALL_TALK_RE.search(cleaned):
        return SMALL_TALK_REPLY

    if SERVICE_INFO_RE.search(cleaned) and len(cleaned) < 40:
        return SERVICE_INFO_REPLY

    if TELL_ABOUT_RE.search(cleaned) and len(cleaned) < 40:
        return SERVICE_INFO_REPLY

    return None
