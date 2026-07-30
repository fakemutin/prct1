"""Маршрутизация: когда думать (LLM), когда отвечать мгновенно (шаблон)."""

from __future__ import annotations

import re

# Разговор, болтовня, сложные вопросы — только LLM
CONVERSATIONAL_RE = re.compile(
    r"("
    r"поболта|поговор|пообщ|поболтать|поговорить|пообщаться|"
    r"хочу\s+с\s+тобой|хочу\s+поговор|хочу\s+поболт|"
    r"расскаж|рассказ|о\s+чем\s+дума|что\s+думаешь|"
    r"как\s+жизнь|как\s+дела\s+у\s+тебя|"
    r"чем\s+(он\s+)?лучше|почему\s+(вы|вас|satka|сатк)|"
    r"чем\s+отлича|преимущества|"
    r"не\s+понимаешь|ты\s+меня\s+не|или\s+че|или\s+чё|"
    r"че\s+у\s+меня|у\s+меня\s+че|че\s+такое|"
    r"че\s+говори|чё\s+говори|"
    r"о\s+сатк|о\s+сервис|про\s+сатк|про\s+сервис|"
    r"что\s+такое\s+satka|что\s+за\s+vpn|"
    r"интересно\s+узнать|посоветуй|порекомендуй|"
    r"объясни|разъясни|подробнее|поподробнее|"
    r"кабинет|подписк|сайт|функци|возможност|"
    r"дорог|дешев|почему\s+так|обман|"
    r"глушилк|белые\s+списк|"
    r"какие\s+лимит|лимит"
    r")",
    re.IGNORECASE,
)

# Только явные запросы цены — шаблон
EXPLICIT_PRICE_RE = re.compile(
    r"(сколько\s+стоит|цена\s+на|цены\s+на|прайс|стоимость|сколько\s+денег|почём\s)",
    re.IGNORECASE,
)

# Только явная поломка — шаблон (не факты про глушилки)
EXPLICIT_BROKEN_RE = re.compile(
    r"(не\s+работ|не\s+подключ|не\s+включ|не\s+груз|не\s+открыв|"
    r"не\s+фурычит|не\s+пашет|не\s+коннект|"
    r"ошибк|timed?\s*out|timeout|таймаут|отвал|висит|"
    r"502|gateway|gate\s*away|отьебн|нихуя\s+не)",
    re.IGNORECASE,
)

EXPLICIT_CONNECT_RE = re.compile(
    r"(как\s+(подключ|оформ|куп|получ)\w*\s+подписк|"
    r"инструкц|науч\w*\s+подключ)",
    re.IGNORECASE,
)

_GLUSHILKI_DISCUSSION_RE = re.compile(
    r"глушилк|белые\s+списк|бс\s",
    re.IGNORECASE,
)

_OPINION_RE = re.compile(
    r"дорог|дешев|обман|развод|почему\s+так",
    re.IGNORECASE,
)

_EMBEDDED_TROLL_RE = re.compile(
    r"для\s+(?:этого|помощи).{0,60}напиш\w*",
    re.IGNORECASE,
)

_EXPLICIT_TROLL_START_RE = re.compile(
    r"^(?:напиш\w*|скаж\w*|повтор\w*)\s+",
    re.IGNORECASE,
)


def _is_explicit_troll_only(text: str) -> bool:
    if re.search(
        r"(?:расскаж|поболта|поговор|чем\s+лучше|о\s+чем\s+дума|икай)",
        text,
        re.I,
    ):
        return False
    if _EMBEDDED_TROLL_RE.search(text):
        return True
    if _EXPLICIT_TROLL_START_RE.match(text) and len(text) < 100:
        return True
    return False


def needs_llm_thinking(text: str) -> bool:
    """Сообщение требует осмысленного ответа от LLM, не шаблона."""
    cleaned = (text or "").strip()
    if not cleaned or cleaned == "[стикер]":
        return False

    if _is_explicit_troll_only(cleaned):
        return False

    if CONVERSATIONAL_RE.search(cleaned):
        return True

    # Мнение о цене — LLM, не прайс-шаблон
    if _OPINION_RE.search(cleaned) and re.search(r"тариф|цен|дорог|подписк", cleaned, re.I):
        return True

    # Обсуждение глушилок (не поломка) — LLM
    if _GLUSHILKI_DISCUSSION_RE.search(cleaned) and not EXPLICIT_BROKEN_RE.search(cleaned):
        return True

    # Явная поломка без обсуждения — можно шаблон
    if EXPLICIT_BROKEN_RE.search(cleaned) and not CONVERSATIONAL_RE.search(cleaned):
        return False

    if EXPLICIT_PRICE_RE.search(cleaned) and not _OPINION_RE.search(cleaned):
        return False

    if EXPLICIT_CONNECT_RE.search(cleaned) and not CONVERSATIONAL_RE.search(cleaned):
        return False

    if len(cleaned) > 40:
        return True

    if cleaned.count("?") >= 1 and len(cleaned) > 20:
        return True
    if cleaned.count(",") >= 2:
        return True
    if len(re.findall(r"\s+и\s+", cleaned, re.I)) >= 2 and len(cleaned) > 25:
        return True

    if re.search(r"как\s+дела", cleaned, re.I) and len(cleaned) > 15:
        return True
    if re.search(r"расскаж", cleaned, re.I):
        return True
    if re.search(r"тупой|дебил|идиот|быдл|долбо|ты\s+че|ты\s+чё", cleaned, re.I):
        return True
    if re.search(r"икай|не\s+неси|не\s+гони|не\s+беси|заткнись", cleaned, re.I):
        return True
    if re.search(r"^(че|чё|ну)\s+говори|^(ну\s+и|и\s+что)\s*\??$", cleaned, re.I):
        return True

    return False


def force_llm_from_history(history: list[dict[str, str]], text: str) -> bool:
    """После начала диалога — почти всё в LLM, кроме явной поломки."""
    if not history:
        return False

    cleaned = (text or "").strip()
    if not cleaned:
        return False

    # Явная поломка без обсуждения тарифов/глушилок — можно шаблон
    if (
        EXPLICIT_BROKEN_RE.search(cleaned)
        and not _GLUSHILKI_DISCUSSION_RE.search(cleaned)
        and not _OPINION_RE.search(cleaned)
        and not CONVERSATIONAL_RE.search(cleaned)
        and len(cleaned) < 60
    ):
        return False

    # Любой продолжающийся диалог — LLM
    if len(history) >= 2:
        return True

    recent_user = " ".join(
        t["text"].lower() for t in history[-4:] if t.get("role") == "user"
    )
    triggers = (
        "расскаж", "поболта", "тупой", "впн", "vpn", "сатк", "тариф",
        "дорог", "глушилк", "кабинет", "подписк", "лимит",
    )
    if any(k in recent_user for k in triggers):
        return len(cleaned) < 80

    return False


def allow_instant_canned(text: str, *, in_active_chat: bool) -> bool:
    """Можно ли вообще использовать шаблонный ответ."""
    if in_active_chat:
        return False
    cleaned = (text or "").strip()
    if needs_llm_thinking(cleaned):
        return False
    # Только короткие однозначные запросы
    if EXPLICIT_BROKEN_RE.search(cleaned) and len(cleaned) < 80:
        return True
    if EXPLICIT_PRICE_RE.search(cleaned) and len(cleaned) < 50:
        return True
    if EXPLICIT_CONNECT_RE.search(cleaned) and len(cleaned) < 60:
        return True
    if len(cleaned) < 25:
        return True
    return False
