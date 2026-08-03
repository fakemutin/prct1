"""Split replies into several Telegram messages like a real person."""

from __future__ import annotations

import re

SPLIT_MARKER = "|||SPLIT|||"

# Не резать нумерованные инструкции пополам
_NUMBERED_BLOCK_RE = re.compile(r"^\d+\.\s", re.MULTILINE)


def split_reply_parts(text: str, *, max_parts: int = 4) -> list[str]:
    cleaned = (text or "").strip()
    if not cleaned:
        return []

    if SPLIT_MARKER in cleaned:
        parts = [p.strip() for p in cleaned.split(SPLIT_MARKER) if p.strip()]
        return parts[:max_parts]

    if len(cleaned) <= 120:
        return [cleaned]

    # Два абзаца — два сообщения (как в чате)
    if "\n\n" in cleaned and not _NUMBERED_BLOCK_RE.search(cleaned):
        parts = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
        if 2 <= len(parts) <= max_parts:
            return parts[:max_parts]

    # Длинная простыня — режем по одинарным переносам, но не внутри списка
    if len(cleaned) > 220 and "\n" in cleaned:
        lines = cleaned.splitlines()
        chunks: list[str] = []
        buf: list[str] = []
        for line in lines:
            buf.append(line)
            block = "\n".join(buf).strip()
            if len(block) >= 90 and not line.strip().startswith(("•", "-", "1.", "2.", "3.", "4.", "5.")):
                chunks.append(block)
                buf = []
        if buf:
            chunks.append("\n".join(buf).strip())
        if 2 <= len(chunks) <= max_parts:
            return chunks[:max_parts]

    return [cleaned]
