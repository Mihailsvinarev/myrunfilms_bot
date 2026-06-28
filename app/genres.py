from __future__ import annotations

from dataclasses import dataclass

GENRE_ANY_ID = "any"
COLLECTION_CALLBACK_PREFIX = "collection:"
COLLECTION_GENRE_CALLBACK_PREFIX = "collection_genre:"


@dataclass(frozen=True, slots=True)
class GenreOption:
    id: str
    title: str
    kinopoisk_value: str | None = None


GENRES: tuple[GenreOption, ...] = (
    GenreOption(GENRE_ANY_ID, "🎭 Любой жанр", None),
    GenreOption("detective", "🕵️ Детектив", "детектив"),
    GenreOption("comedy", "😂 Комедия", "комедия"),
    GenreOption("horror", "😱 Ужасы", "ужасы"),
    GenreOption("scifi", "🚀 Фантастика", "фантастика"),
    GenreOption("melodrama", "❤️ Мелодрама", "мелодрама"),
    GenreOption("drama", "🎬 Драма", "драма"),
    GenreOption("action", "⚔️ Боевик", "боевик"),
    GenreOption("fantasy", "🧙 Фэнтези", "фэнтези"),
    GenreOption("family", "👨‍👩‍👧‍👦 Семейный", "семейный"),
)

FILTER_EXTRA_GENRES: tuple[GenreOption, ...] = (
    GenreOption("thriller", "🔪 Триллер", "триллер"),
)

PARSER_GENRE_ALIASES: dict[str, list[str]] = {
    "криминал": ["криминал"],
    "триллер": ["триллер"],
    "ужас": ["ужасы"],
    "хоррор": ["ужасы"],
    "комед": ["комедия"],
    "драм": ["драма"],
    "фантаст": ["фантастика"],
    "мелодрам": ["мелодрама"],
    "романт": ["мелодрама"],
    "аним": ["мультфильм"],
    "документал": ["документальный"],
    "истор": ["история"],
    "приключ": ["приключения"],
    "семейн": ["семейный"],
    "военн": ["военный"],
    "вестерн": ["вестern"],
}

_GENRES_BY_ID: dict[str, GenreOption] = {genre.id: genre for genre in GENRES}


def get_genre(genre_id: str) -> GenreOption | None:
    return _GENRES_BY_ID.get(genre_id)


def collection_genres() -> tuple[GenreOption, ...]:
    return GENRES


def filter_genres() -> tuple[GenreOption, ...]:
    selectable = tuple(genre for genre in GENRES if genre.id != GENRE_ANY_ID)
    return selectable + FILTER_EXTRA_GENRES


def build_parser_genre_keywords() -> dict[str, list[str]]:
    keywords: dict[str, list[str]] = {}
    for genre in filter_genres():
        if genre.kinopoisk_value:
            keywords[genre.kinopoisk_value] = [genre.kinopoisk_value]
    keywords.update(PARSER_GENRE_ALIASES)
    return keywords


PARSER_GENRE_KEYWORDS = build_parser_genre_keywords()


def build_collection_callback(collection_id: str) -> str:
    return f"{COLLECTION_CALLBACK_PREFIX}{collection_id}"


def build_collection_genre_callback(collection_id: str, genre_id: str) -> str:
    return f"{COLLECTION_GENRE_CALLBACK_PREFIX}{collection_id}:{genre_id}"


def parse_collection_callback(data: str) -> str | None:
    if not data.startswith(COLLECTION_CALLBACK_PREFIX):
        return None
    collection_id = data.removeprefix(COLLECTION_CALLBACK_PREFIX).strip()
    return collection_id or None


def parse_collection_genre_callback(data: str) -> tuple[str, str] | None:
    if not data.startswith(COLLECTION_GENRE_CALLBACK_PREFIX):
        return None
    payload = data.removeprefix(COLLECTION_GENRE_CALLBACK_PREFIX)
    if ":" not in payload:
        return None
    collection_id, genre_id = payload.split(":", 1)
    if not collection_id or not genre_id:
        return None
    return collection_id, genre_id
