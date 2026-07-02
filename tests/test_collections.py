from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest

from app.collections import (
    EMPTY_COLLECTION_MESSAGE,
    NEW_RELEASE_PREMIERE_DAYS,
    build_search_params,
    get_collection,
    passes_collection_filters,
    premiere_field_for_scope,
    premiere_range_days,
    release_years_for_period,
    search_collection,
    year_in_release_window,
)
from app.genres import (
    GENRE_ANY_ID,
    build_collection_callback,
    build_collection_genre_callback,
    get_genre,
    parse_collection_callback,
    parse_collection_genre_callback,
)
from app.models import MovieItem


def test_build_collection_callback():
    assert parse_collection_callback("collection:new_foreign_movies") == (
        "new_foreign_movies"
    )
    assert build_collection_callback("new_foreign_movies") == (
        "collection:new_foreign_movies"
    )


def test_build_collection_genre_callback():
    data = build_collection_genre_callback("new_foreign_movies", "detective")
    assert parse_collection_genre_callback(data) == (
        "new_foreign_movies",
        "detective",
    )


def test_new_releases_use_120_day_premiere_window():
    collection = get_collection("new_foreign_series")
    assert collection is not None
    assert collection.period == "last_120_days"

    params = build_search_params(collection, get_genre(GENRE_ANY_ID))
    premiere_value = next(value for key, value in params if key.startswith("premiere."))
    expected_start = date.today() - timedelta(days=NEW_RELEASE_PREMIERE_DAYS)
    assert premiere_value == premiere_range_days(NEW_RELEASE_PREMIERE_DAYS)
    assert premiere_value.startswith(expected_start.strftime("%d.%m.%Y"))


def test_russian_collection_uses_premiere_russia():
    collection = get_collection("new_russian_movies")
    assert collection is not None
    assert premiere_field_for_scope(collection.country_scope) == "premiere.russia"

    params = build_search_params(collection, get_genre(GENRE_ANY_ID))
    premiere_params = [item for item in params if item[0].startswith("premiere.")]
    assert len(premiere_params) == 1
    assert premiere_params[0][0] == "premiere.russia"
    assert ("premiere.world", premiere_params[0][1]) not in params
    assert ("sortField", "premiere.russia") in params


def test_release_years_for_period_covers_window():
    years = release_years_for_period(NEW_RELEASE_PREMIERE_DAYS)
    today = date.today()
    start = today - timedelta(days=NEW_RELEASE_PREMIERE_DAYS)
    assert years == tuple(range(start.year, today.year + 1))


def test_year_in_release_window():
    today = date.today()
    in_window = MovieItem(
        id=1,
        title="Новинка",
        year=today.year,
        kp_rating=7.0,
        genres=["драма"],
        countries=["Россия"],
    )
    old = MovieItem(
        id=2,
        title="Старое",
        year=today.year - 2,
        kp_rating=7.0,
        genres=["драма"],
        countries=["Россия"],
    )
    assert year_in_release_window(in_window, days=NEW_RELEASE_PREMIERE_DAYS) is True
    assert year_in_release_window(old, days=NEW_RELEASE_PREMIERE_DAYS) is False


def test_build_search_params_year_mode():
    collection = get_collection("new_russian_series")
    assert collection is not None

    params = build_search_params(
        collection,
        get_genre(GENRE_ANY_ID),
        search_mode="year",
    )
    assert not any(key.startswith("premiere.") for key, _ in params)
    years = release_years_for_period(NEW_RELEASE_PREMIERE_DAYS)
    if len(years) == 1:
        assert ("year", years[0]) in params
    else:
        assert ("year", f"{years[0]}-{years[-1]}") in params


@pytest.mark.asyncio
async def test_search_collection_merges_year_fallback():
    client = AsyncMock()
    premiere_hit = MovieItem(
        id=1,
        title="С датой премьеры",
        year=2026,
        kp_rating=7.5,
        genres=["драма"],
        countries=["Россия"],
        is_series=True,
        poster_url="https://example.com/1.jpg",
    )
    year_only = MovieItem(
        id=9006713,
        title="Первая ракетка",
        year=2026,
        kp_rating=7.95,
        genres=["драма", "спорт"],
        countries=["Россия"],
        is_series=True,
        poster_url="https://example.com/2.jpg",
    )
    client.fetch_by_params = AsyncMock(
        side_effect=[[premiere_hit], [], [year_only], []]
    )

    movies = await search_collection(client, "new_russian_series", GENRE_ANY_ID)

    assert [movie.title for movie in movies] == [
        "С датой премьеры",
        "Первая ракетка",
    ]
    year_params = next(
        call.args[0]
        for call in client.fetch_by_params.await_args_list
        if any(key == "year" for key, _ in call.args[0])
    )
    assert not any(key.startswith("premiere.") for key, _ in year_params)


