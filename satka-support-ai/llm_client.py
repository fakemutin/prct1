"""OpenAI-compatible LLM client for Satka support."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from openai import APIStatusError, OpenAI

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
    api_error: bool = False


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


def _user_facing_error(exc: Exception) -> str:
    if isinstance(exc, APIStatusError):
        if exc.status_code in {402, 403}:
            return (
                "Сейчас ассистент на паузе — оператор скоро ответит лично. "
                "Если срочно, напишите «Оператор»."
            )
        if exc.status_code == 429:
            return "Много обращений сейчас — подождите минуту и напишите снова."
    return (
        "Не удалось обработать сообщение автоматически. "
        "Напишите «Оператор» — подключим специалиста."
    )


class LlmSupportClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=60.0,
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
                model=self._settings.llm_model,
                messages=self._messages(history, user_message, user_ctx),
                temperature=0.4,
                top_p=0.9,
                max_tokens=700,
            )
            raw = (response.choices[0].message.content or "").strip()
        except APIStatusError as exc:
            logger.error("LLM API %s: %s", exc.status_code, exc.message)
            return AiReply(
                text=_user_facing_error(exc),
                escalate=False,
                confidence="low",
                raw=str(exc),
                api_error=True,
            )
        except Exception as exc:
            logger.exception("LLM API error")
            return AiReply(
                text=_user_facing_error(exc),
                escalate=False,
                confidence="low",
                raw=str(exc),
                api_error=True,
            )

        if not raw:
            return AiReply(
                text="Не получилось сформировать ответ. Напишите «Оператор» — передам специалисту.",
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
