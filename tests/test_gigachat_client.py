import json
import time

import httpx
import pytest

from app.gigachat_client import (
    GigaChatClient,
    QueryFilters,
    parse_query_payload,
    query_filters_to_search_filters,
)


def test_parse_query_payload_clamps_count():
    query = parse_query_payload(
        {
            "media_type": "tv",
            "genres": ["детектив"],
            "country": "Россия",
            "year": 2024,
            "year_from": None,
            "year_to": None,
            "director": None,
            "actor": None,
            "mood": "мрачное",
            "count": 12,
        }
    )
    assert query.count == 10
    assert query.genres == ["детектив"]


def test_query_filters_to_search_filters_maps_mood_and_director():
    query = QueryFilters(
        media_type="tv",
        genres=["детектив"],
        country="Россия",
        mood="мрачное",
        director="Нолан",
        count=3,
    )
    filters = query_filters_to_search_filters(query, "что-то мрачное про расследование")

    assert filters.media_type == "tv"
    assert filters.country_name == "Россия"
    assert "детектив" in filters.genre_names
    assert "режиссер" in filters.user_text.lower()
    assert filters.query_mode == "filter"


@pytest.mark.asyncio
async def test_gigachat_token_is_cached():
    oauth_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal oauth_calls
        if request.url.path.endswith("/oauth"):
            oauth_calls += 1
            return httpx.Response(
                200,
                json={"access_token": "token-1", "expires_in": 1800},
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "media_type": "movie",
                                    "genres": ["детектив"],
                                    "country": None,
                                    "year": None,
                                    "year_from": None,
                                    "year_to": None,
                                    "director": None,
                                    "actor": None,
                                    "mood": "мрачное",
                                    "count": 5,
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = GigaChatClient(auth_key="test-key", client=http_client)
        client._token_cache.expires_at = time.time() + 1800
        client._token_cache.token = "cached-token"

        query = await client.parse_query("что-то мрачное про расследование")

    assert oauth_calls == 0
    assert query.genres == ["детектив"]


@pytest.mark.asyncio
async def test_gigachat_parse_query_calls_chat_completions():
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        if request.url.path.endswith("/oauth"):
            return httpx.Response(
                200,
                json={"access_token": "token-1", "expires_in": 1800},
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "media_type": "tv",
                                    "genres": ["детектив"],
                                    "country": "Россия",
                                    "year": 2026,
                                    "year_from": None,
                                    "year_to": None,
                                    "director": None,
                                    "actor": None,
                                    "mood": None,
                                    "count": 5,
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = GigaChatClient(auth_key="test-key", client=http_client)
        query = await client.parse_query("лучшие детективные сериалы России 2026")
        filters = client.to_search_filters(
            query, "лучшие детективные сериалы России 2026"
        )

    assert captured["path"].endswith("/chat/completions")
    assert filters.genre_names == ["детектив"]
    assert filters.country_name == "Россия"
    assert filters.year == 2026