def test_foreign_collection_uses_premiere_world():
    collection = get_collection("new_foreign_movies")
    assert collection is not None
    assert premiere_field_for_scope(collection.country_scope) == "premiere.world"

    params = build_search_params(collection, get_genre(GENRE_ANY_ID))
    premiere_params = [item for item in params if item[0].startswith("premiere.")]
    assert premiere_params[0][0] == "premiere.world"
    assert ("sortField", "premiere.world") in params


def test_build_search_params_can_skip_api_genre_filter():
    collection = get_collection("new_russian_movies")
    genre = get_genre("detective")
    assert collection is not None
    assert genre is not None

    params = build_search_params(
        collection,
        genre,
        include_genre_filter=False,
    )
    assert ("genres.name", "+детектив") not in params


@pytest.mark.asyncio
async def test_search_collection_falls_back_to_client_side_genre_filter():
    client = AsyncMock()
    comedy = MovieItem(
        id=11,
        title="Холоп 3",
        year=2026,
        kp_rating=7.0,
        genres=["комедия", "приключения"],
        countries=["Россия"],
        poster_url="https://example.com/poster.jpg",
    )

    async def fetch_side_effect(params):
        params_dict = dict(params)
        is_year = "year" in params_dict and not any(
            key.startswith("premiere.") for key, _ in params
        )
        has_genre = ("genres.name", "+комедия") in params
        if is_year:
            return []
        if has_genre:
            return []
        if params_dict["page"] == 1:
            return [comedy]
        return []

    client.fetch_by_params = AsyncMock(side_effect=fetch_side_effect)

    movies = await search_collection(client, "new_russian_movies", "comedy")

    assert [movie.title for movie in movies] == ["Холоп 3"]
    premiere_with_genre = next(
        call.args[0]
        for call in client.fetch_by_params.await_args_list
        if ("genres.name", "+комедия") in call.args[0]
        and any(key.startswith("premiere.") for key, _ in call.args[0])
    )
    premiere_without_genre = next(
        call.args[0]
        for call in client.fetch_by_params.await_args_list
        if ("genres.name", "+комедия") not in call.args[0]
        and any(key.startswith("premiere.") for key, _ in call.args[0])
    )
    assert ("genres.name", "+комедия") in premiere_with_genre
    assert ("genres.name", "+комедия") not in premiere_without_genre


def test_any_genre_does_not_add_filter():
    collection = get_collection("new_foreign_movies")
    genre = get_genre(GENRE_ANY_ID)
    assert collection is not None
    assert genre is not None

    params = build_search_params(collection, genre)
    assert ("genres.name", "+детектив") not in params
    assert all(
        item[0] != "genres.name" or not str(item[1]).startswith("+") for item in params
    )


def test_genre_filter_is_applied_in_params_and_client_filter():
    collection = get_collection("new_russian_movies")
    genre = get_genre("detective")
    assert collection is not None
    assert genre is not None

    params = build_search_params(collection, genre)
    assert ("genres.name", "+детектив") in params

    matching = MovieItem(
        id=1,
        title="Детектив",
        year=2025,
        kp_rating=7.0,
        genres=["детектив"],
        countries=["Россия"],
        poster_url="https://example.com/poster.jpg",
    )
    other = MovieItem(
        id=2,
        title="Комедия",
        year=2025,
        kp_rating=7.0,
        genres=["комедия"],
        countries=["Россия"],
        poster_url="https://example.com/poster.jpg",
    )

    assert passes_collection_filters(matching, collection, genre) is True
    assert passes_collection_filters(other, collection, genre) is False


def test_passes_collection_filters_requires_kp_rating():
    collection = get_collection("most_popular")
    genre = get_genre(GENRE_ANY_ID)
    movie = MovieItem(
        id=3,
        title="Без рейтинга",
        year=2024,
        kp_rating=None,
        genres=["драма"],
        countries=["США"],
    )

    assert collection is not None
    assert genre is not None
    assert passes_collection_filters(movie, collection, genre) is False


@pytest.mark.asyncio
async def test_search_collection_returns_empty_without_padding():
    client = AsyncMock()
    client.fetch_by_params = AsyncMock(
        return_value=[
            MovieItem(
                id=10,
                title="Единственный",
                year=2025,
                kp_rating=7.1,
                genres=["драма"],
                countries=["США"],
                poster_url="https://example.com/poster.jpg",
            )
        ]
    )

    movies = await search_collection(client, "most_popular", GENRE_ANY_ID)

    assert len(movies) == 1
    assert movies[0].title == "Единственный"


@pytest.mark.asyncio
async def test_search_collection_unknown_collection():
    client = AsyncMock()
    movies = await search_collection(client, "unknown", GENRE_ANY_ID)
    assert movies == []
    client.fetch_by_params.assert_not_called()


def test_empty_collection_message_constant():
    assert EMPTY_COLLECTION_MESSAGE == "По этой подборке и жанру ничего не найдено."
