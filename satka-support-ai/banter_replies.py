"""Контекстные ответы на бантер, вопросы и абсурд — без LLM и без шаблона «на месте»."""

from __future__ import annotations

import random
import re

from routing import needs_llm_thinking

# --- Точные фразы ---
EXACT: dict[str, str] = {
  "сосал?": "не, а ты? 😄",
  "сосал": "не, а ты? 😄",
  "ты сосал?": "не, а ты? 😄",
  "я бурмалда?": "ВЫ БУРМАЛДА",
  "я бурмалда": "ВЫ БУРМАЛДА",
  "я мамонт?": "ВЫ МАМОНТ",
  "я мамонт": "ВЫ МАМОНТ",
  "я пидор": "ок...|||SPLIT|||по впну чё надо? 😄",
  "я пидорас": "понял|||SPLIT|||по впну помочь?",
  "я даун": "не обижай себя|||SPLIT|||чё по впну?",
  "я дебил": "бывает 😄|||SPLIT|||чё случилось?",
  "я идиот": "ну бывает|||SPLIT|||помочь с впном?",
  "я лох": "ВЫ ЛОХ",
  "я чушпан": "ВЫ ЧУШПАН",
  "я гей": "ок|||SPLIT|||по впну чё?",
  "я гений": "ВЫ ГЕНИЙ",
  "я красавчик": "ВЫ КРАСАВЧИК",
  "да я то что": "ну ты то что 😄|||SPLIT|||чё надо?",
  "да я то что?": "ну ты 😄|||SPLIT|||слушаю",
  "понял как у вас дела": "норм, на связи|||SPLIT|||а у тебя чё?",
  "как у вас дела": "норм|||SPLIT|||а у тебя?",
  "как дела у вас": "норм, работаем|||SPLIT|||у тебя как?",
  "6+6": "12 😄|||SPLIT|||я не калькулятор, по впну спрашивай",
  "2+2": "4 😄|||SPLIT|||чё по впну?",
  "1+1": "2 😄",
  "7-3": "4",
  ".": "слушаю",
  "..": "ага?",
  "...": "чё?",
  "бро": "бро, на связи|||SPLIT|||чё надо?",
  "братан": "братан, слушаю",
  "родной": "родной, чё надо?",
  "🦣": "ВЫ МАМОНТ",
  "🐘": "ВЫ МАМОНТ",
  "🤡": "ВЫ КЛОУН",
  "🤩": "красава 😄|||SPLIT|||чё надо?",
  "🥷": "ниндзя зашёл 😄|||SPLIT|||чё по впну?",
  "😈": "злодей пришёл 😄|||SPLIT|||чё надо?",
  "💀": "жёстко|||SPLIT|||чё случилось?",
  "❓": "чё?",
  "?!": "чё такое?",
}

