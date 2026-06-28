from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from app.content_filters import (
    EXCLUDED_COUNTRY_NAMES,
    EXCLUDED_GENRE_NAMES,
    is_allowed_movie,
)
from app.genres import GENRE_ANY_ID, GenreOption, get_genre
from app.kinopoisk_client import KinopoiskClient
from app.models import MovieItem

logger = logging.getLogger(__name__)

COLLECTION_RESULT_LIMIT = 20
COLLECTION_MIN_KP_RATING = 6.0
COLLECTION_MAX_PAGES = 5
NEW_RELEASE_PREMIERE_DAYS = 120
EMPTY_COLLECTION_MESSAGE = "По этой подборке и жанру ничего не найдено."

CountryScope = Literal["ru", "foreign", "any"]
PeriodScope = Literal["last_120_days", "any"]
SortMode = Literal["rating", "popularity"]
MediaScope = Literal["movie", "tv"]


@dataclass(frozen=True, slots=True)
class Collection:
    id: str
    title: str
    media_type: MediaScope
    country_scope: CountryScope = "any"
    period: PeriodScope = "any"
    sort_mode: SortMode = "popularity"
    result_limit: int = COLLECTION_RESULT_LIMIT
    random_pick: bool = False


COLLECTIONS: tuple[Collection, ...] = (
    Collection(
        id="new_foreign_movies",
        title="🌍 Новые зарубежные фильмы",
        media_type="movie",
        country_scope="foreign",
        period="last_120_days",
        sort_mode="popularity",
    ),
    Collection(
        id="new_russian_movies",
        title="🇷🇺 Новые российские фильмы",
        media_type="movie",
        country_scope="ru",
        period="last_120_days",
        sort_mode="popularity",
    ),
    Collection(
        id="new_foreign_series",
        title="📺 Новые зарубежные сериалы",
        media_type="tv",
        country_scope="foreign",
        period="last_120_days",
        sort_mode="popularity",
    ),
    Collection(
        id="new_russian_series",
        title="🇷🇺📺 Новые российские сериалы",
        media_type="tv",
        country_scope="ru",
        period="last_120_days",
        sort_mode="popularity",
    ),
    Collection(
        id="most_popular",
        title="🔥 Самые популярные",
        media_type="movie",
        sort_mode="popularity",
    ),
    Collection(
        id="best_rating",
        title="🏆 Лучшие по рейтингу",
        media_type="movie",
        sort_mode="rating",
    ),
    Collection(
        id="random_movie",
        title="🎲 Случайный фильм",
        media_type="movie",
        sort_mode="popularity",
        result_limit=1,
        random_pick=True,
    ),
)

_COLLECTIONS_BY_ID: dict[str, Collection] = {
    collection.id: collection for collection in COLLECTIONS
}


def get_collection(collection_id: str) -> Collection | None:
    return _COLLECTIONS_BY_ID.get(collection_id)


def premiere_range_days(days: int) -> str:
    today = date.today()
    start = today - timedelta(days=days)
    return f"{start.strftime('%d.%m.%Y')}-{today.strftime('%d.%m.%Y')}"


def release_years_for_period(days: int) -> tuple[int, ...]:
    today = date.today()
    start = today - timedelta(days=days)
    return tuple(range(start.year, today.year + 1))


def year_in_release_window(movie: MovieItem, *, days: int) -> bool:
    if movie.year is None:
        return False
    return movie.year in release_years_for_period(days)


def premiere_field_for_scope(country_scope: CountryScope) -> str:
    if country_scope == "ru":
        return "premiere.russia"
    return "premiere.world"


def build_search_params(
    collection: Collection,
    genre: GenreOption | None,
    *,
    page: int = 1,
    include_genre_filter: bool = True,
    search_mode: Literal["premiere", "year"] = "premiere",
) -> list[tuple[str, str | int]]:
    params: list[tuple[str, str | int]] = [
        ("page", page),
        ("limit", 50),
        ("rating.kp", f"{COLLECTION_MIN_KP_RATING:g}-10"),
        ("notNullField", "rating.kp"),
        ("notNullField", "poster.url"),
    ]

    if collection.media_type == "movie":
        params.extend(
            [
                ("isSeries", "false"),
                ("type", "movie"),
                ("typeNumber", 1),
            ]
        )
    else:
        params.append(("isSeries", "true"))

    if collection.country_scope == "ru":
        params.append(("countries.name", "Россия"))
    elif collection.country_scope == "foreign":
        params.append(("countries.name", "!Россия"))

    premiere_field = premiere_field_for_scope(collection.country_scope)
    if collection.period == "last_120_days":
        if search_mode == "premiere":
            params.append((premiere_field, premiere_range_days(NEW_RELEASE_PREMIERE_DAYS)))
        else:
            years = release_years_for_period(NEW_RELEASE_PREMIERE_DAYS)
            if len(years) == 1:
                params.append(("year", years[0]))
            else:
                params.append(("year", f"{years[0]}-{years[-1]}"))

    if include_genre_filter and genre and genre.kinopoisk_value:
        params.append(("genres.name", f"+{genre.kinopoisk_value}"))

    if collection.sort_mode == "rating":
        params.extend([("sortField", "rating.kp"), ("sortType", -1)])
    else:
        params.extend([("sortField", "votes.kp"), ("sortType", -1)])

    if collection.period == "last_120_days" and search_mode == "premiere":
        params.extend([("sortField", premiere_field), ("sortType", -1)])

    for country in sorted(EXCLUDED_COUNTRY_NAMES):
        params.append(("countries.name", f"!{country}"))
    for genre_name in sorted(EXCLUDED_GENRE_NAMES):
        params.append(("genres.name", f"!{genre_name}"))

    return params


