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
    r"объясни|разъясни|подробнее|поподробнее"
    r")",
    re.IGNORECASE,
)

VPN_INSTANT_RE = re.compile(
    r"(не\s+работ|не\s+подключ|не\s+фурычит|не\s+пашет|ошибк|timeout|"
    r"таймаут|502|отвал|отьебн|сколько\s+стоит|цена|тариф|"
    r"как\s+(подключ|оформ|куп|получ)\w*\s+подписк|"
    r"инструкц|науч\w*\s+подключ)",
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
    """«…для этого напиши "мамонт"» — троллинг, не болтовня."""
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

    # VPN-проблемы и инструкции — шаблоны точнее
    if VPN_INSTANT_RE.search(cleaned) and not CONVERSATIONAL_RE.search(cleaned):
        return False

    if CONVERSATIONAL_RE.search(cleaned):
        return True

    if len(cleaned) > 45:
        return True

    # Несколько вопросов / тем
    if cleaned.count("?") >= 1 and len(cleaned) > 25:
        return True
    if cleaned.count(",") >= 2:
        return True
    if len(re.findall(r"\s+и\s+", cleaned, re.I)) >= 2 and len(cleaned) > 30:
        return True

    # «как дела» + ещё что-то в том же сообщении
    if re.search(r"как\s+дела", cleaned, re.I) and len(cleaned) > 20:
        return True
    if re.search(r"расскаж", cleaned, re.I):
        return True
    if re.search(r"тупой|дебил|идиот|быдл|долбо|тупой\s+бот|ты\s+че|ты\s+чё", cleaned, re.I):
        return True
    if re.search(r"икай|не\s+неси|не\s+гони|не\s+беси|заткнись", cleaned, re.I):
        return True
    # Короткая фрустрация после диалога («че говори», «ну и?»)
    if re.search(r"^(че|чё|ну)\s+говори|^(ну\s+и|и\s+что)\s*\??$", cleaned, re.I):
        return True

    return False


def force_llm_from_history(history: list[dict[str, str]], text: str) -> bool:
    """Если уже шла болтовня/провокация — короткий ответ тоже в LLM."""
    if not history:
        return False
    recent_user = " ".join(
        t["text"].lower() for t in history[-6:] if t.get("role") == "user"
    )
    triggers = (
        "расскаж", "поболта", "тупой", "дебил", "икай", "впн", "vpn",
        "сатк", "лучше", "думаешь", "не понима", "быдл",
    )
    if not any(k in recent_user for k in triggers):
        return False
    cleaned = (text or "").strip()
    if len(cleaned) > 90:
        return True
    if re.search(r"говори|ну\s+и|че\s+так|тупой|впн|vpn|сатк|расскаж", cleaned, re.I):
        return True
    return len(cleaned) < 35