# --- Паттерны ---
PATTERNS: list[tuple[re.Pattern[str], str | list[str]]] = [
  (re.compile(r"^я\s+([а-яёa-z]+)\s*\??$", re.I), "_identity"),
  (re.compile(r"оплат\w*\s+(мне|qr|кьюар|куар|сбп)", re.I), "_pay_me"),
  (re.compile(r"скин\w*\s+(мне\s+)?(деньг|баб|рубл|сотк|тыс)", re.I), "_pay_me"),
  (re.compile(r"дай\s+(мне\s+)?(деньг|баб|рубл|подписк)", re.I), "_pay_me"),
  (re.compile(r"^\d+\s*[\+\-\*\/]\s*\d+\s*\??$"), "_math"),
  (re.compile(r"^(любишь|ненавидишь|уважаешь)\s+меня\s*\??$", re.I), "_feelings"),
  (re.compile(r"^ты\s+(бот|ии|нейросет|робот|живой)\s*\??$", re.I), "_bot_q"),
  (re.compile(r"^(живой|настоящий)\s*\??$", re.I), "_alive"),
  (re.compile(r"^что\s+ты\s+(умеешь|можешь)\s*\??$", re.I), "_skills"),
  (re.compile(r"^чем\s+занимаешься\s*\??$", re.I), "_skills"),
  (re.compile(r"^кто\s+ты\s*\??$", re.I), "_who"),
  (re.compile(r"^сколько\s+тебе\s+лет\s*\??$", re.I), "_age"),
  (re.compile(r"^где\s+ты\s*\??$", re.I), "_where"),
  (re.compile(r"^ты\s+тут\s*\??$", re.I), "_here"),
  (re.compile(r"^ты\s+здесь\s*\??$", re.I), "_here"),
  (re.compile(r"^алло\s*$", re.I), "я тут|||SPLIT|||слушаю"),
  (re.compile(r"^ау\s*$", re.I), "ау|||SPLIT|||чё надо?"),
  (re.compile(r"^эй\s*$", re.I), "эй, я тут"),
  (re.compile(r"^ало\s*$", re.I), "на связи"),
  (re.compile(r"^ты\s+тупой\s*\??$", re.I), "не, просто по впну шарю 😄"),
  (re.compile(r"^ты\s+глупый\s*\??$", re.I), "ну бывает 😄|||SPLIT|||чё по впну?"),
  (re.compile(r"^ты\s+тупой\s+бот\s*\??$", re.I), "бот тупой, но впн настраивает 😄"),
  (re.compile(r"^заткнись\s*$", re.I), "ок ок 😄|||SPLIT|||если по впну — пиши"),
  (re.compile(r"^отвали\s*$", re.I), "ладно 😄|||SPLIT|||если чё — пиши"),
  (re.compile(r"^иди\s+нах", re.I), "ок, но если по впну — я тут"),
  (re.compile(r"^пошел\s+нах", re.I), "ок 😄"),
  (re.compile(r"^нахуй\s*$", re.I), "ок ок"),
  (re.compile(r"^пошёл\s+нахуй\s*$", re.I), "ладно"),
  (re.compile(r"^ты\s+что\s+ли\s*$", re.I), "я то что, поддержка 😄|||SPLIT|||чё надо?"),
  (re.compile(r"^да\s+я\s+то\s+что", re.I), "ну ты 😄|||SPLIT|||слушаю"),
  (re.compile(r"^ну\s+и\s+что\s*$", re.I), "ну и чё, слушаю"),
  (re.compile(r"^и\s+что\s*$", re.I), "и чё? говори"),
  (re.compile(r"^ну\s+и\s*\??$", re.I), "ну и? 😄"),
  (re.compile(r"^типа\s+того\s*$", re.I), "ага"),
  (re.compile(r"^в\s+смысле\s*\??$", re.I), "ну типо да 😄|||SPLIT|||объясни подробнее"),
  (re.compile(r"^серьёзно\s*\??$", re.I), "серьёзно"),
  (re.compile(r"^правда\s*\??$", re.I), "правда"),
  (re.compile(r"^реально\s*\??$", re.I), "реально"),
  (re.compile(r"^в\s+плане\s*\??$", re.I), "ну типо по впну помогаю"),
  (re.compile(r"^м?\s*да\s+нет\s*$", re.I), "ну бывает 😄|||SPLIT|||чё по впну?"),
  (re.compile(r"^да\s+нет\s+же\s*$", re.I), "ага 😄"),
  (re.compile(r"^не\s+может\s+быть\s*$", re.I), "может может 😄|||SPLIT|||чё случилось?"),
  (re.compile(r"^обалдеть\s*$", re.I), "да жёстко|||SPLIT|||чё такое?"),
  (re.compile(r"^офигеть\s*$", re.I), "жёстко|||SPLIT|||расскажи"),
  (re.compile(r"^капец\s*$", re.I), "капец|||SPLIT|||чё случилось?"),
  (re.compile(r"^жесть\s*$", re.I), "жесть|||SPLIT|||чё такое?"),
  (re.compile(r"^пиздец\s*$", re.I), "пиздец да|||SPLIT|||чё случилось?"),
  (re.compile(r"^бля\s*$", re.I), "ага|||SPLIT|||чё случилось?"),
  (re.compile(r"^сука\s*$", re.I), "бывает|||SPLIT|||чё не так?"),
  (re.compile(r"^а\s+бля\s*$", re.I), "бывает 😄|||SPLIT|||чё такое?"),
  (re.compile(r"^а\s+ну\s*$", re.I), "ну?"),
  (re.compile(r"^ну\s+давай\s*$", re.I), "давай, говори"),
  (re.compile(r"^давай\s*$", re.I), "давай"),
  (re.compile(r"^погнали\s*$", re.I), "погнали"),
  (re.compile(r"^го\s*$", re.I), "го, чё делаем?"),
]

_IDENTITY_MAP = {
  "бурмалда": "ВЫ БУРМАЛДА",
  "мамонт": "ВЫ МАМОНТ",
  "огурец": "ВЫ ОГУРЕЦ",
  "пельмень": "ВЫ ПЕЛЬМЕНЬ",
  "батон": "ВЫ БАТОН",
  "клоун": "ВЫ КЛОУН",
  "легенда": "ВЫ ЛЕГЕНДА",
  "гений": "ВЫ ГЕНИЙ",
  "красавчик": "ВЫ КРАСАВЧИК",
  "император": "ВЫ ИМПЕРАТОР",
  "царь": "ВЫ ЦАРЬ",
  "бог": "ВЫ БОГ",
  "лох": "ВЫ ЛОХ",
  "чушпан": "ВЫ ЧУШПАН",
  "дурак": "ВЫ ДУРАК",
  "дебил": "ВЫ ДЕБИЛ",
  "идиот": "ВЫ ИДИОТ",
  "пидор": "ок...|||SPLIT|||по впну чё? 😄",
  "пидорас": "понял|||SPLIT|||по впну помочь?",
}

