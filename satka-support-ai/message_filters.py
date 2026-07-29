"""Pre-LLM message filters for manipulation attempts only."""

from __future__ import annotations

import re
from typing import Literal

FilterResult = Literal["ok", "manipulation"]

MANIPULATION_REPLY = (
    "Я общаюсь только по темам VPN. Не надо меня обманывать и уверять в этом. "
    "Если есть вопрос по Satka VPN — напишите."
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


def classify_message(text: str) -> tuple[FilterResult, str | None]:
    cleaned = (text or "").strip()
    if not cleaned:
        return "ok", None

    if MANIPULATION_RE.search(cleaned):
        return "manipulation", MANIPULATION_REPLY

    return "ok", None
