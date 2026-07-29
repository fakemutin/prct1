"""DeepSeek client with Satka support prompt."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from openai import OpenAI

from config import Settings
from prompts import SYSTEM_PROMPT, build_user_context

logger = logging.getLogger(__name__)

META_RE = re.compile(r"SATKA_META:\s*(\{.*?\})\s*$", re.DOTALL | re.MULTILINE)


@dataclass
class AiReply:
    text: str
    escalate: bool
    confidence: str
    raw: str


def _parse_meta(raw: str) -> tuple[str, bool, str]:
    match = META_RE.search(raw)
    if not match:
        return raw.strip(), False, "medium"

    visible = META_RE.sub("", raw).strip()
    try:
        meta = json.loads(match.group(1))
    except json.JSONDecodeError:
        return visible, False, "medium"

    escalate = bool(meta.get("escalate"))
    confidence = str(meta.get("confidence", "medium")).lower()
    if confidence not in {"high", "medium", "low"}:
        confidence = "medium"
    return visible, escalate, confidence


class DeepSeekSupportClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )

    def _messages(
        self,
        history: list[dict[str, str]],
        user_message: str,
        user_ctx: str,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        for turn in history[-self._settings.max_history_turns :]:
            role = "user" if turn["role"] == "user" else "assistant"
            messages.append({"role": role, "content": turn["text"]})
        messages.append({"role": "user", "content": f"{user_ctx}\n\n{user_message}"})
        return messages

    def reply(
        self,
        user_message: str,
        *,
        history: list[dict[str, str]],
        username: str | None,
        user_id: int,
        display_name: str | None,
    ) -> AiReply:
        user_ctx = build_user_context(username, user_id, display_name)

        try:
            response = self._client.chat.completions.create(
                model=self._settings.deepseek_model,
                messages=self._messages(history, user_message, user_ctx),
                temperature=0.35,
                top_p=0.9,
                max_tokens=900,
            )
            raw = (response.choices[0].message.content or "").strip()
        except Exception as exc:
            logger.exception("DeepSeek API error")
            return AiReply(
                text=(
                    "Сейчас не могу обработать запрос — техсбой на стороне ассистента. "
                    "Напишите **Оператор**, и мы подключим живую поддержку."
                ),
                escalate=True,
                confidence="low",
                raw=str(exc),
            )

        if not raw:
            return AiReply(
                text="Не получилось сформировать ответ. Напишите **Оператор** — передам специалисту.",
                escalate=True,
                confidence="low",
                raw="",
            )

        text, escalate, confidence = _parse_meta(raw)
        return AiReply(text=text, escalate=escalate, confidence=confidence, raw=raw)


OPERATOR_TRIGGERS = re.compile(
    r"(^|\s)(оператор|operator|живой\s+человек|живой\s+оператор|менеджер|человек|support\s+human)(\s|$|[!.?,])",
    re.IGNORECASE,
)


def user_requests_operator(message: str) -> bool:
    return bool(OPERATOR_TRIGGERS.search(message.strip()))
