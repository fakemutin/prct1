"""Gemini Flash client with Satka support prompt."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types

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


class GeminiSupportClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = genai.Client(api_key=settings.gemini_api_key)

    def _contents(self, history: list[dict[str, str]], user_message: str, user_ctx: str) -> list[types.Content]:
        contents: list[types.Content] = []
        for turn in history[-self._settings.max_history_turns :]:
            role = "user" if turn["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=turn["text"])]))
        contents.append(types.Content(role="user", parts=[types.Part(text=f"{user_ctx}\n\n{user_message}")]))
        return contents

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
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.35,
            top_p=0.9,
            max_output_tokens=900,
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_ONLY_HIGH"),
            ],
        )

        try:
            response = self._client.models.generate_content(
                model=self._settings.gemini_model,
                contents=self._contents(history, user_message, user_ctx),
                config=config,
            )
            raw = (response.text or "").strip()
        except Exception as exc:
            logger.exception("Gemini API error")
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
