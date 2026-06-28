from __future__ import annotations

TELEGRAM_MESSAGE_LIMIT = 4096
DESCRIPTION_MAX_LENGTH = 350


def truncate_description(text: str, *, max_length: int = DESCRIPTION_MAX_LENGTH) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_length:
        return cleaned
    return cleaned[: max_length - 1].rstrip() + "…"


def split_telegram_message(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current = ""

    for paragraph in text.split("\n\n"):
        block = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(block) <= limit:
            current = block
            continue

        if current:
            chunks.append(current)
            current = ""

        if len(paragraph) <= limit:
            current = paragraph
            continue

        for line in paragraph.split("\n"):
            candidate = line if not current else f"{current}\n{line}"
            if len(candidate) <= limit:
                current = candidate
                continue

            if current:
                chunks.append(current)
                current = ""

            while len(line) > limit:
                chunks.append(line[:limit])
                line = line[limit:]

            if line:
                current = line

    if current:
        chunks.append(current)

    return chunks or [text[:limit]]
