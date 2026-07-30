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
    r"^(ку|йоу|йо|yo|сап|здарова|чикаго\s+бро|бро)[\s!.?]*$",
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

_INSULT_WORD_RE = re.compile(
    r"(пидар|пидор|ебан|хуй|сука|мудак|дебил|идиот|говн|урод|мраз|чмо)",
    re.IGNORECASE,
)

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
    r"502|gateway|gate\s*away)",
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
    "Привет! 👋 Рад вас видеть.\n"
    "Я по Satka VPN — подключение, тарифы, Happ, оплата, кабинет. "
    "С чем помочь?"
)

GREETING_AGAIN_REPLY = (
    "На связи 🙂 Чем помочь — подключение, тарифы, Happ или что-то ещё?"
)

CASUAL_REPLY = (
    "Йоу! 🙂 Рад, что написали.\n"
    "Я тут по Satka VPN — если нужна помощь с подключением или тарифами, спрашивайте."
)

CONNECT_REPLY = (
    "Как оформить и подключить подписку:\n"
    "1. @satkavpn_bot → /start → «Подписка» (или бесплатный период 4 дня)\n"
    "2. Оплатить и скопировать ссылку подписки целиком\n"
    "3. Установить Happ → «+» → вставить ссылку\n"
    "4. Обновить список серверов → выбрать локацию → подключить\n\n"
    "Кабинет: node.satkaconnect.xyz\n"
    "На каком шаге нужна помощь?"
)

PRICE_REPLY = (
    "Тарифы Satka VPN (безлимит):\n"
    "• Базовый (1 устр.): от 20 ₽/день, 50 ₽/30 дней\n"
    "• Расширенный (3 устр.): 99 ₽/30 дней\n"
    "• Для мамы (обход глушилок LTE): от 69 ₽/30 дней\n"
    "• Семейный (7 устр.): 145 ₽/30 дней\n"
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
    "Не помогло — напишите устройство (iPhone/Android), Wi‑Fi или LTE, и текст ошибки из Happ."
)

SERVICE_INFO_REPLY = (
    "Satka VPN — сервис с тарифами от 20 ₽/день и бесплатным периодом 4 дня.\n"
    "Подключение через Happ, оплата картой/СБП/Stars/крипто.\n"
    "Бот @satkavpn_bot, кабинет node.satkaconnect.xyz.\n\n"
    "Что интересует — подключение, цена или обход блокировок?"
)

ACK_REPLY = (
    "Рад был помочь! 🙂 Если что-то ещё по Satka VPN — пишите. "
    "Или «Оператор», если нужен живой специалист."
)

SMALL_TALK_REPLY = (
    "Всё хорошо, спасибо что спросили 🙂 На связи и готов помочь.\n"
    "Если по Satka VPN что-то нужно — подключение, тарифы, Happ — спрашивайте."
)

FAREWELL_REPLY = (
    "До связи! Было приятно пообщаться 🙂\n"
    "Если что — мы тут. Хорошего дня!"
)

COMPLIMENT_REPLY = (
    "Спасибо, очень приятно слышать! 🙌\n"
    "Стараемся помогать по-человечески. Если ещё что-то по Satka VPN — я тут."
)

LAUGHTER_REPLY = (
    "😄 Ха-ха, заразили!\n"
    "Если по Satka VPN что-то нужно — я тут."
)

BANTER_REPLY = (
    "Ну я стараюсь 🙂 Если скучно — давайте по делу: "
    "подключение, тарифы, Happ — чем помочь?"
)

AFFECTION_REPLY = (
    "Спасибо, приятно слышать! 🙌\n"
    "Я тут по Satka VPN — если что, пишите."
)

CASUAL_CHAT_REPLY = (
    "Я на связи 🙂 По Satka VPN помогу с чем угодно — "
    "подключение, тарифы, Happ. Или просто спросите, как дела."
)

STICKER_REPLY = (
    "Вижу стикер 🙂 Напишите текстом, чем помочь — или просто поздоровайтесь. "
    "Я по Satka VPN: подключение, тарифы, Happ, оплата."
)

BUSY_REPLY = (
    "Сейчас высокая нагрузка на ассистента. Кратко:\n"
    "• Подписка: @satkavpn_bot → /start → Подписка\n"
    "• Подключение: ссылка из бота → Happ → импорт → обновить → подключить\n"
    "• Проблема: опишите что не работает или напишите «Оператор»"
)

OPERATOR_FIRST_HINT = (
    "\n\nЕсли не смогу помочь — напишите «Оператор», подключим специалиста."
)


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
    """«напиши мамонт» без кавычек → «ВЫ МАМОНТ»."""
    match = WRITE_WORD_RE.match((text or "").strip())
    if not match:
        return None
    phrase = match.group(1).strip()
    if not phrase or len(phrase) > 40:
        return None
    if _INSULT_WORD_RE.search(phrase):
        return None
    if re.match(r"^я\s+", phrase, re.IGNORECASE):
        rest = re.sub(r"^я\s+", "", phrase, flags=re.IGNORECASE).strip()
        return f"ВЫ {rest.upper()}"
    return f"ВЫ {phrase.upper()}"


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

    if CASUAL_RE.match(cleaned):
        return GREETING_AGAIN_REPLY if already_greeted else CASUAL_REPLY

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

    # Подписка/подключение — даже если есть «расскажите» или «как дела»
    if SUBSCRIPTION_RE.search(cleaned):
        if SMALL_TALK_RE.search(cleaned):
            return "Всё отлично, спасибо! 🙂\n\n" + CONNECT_REPLY
        return CONNECT_REPLY

    if NOT_WORKING_RE.search(cleaned):
        return NOT_WORKING_REPLY

    if PRICE_RE.search(cleaned):
        return PRICE_REPLY

    if SMALL_TALK_RE.search(cleaned):
        return SMALL_TALK_REPLY

    if SERVICE_INFO_RE.search(cleaned):
        return SERVICE_INFO_REPLY

    if TELL_ABOUT_RE.search(cleaned) and not SUBSCRIPTION_RE.search(cleaned):
        return SERVICE_INFO_REPLY

    return None
