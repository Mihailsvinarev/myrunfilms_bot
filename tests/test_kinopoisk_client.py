import httpx
import pytest

from app.kinopoisk_client import KinopoiskClient
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
