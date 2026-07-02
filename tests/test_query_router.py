from unittest.mock import AsyncMock, MagicMock

import pytest

from app.gigachat_client import QueryFilters
from app.models import SearchFilters
from app.query_router import resolve_search_filters


@pytest.mark.asyncio
async def test_resolve_search_filters_uses_gigachat_first():
    giga = AsyncMock()
    giga.is_available = MagicMock(return_value=True)
    giga.parse_query = AsyncMock(
        return_value=QueryFilters(
            media_type="tv",
            country="Россия",
            year=2025,
            count=5,
        )
    )
    giga.to_search_filters = MagicMock(
        return_value=SearchFilters(
            media_type="tv",
            country_name="Россия",
            year=2025,
            count=5,
            query_mode="filter",
        )
    )

    filters = await resolve_search_filters(
        "Сериалы Netflix 2025",
        ai_parser=giga,
    )

    giga.parse_query.assert_awaited_once()
    assert filters.country_name == "Россия"
    assert filters.year == 2025


@pytest.mark.asyncio
async def test_resolve_search_filters_falls_back_to_gigachat():
    giga = AsyncMock()
    giga.is_available = MagicMock(return_value=True)
    giga.parse_query = AsyncMock(
        return_value=QueryFilters(
            media_type="tv",
            genres=["детектив"],
            country="Россия",
            count=3,
        )
    )
    giga.to_search_filters = MagicMock(
        return_value=SearchFilters(
            media_type="tv",
            genre_names=["детектив"],
            country_name="Россия",
            count=3,
            query_mode="filter",
        )
    )

    filters = await resolve_search_filters(
        "Хочу что-нибудь мрачное про расследования",
        ai_parser=giga,
    )

    giga.parse_query.assert_awaited_once()
    assert filters.genre_names == ["детектив"]
    assert filters.country_name == "Россия"


@pytest.mark.asyncio
async def test_resolve_search_filters_uses_heuristic_when_gigachat_unavailable():
    giga = AsyncMock()
    giga.is_available = MagicMock(return_value=False)

    filters = await resolve_search_filters(
        "Хочу что-нибудь мрачное про расследования",
        ai_parser=giga,
    )

    giga.parse_query.assert_not_called()
    assert filters.query_mode == "filter"
    assert filters.genre_names == ["детектив", "триллер"]


@pytest.mark.asyncio
async def test_resolve_search_filters_uses_heuristic_when_gigachat_fails():
    giga = AsyncMock()
    giga.is_available = MagicMock(return_value=True)
    giga.parse_query = AsyncMock(side_effect=ValueError("invalid json"))

    filters = await resolve_search_filters(
        "что-то мрачное про расследование",
        ai_parser=giga,
    )

    assert filters.query_mode == "filter"
    assert filters.genre_names == ["детектив", "триллер"]


@pytest.mark.asyncio
async def test_resolve_search_filters_applies_topic_intent_from_text():
    giga = AsyncMock()
    giga.is_available = MagicMock(return_value=True)
    giga.parse_query = AsyncMock(return_value=QueryFilters(count=5))
    giga.to_search_filters = MagicMock(
        return_value=SearchFilters(
            count=5,
            query_mode="filter",
            media_type="movie",
        )
    )

    filters = await resolve_search_filters(
        "Сериал про теннис",
        ai_parser=giga,
    )

    assert filters.query_mode == "filter"
    assert filters.media_type == "tv"
    assert filters.topic_query == "теннис"
    assert filters.genre_names == ["спорт"]


@pytest.mark.asyncio
async def test_resolve_search_filters_applies_similar_intent_from_text():
    giga = AsyncMock()
    giga.is_available = MagicMock(return_value=True)
    giga.parse_query = AsyncMock(return_value=QueryFilters(count=5))
    giga.to_search_filters = MagicMock(
        return_value=SearchFilters(count=5, query_mode="filter")
    )

    filters = await resolve_search_filters(
        "посоветуй фильм как Интерстеллар",
        ai_parser=giga,
    )

    giga.parse_query.assert_awaited_once()
    assert filters.query_mode == "similar"
    assert filters.title_query == "Интерстеллар"