def genre_matches(movie: MovieItem, genre: GenreOption) -> bool:
    if not genre.kinopoisk_value:
        return True
    target = genre.kinopoisk_value.lower()
    return any(item.lower() == target for item in movie.genres)


def passes_collection_filters(
    movie: MovieItem,
    collection: Collection,
    genre: GenreOption | None,
) -> bool:
    if collection.media_type == "movie" and movie.is_series:
        return False
    if collection.media_type == "tv" and not movie.is_series:
        return False
    if not is_allowed_movie(movie, require_russian_title=False):
        return False
    if movie.kp_rating is None or movie.kp_rating < COLLECTION_MIN_KP_RATING:
        return False
    if genre and genre.id != GENRE_ANY_ID and not genre_matches(movie, genre):
        return False
    if collection.country_scope == "ru" and "Россия" not in movie.countries:
        return False
    if collection.country_scope == "foreign" and movie.countries == ["Россия"]:
        return False
    return True


async def _fetch_collection_movies(
    client: KinopoiskClient,
    collection: Collection,
    genre: GenreOption,
    *,
    include_genre_filter: bool,
    search_mode: Literal["premiere", "year"] = "premiere",
    seen_ids: set[int] | None = None,
) -> tuple[list[MovieItem], list[MovieItem]]:
    target_limit = collection.result_limit
    selected: list[MovieItem] = []
    pool: list[MovieItem] = []
    known_ids = seen_ids if seen_ids is not None else set()

    for page in range(1, COLLECTION_MAX_PAGES + 1):
        params = build_search_params(
            collection,
            genre,
            page=page,
            include_genre_filter=include_genre_filter,
            search_mode=search_mode,
        )
        movies = await client.fetch_by_params(params)
        if not movies:
            break

        for movie in movies:
            if movie.id in known_ids:
                continue
            known_ids.add(movie.id)
            if not passes_collection_filters(movie, collection, genre):
                continue
            if search_mode == "year" and collection.period == "last_120_days":
                if not year_in_release_window(
                    movie, days=NEW_RELEASE_PREMIERE_DAYS
                ):
                    continue
            if collection.random_pick:
                pool.append(movie)
            else:
                selected.append(movie)
                if len(selected) >= target_limit:
                    break
        if collection.random_pick:
            if pool:
                break
        elif len(selected) >= target_limit:
            break

    return selected, pool


async def _merge_year_fallback(
    client: KinopoiskClient,
    collection: Collection,
    genre: GenreOption,
    *,
    include_genre_filter: bool,
    selected: list[MovieItem],
    seen_ids: set[int],
) -> list[MovieItem]:
    if collection.period != "last_120_days":
        return selected
    if len(selected) >= collection.result_limit:
        return selected

    year_selected, year_pool = await _fetch_collection_movies(
        client,
        collection,
        genre,
        include_genre_filter=include_genre_filter,
        search_mode="year",
        seen_ids=seen_ids,
    )
    if collection.random_pick:
        return selected

    merged = selected + year_selected
    return merged[: collection.result_limit]


async def search_collection(
    client: KinopoiskClient,
    collection_id: str,
    genre_id: str,
) -> list[MovieItem]:
    collection = get_collection(collection_id)
    if collection is None:
        logger.warning("Unknown collection_id=%s", collection_id)
        return []

    genre = get_genre(genre_id)
    if genre is None:
        logger.warning(
            "Unknown genre_id=%s for collection_id=%s", genre_id, collection_id
        )
        return []

    seen_ids: set[int] = set()
    selected, pool = await _fetch_collection_movies(
        client,
        collection,
        genre,
        include_genre_filter=True,
        search_mode="premiere",
        seen_ids=seen_ids,
    )
    if not selected and not pool and genre.id != GENRE_ANY_ID:
        selected, pool = await _fetch_collection_movies(
            client,
            collection,
            genre,
            include_genre_filter=False,
            search_mode="premiere",
            seen_ids=seen_ids,
        )

    if not collection.random_pick:
        selected = await _merge_year_fallback(
            client,
            collection,
            genre,
            include_genre_filter=True,
            selected=selected,
            seen_ids=seen_ids,
        )
        if (
            genre.id != GENRE_ANY_ID
            and len(selected) < collection.result_limit
        ):
            selected = await _merge_year_fallback(
                client,
                collection,
                genre,
                include_genre_filter=False,
                selected=selected,
                seen_ids=seen_ids,
            )

    if collection.random_pick:
        if not pool:
            logger.info(
                "Collection search collection_id=%s genre_id=%s results=0",
                collection_id,
                genre_id,
            )
            return []
        picked = random.choice(pool)
        logger.info(
            "Collection search collection_id=%s genre_id=%s results=1",
            collection_id,
            genre_id,
        )
        return [picked]

    logger.info(
        "Collection search collection_id=%s genre_id=%s results=%d",
        collection_id,
        genre_id,
        len(selected),
    )
    return selected