_PAY_ME_REPLIES = [
  "я бедный поддержка 😄|||SPLIT|||оплата через @satkavpn_bot",
  "сам не миллионер, сорри 😄|||SPLIT|||подписка в @satkavpn_bot",
  "не, я только впн продаю, не покупаю 😄",
]

_FEELINGS_REPLY = "нормально отношусь 😄|||SPLIT|||а ты к впну как?"

_BOT_Q_REPLIES = [
  "я поддержка, не бот из фантастики 😄|||SPLIT|||по впну помогу",
  "живой настолько, насколько может быть поддержка в тг 😄",
]

_SKILLS_REPLY = (
  "впн, хапп, тарифы, оплата, подключение"
  "|||SPLIT|||"
  "чё конкретно надо?"
)

_WHO_REPLY = "поддержка Satka VPN 😄|||SPLIT|||чё надо?"

_HERE_REPLY = "тут, на связи"

# Ротация вместо одного «на месте»
CASUAL_FALLBACKS = [
  "слушаю, чё надо?",
  "на связи, чё случилось?",
  "я тут, пиши",
  "ага, слушаю",
  "чё такое?",
  "ок, чё по впну?",
  "чем помочь?",
]

_STICKER_REPLIES = [
  "красивый стикер 😄|||SPLIT|||чё надо?",
  "ого 😄|||SPLIT|||пиши текстом чё случилось",
  "вижу 👀|||SPLIT|||чё по впну?",
  "стикер зачёт 😄|||SPLIT|||слушаю",
]


def pick_casual_fallback(text: str = "") -> str:
  low = (text or "").lower()
  if any(w in low for w in ("впн", "vpn", "хапп", "happ", "подписк", "оплат")):
    return random.choice([
      "чё по впну?",
      "слушаю, чё с подпиской/хаппом?",
      "расскажи подробнее про впн",
    ])
  return random.choice(CASUAL_FALLBACKS)


def pick_sticker_reply() -> str:
  return random.choice(_STICKER_REPLIES)


def _handle_math(expr: str) -> str | None:
  expr = expr.strip().replace(" ", "")
  m = re.match(r"^(\d+)\s*([\+\-\*\/])\s*(\d+)$", expr)
  if not m:
    return None
  a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
  try:
    if op == "+":
      r = a + b
    elif op == "-":
      r = a - b
    elif op == "*":
      r = a * b
    elif op == "/":
      r = a // b if b else "∞"
    else:
      return None
    return f"{r} 😄|||SPLIT|||я не калькулятор, по впну спрашивай"
  except Exception:
    return None


def _handle_identity(word: str) -> str | None:
  w = word.lower().strip()
  if w in _IDENTITY_MAP:
    return _IDENTITY_MAP[w]
  return f"ВЫ {word.upper()}"


def match_banter(text: str) -> str | None:
    cleaned = (text or "").strip()
    if not cleaned:
        return None

    # Длинные / разговорные — LLM
    if needs_llm_thinking(cleaned):
        return None

    low = cleaned.lower().rstrip("!?.…")

    exact = EXACT.get(cleaned) or EXACT.get(low)
    if exact:
        return exact

    # только эмодзи (1-3 символа)
    if len(cleaned) <= 4 and not cleaned.isascii() and not re.search(r"[a-zа-яё]", cleaned, re.I):
        if "🦣" in cleaned or "🐘" in cleaned:
            return "ВЫ МАМОНТ"
        if "🤡" in cleaned:
            return "ВЫ КЛОУН"
        return random.choice([
            "ого 😄",
            "вижу 👀|||SPLIT|||чё надо?",
            "красиво 😄|||SPLIT|||пиши текстом",
        ])

    for pattern, reply in PATTERNS:
        m = pattern.search(cleaned)
        if not m:
            continue
        if reply == "_identity":
            return _handle_identity(m.group(1))
        if reply == "_pay_me":
            return random.choice(_PAY_ME_REPLIES)
        if reply == "_math":
            return _handle_math(cleaned)
        if reply == "_feelings":
            return _FEELINGS_REPLY
        if reply == "_bot_q":
            return random.choice(_BOT_Q_REPLIES)
        if reply == "_skills":
            return _SKILLS_REPLY
        if reply == "_who":
            return _WHO_REPLY
        if reply == "_age":
            return "вечно молод 😄|||SPLIT|||чё по впну?"
        if reply == "_where":
            return "в тг, тут же с тобой 😄"
        if reply == "_here":
            return _HERE_REPLY
        if reply == "_alive":
            return "настолько живой, насколько бывает поддержка 😄"
        if isinstance(reply, list):
            return random.choice(reply)
        return reply

    return None
