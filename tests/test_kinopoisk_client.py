import httpx
import pytest

from app.kinopoisk_client import (
    KinopoiskClient,
    _extract_russian_title,
    _premiere_range,
)
from app.models import MovieItem, SearchFilters

SAMPLE_DOC = {
    "id": 100,
    "name": "Тестовый сериал",
    "year": 2025,
    "rating": {"kp": 7.5},
    "genres": [{"name": "детектив"}],
    "countries": [{"name": "Россия"}],
    "description": "Русское описание сериала на Kinopoisk.",
    "isSeries": True,
    "type": "tv-series",
    "poster": {"url": "https://example.com/poster.jpg"},
}


@pytest.mark.asyncio
async def test_search_by_filters_builds_kinopoisk_params():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json={"docs": [SAMPLE_DOC]})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://api.kinopoisk.dev/v1.4",
        headers={"X-API-KEY": "test"},
    ) as http_client:
        client = KinopoiskClient(api_key="test", client=http_client)
        filters = SearchFilters(
            media_type="tv",
            year=2025,
            country_name="Россия",
            genre_names=["детектив"],
            count=3,
        )
        movies = await client.search(filters)

    assert movies[0].title == "Тестовый сериал"
    assert movies[0].is_series is True
    assert captured["params"]["year"] == "2025"
    assert captured["params"]["isSeries"] == "true"


@pytest.mark.asyncio
async def test_search_by_company_uses_network_filter():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json={"docs": [SAMPLE_DOC]})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://api.kinopoisk.dev/v1.4",
        headers={"X-API-KEY": "test"},
    ) as http_client:
        client = KinopoiskClient(api_key="test", client=http_client)
        filters = SearchFilters(
            media_type="tv", year=2025, company_query="Netflix", count=3
        )
        movies = await client.search(filters)

    assert captured["path"].endswith("/movie")
    assert captured["params"]["networks.items.name"] == "Netflix"
    assert captured["params"]["year"] == "2025"
    assert movies[0].kinopoisk_url.endswith("/series/100/")


