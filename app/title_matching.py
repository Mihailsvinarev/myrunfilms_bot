from __future__ import annotations

import re


def normalize_title(value: str) -> str:
    cleaned = value.lower().strip()
    cleaned = re.sub(r"[«»\"'„“]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def title_matches(query: str, title: str, alternative_title: str | None = None) -> bool:
    normalized_query = normalize_title(query)
    if not normalized_query:
        return False

    for candidate in (title, alternative_title):
        if not candidate:
            continue
        if normalize_title(candidate) == normalized_query:
            return True

    return False
