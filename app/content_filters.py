from __future__ import annotations

import re

from app.models import MovieItem

EXCLUDED_GENRE_NAMES: frozenset[str] = frozenset(
    {
        "мультфильм",
        "документальный",
        "ток-шоу",
        "аниме",
    }
)

CYRILLIC_RE = re.compile(r"[а-яА-ЯёЁ]")


def contains_russian(text: str | None) -> bool:
    return bool(text and CYRILLIC_RE.search(text))


def has_excluded_genre(movie: MovieItem) -> bool:
    lowered = {genre.lower() for genre in movie.genres}
    return bool(lowered & EXCLUDED_GENRE_NAMES)


def filter_movies(movies: list[MovieItem], *, limit: int) -> list[MovieItem]:
    selected: list[MovieItem] = []
    for movie in movies:
        if len(selected) >= limit:
            break
        if has_excluded_genre(movie):
            continue
        if not contains_russian(movie.description):
            continue
        selected.append(movie)
    return selected