@pytest.mark.asyncio
async def test_enrich_watchability_fetches_platform_links():
    sample = {
        "watchability": {
            "items": [
                {"name": "Иви", "url": "https://ivi.ru/watch/1"},
                {"name": "Wink", "url": "https://wink.ru/1"},
            ]
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/111"):
            return httpx.Response(200, json=sample)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://api.kinopoisk.dev/v1.4",
        headers={"X-API-KEY": "test"},
    ) as http_client:
        client = KinopoiskClient(api_key="test", client=http_client)
        movie = MovieItem(
            id=111,
            title="Тест",
            year=2024,
            description="Описание.",
        )
        enriched = await client.enrich_watchability([movie])

    assert len(enriched[0].watch_platforms) == 2
    assert enriched[0].watch_platforms[0].name == "Иви"
    assert enriched[0].watch_platforms[1].url == "https://wink.ru/1"


@pytest.mark.asyncio
async def test_search_by_title_matches_exact_name():
    docs = [
        {
            "id": 258687,
            "name": "Интерстеллар",
            "alternativeName": "Interstellar",
            "year": 2014,
            "genres": [{"name": "фантастика"}],
            "countries": [{"name": "США"}],
            "description": "Русское описание фильма.",
            "isSeries": False,
            "poster": {"url": "https://example.com/interstellar.jpg"},
        },
        {
            "id": 1009186,
            "name": "Наука «Интерстеллар»",
            "alternativeName": "The Science of Interstellar",
            "year": 2014,
            "genres": [{"name": "документальный"}],
            "countries": [{"name": "США"}],
            "description": "Русское описание документального фильма.",
            "isSeries": False,
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/movie/search")
        return httpx.Response(200, json={"docs": docs})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://api.kinopoisk.dev/v1.4",
        headers={"X-API-KEY": "test"},
    ) as http_client:
        client = KinopoiskClient(api_key="test", client=http_client)
        filters = SearchFilters(
            title_query="Интерстеллар",
            query_mode="title",
            restrict_media_type=False,
            count=5,
        )
        movies = await client.search_by_title("Интерстеллар", filters)

    assert len(movies) == 1
    assert movies[0].id == 258687
    assert movies[0].title == "Интерстеллар"


@pytest.mark.asyncio
async def test_search_similar_loads_similar_movies_from_reference_detail():
    captured: dict[str, object] = {}

    reference_doc = {
        "id": 258687,
        "name": "Интерстеллар",
        "alternativeName": "Interstellar",
        "year": 2014,
        "genres": [{"name": "фантастика"}],
        "countries": [{"name": "США"}],
        "description": "Русское описание фильма.",
        "isSeries": False,
        "poster": {"url": "https://example.com/interstellar.jpg"},
    }
    similar_doc = {
        **SAMPLE_DOC,
        "id": 777,
        "name": "Гравитация",
        "genres": [{"name": "фантастика"}],
        "isSeries": False,
        "type": "movie",
        "poster": {"url": "https://example.com/gravity.jpg"},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/movie/search"):
            return httpx.Response(200, json={"docs": [reference_doc]})
        if request.url.path.endswith("/258687"):
            return httpx.Response(
                200,
                json={
                    **reference_doc,
                    "similarMovies": [{"id": 777, "name": "Гравитация"}],
                },
            )
        if request.url.path.endswith("/movie"):
            captured["params"] = dict(request.url.params)
            return httpx.Response(200, json={"docs": [similar_doc]})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://api.kinopoisk.dev/v1.4",
        headers={"X-API-KEY": "test"},
    ) as http_client:
        client = KinopoiskClient(api_key="test", client=http_client)
        filters = SearchFilters(
            title_query="Интерстеллар",
            query_mode="similar",
            restrict_media_type=False,
            count=3,
        )
        movies = await client.search_similar("Интерстеллар", filters)

    assert captured["params"]["id"] == "777"
    assert "similarMovies.id" not in captured["params"]
    assert len(movies) == 1
    assert movies[0].title == "Гравитация"


@pytest.mark.asyncio
async def test_search_new_movies_uses_premiere_and_rating_sort():
    captured_pages: list[list[tuple[str, str | int]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_pages.append(list(request.url.params.multi_items()))
        return httpx.Response(
            200,
            json={
                "docs": [
                    {
                        **SAMPLE_DOC,
                        "id": 501,
                        "name": "Новый фильм",
                        "isSeries": False,
                        "type": "movie",
                        "rating": {"kp": 7.0, "tmdb": 8.2},
                        "poster": {"url": "https://example.com/poster.jpg"},
                    },
                    {
                        **SAMPLE_DOC,
                        "id": 502,
                        "name": "Без TMDB",
                        "isSeries": False,
                        "type": "movie",
                        "rating": {"kp": 7.5, "imdb": 6.4},
                        "poster": {"url": "https://example.com/poster2.jpg"},
                    },
                    {
                        **SAMPLE_DOC,
                        "id": 503,
                        "name": "Слабый рейтинг",
                        "isSeries": False,
                        "type": "movie",
                        "rating": {"kp": 5.0, "tmdb": 8.0},
                    },
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://api.kinopoisk.dev/v1.4",
        headers={"X-API-KEY": "test"},
    ) as http_client:
        client = KinopoiskClient(api_key="test", client=http_client)
        movies = await client.search_new_movies(limit=5)

    params = dict(captured_pages[0])
    assert params["isSeries"] == "false"
    assert params["type"] == "movie"
    assert params["rating.kp"] == "6-10"
    assert "premiere.world" in params
    assert captured_pages[0].count(("sortField", "premiere.world")) == 1
    assert captured_pages[0].count(("sortField", "rating.kp")) == 1
    assert captured_pages[0].count(("sortField", "rating.tmdb")) == 1
    assert ("rating.tmdb", "6-10") not in captured_pages[0]
    assert len(movies) == 2
    assert movies[0].title == "Новый фильм"
    assert movies[0].kp_rating == 7.0
    assert movies[0].tmdb_rating == 8.2
    assert movies[1].imdb_rating == 6.4


@pytest.mark.asyncio
async def test_search_popular_series_uses_kp_votes_sort():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = list(request.url.params.multi_items())
        return httpx.Response(200, json={"docs": [SAMPLE_DOC]})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://api.kinopoisk.dev/v1.4",
        headers={"X-API-KEY": "test"},
    ) as http_client:
        client = KinopoiskClient(api_key="test", client=http_client)
        movies = await client.search_popular_series(limit=1)

    params = dict(captured["params"])
    assert params["isSeries"] == "true"
    assert captured["params"].count(("sortField", "votes.kp")) == 1
    assert movies[0].is_series is True


@pytest.mark.asyncio
async def test_search_by_filters_supports_multiple_years():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json={"docs": [SAMPLE_DOC]})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://api.kinopoisk.dev/v1.4",
        headers={"X-API-KEY": "test"},
    ) as http_client:
        client = KinopoiskClient(api_key="test", client=http_client)
        filters = SearchFilters(
            media_type="tv",
            years=[2024, 2025],
            count=3,
        )
        await client.search(filters)

    assert captured["params"]["year"] == "2024-2025"


def test_premiere_range_uses_kinopoisk_date_format():
    value = _premiere_range(6)
    parts = value.split("-")
    assert len(parts) == 2
    for part in parts:
        day, month, year = part.split(".")
        assert len(day) == 2 and len(month) == 2 and len(year) == 4


def test_extract_russian_title_prefers_ru_name():
    title = _extract_russian_title(
        {
            "name": "Interstellar",
            "alternativeName": "Interstellar",
            "names": [
                {
                    "name": "Интерстеллар",
                    "language": "RU",
                    "type": "Russian title on kinopoisk",
                },
                {"name": "Interstellar", "language": None, "type": "Original title"},
            ],
        }
    )
    assert title == "Интерстеллар"
