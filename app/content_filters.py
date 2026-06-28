from __future__ import annotations

import re

from app.models import MovieItem

EXCLUDED_GENRE_NAMES: frozenset[str] = frozenset(
    {
        "мультфильм",
        "документальный",
        "ток-шоу",
        "аниме",
        "концерт",
        "музыка",
    }
)

EXCLUDED_COUNTRY_NAMES: frozenset[str] = frozenset(
    {
        "Индия",
        "Китай",
    }
)

CYRILLIC_RE = re.compile(r"[а-яА-ЯёЁ]")


def contains_russian(text: str | None) -> bool:
    return bool(text and CYRILLIC_RE.search(text))


def has_excluded_genre(movie: MovieItem) -> bool:
    lowered = {genre.lower() for genre in movie.genres}
    return bool(lowered & EXCLUDED_GENRE_NAMES)


def has_excluded_country(movie: MovieItem) -> bool:
    return bool(set(movie.countries) & EXCLUDED_COUNTRY_NAMES)


def is_allowed_movie(
    movie: MovieItem,
    *,
    require_russian_title: bool = False,
) -> bool:
    if has_excluded_genre(movie):
        return False
    if has_excluded_country(movie):
        return False
    if require_russian_title and not contains_russian(movie.title):
        return False
    return True


def filter_movies(
    movies: list[MovieItem],
    *,
    limit: int,
    require_russian_description: bool = True,
    require_russian_title: bool = True,
) -> list[MovieItem]:
    selected: list[MovieItem] = []
    for movie in movies:
        if len(selected) >= limit:
            break
        if not is_allowed_movie(movie, require_russian_title=require_russian_title):
            continue
        if require_russian_description and not contains_russian(movie.description):
            continue
        selected.append(movie)
    return selected
