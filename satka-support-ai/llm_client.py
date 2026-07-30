"""OpenAI-compatible LLM client for Satka support."""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass

from openai import APIStatusError, OpenAI

from banter_replies import pick_casual_fallback
from canned_responses import BUSY_REPLY, match_canned
from config import Settings
from message_filters import CODE_REQUEST_REPLY, WARM_REDIRECT_REPLY
from routing import needs_llm_thinking
from troll_replies import match_troll_reply
from prompts import SYSTEM_PROMPT, build_user_context

logger = logging.getLogger(__name__)

META_RE = re.compile(r"SATKA_META:\s*(\{.*?\})\s*$", re.DOTALL | re.MULTILINE)

CODE_IN_REPLY_RE = re.compile(
    r"(print\s*\(|def\s+\w+\s*\(|```|hello\s*world|import\s+\w+)",
    re.IGNORECASE,
)

GREETING_SPAM_RE = re.compile(r"^(привет|здравствуй|hello|hi)\b", re.IGNORECASE)


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


def _sanitize_reply(text: str, *, has_history: bool) -> str:
    if CODE_IN_REPLY_RE.search(text):
        logger.warning("LLM tried to output code, replacing with code-request reply")
        return CODE_REQUEST_REPLY
    if "Работаем только по Satka VPN" in text:
        return WARM_REDIRECT_REPLY
    if has_history and GREETING_SPAM_RE.search(text.strip()):
        # убрать повторное приветствие — оставить суть
        lines = [ln for ln in text.splitlines() if not GREETING_SPAM_RE.search(ln.strip())]
        cleaned = "\n".join(ln for ln in lines if ln.strip()).strip()
        if cleaned:
            return cleaned
    return text


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


def _rate_limit_fallback(user_message: str) -> str:
    troll = match_troll_reply(user_message)
    if troll:
        return troll
    if needs_llm_thinking(user_message):
        return (
            "ща сек, ассистент подтупливает от нагрузки — напиши через минутку"
            "|||SPLIT|||"
            "или «Оператор» — подключим живого"
        )
    hit = match_canned(user_message)
    if hit:
        return hit
    return pick_casual_fallback(user_message)


class LlmSupportClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=25.0,
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

    def _call_llm(self, messages: list[dict[str, str]]) -> str:
        last_exc: Exception | None = None
        for attempt in range(6):
            try:
                response = self._client.chat.completions.create(
                    model=self._settings.llm_model,
                    messages=messages,
                    temperature=0.65,
                    top_p=0.9,
                    max_tokens=420,
                )
                return (response.choices[0].message.content or "").strip()
            except APIStatusError as exc:
                last_exc = exc
                if exc.status_code == 429 and attempt < 5:
                    time.sleep(min(2 ** attempt + 2, 20))
                    continue
                raise
        raise last_exc  # type: ignore[misc]

    def reply(
        self,
        user_message: str,
        *,
        history: list[dict[str, str]],
        username: str | None,
        user_id: int,
        display_name: str | None,
        has_history: bool = False,
    ) -> AiReply:
        user_ctx = build_user_context(
            username, user_id, display_name, has_history=has_history,
        )
        messages = self._messages(history, user_message, user_ctx)

        try:
            raw = self._call_llm(messages)
            text, escalate, confidence = _parse_meta(raw)
            text = _sanitize_reply(text, has_history=has_history)

        except APIStatusError as exc:
            logger.error("LLM API %s: %s", exc.status_code, exc.message)
            if exc.status_code == 429:
                return AiReply(
                    text=_rate_limit_fallback(user_message),
                    escalate=False,
                    confidence="medium",
                    raw=str(exc),
                    api_error=False,
                )
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

        return AiReply(text=text, escalate=escalate, confidence=confidence, raw=raw)


OPERATOR_TRIGGERS = re.compile(
    r"(^|\s)(оператор|operator|живой\s+человек|живой\s+оператор|менеджер|человек|support\s+human)(\s|$|[!.?,])",
    re.IGNORECASE,
)


def user_requests_operator(message: str) -> bool:
    return bool(OPERATOR_TRIGGERS.search(message.strip()))
