import re
from urllib.parse import quote

# TMDB: мультфильмы, документальное, реалити
EXCLUDED_GENRE_IDS: frozenset[int] = frozenset({16, 99, 10764})

CYRILLIC_RE = re.compile(r"[а-яА-ЯёЁ]")


def excluded_genres_param() -> str:
    return ",".join(str(genre_id) for genre_id in sorted(EXCLUDED_GENRE_IDS))


def collect_genre_ids(item: dict, details: dict | None = None) -> set[int]:
    ids = set(item.get("genre_ids") or [])
    if details:
        ids.update(genre.get("id") for genre in details.get("genres", []) if genre.get("id"))
    return ids


def has_excluded_genre(item: dict, details: dict | None = None) -> bool:
    return bool(collect_genre_ids(item, details) & EXCLUDED_GENRE_IDS)


def filter_excluded_genres(items: list[dict]) -> list[dict]:
    return [item for item in items if not has_excluded_genre(item)]


def contains_russian(text: str | None) -> bool:
    return bool(text and CYRILLIC_RE.search(text))


def has_russian_overview(item: dict, details: dict) -> bool:
    overview = (details.get("overview") or item.get("overview") or "").strip()
    return contains_russian(overview)


def build_kinopoisk_url(title: str, year: str) -> str:
    query = title if year == "—" else f"{title} {year}"
    return f"https://www.kinopoisk.ru/index.php?kp_query={quote(query)}"
