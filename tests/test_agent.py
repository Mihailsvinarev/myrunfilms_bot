from unittest.mock import AsyncMock, patch

import pytest

from app.agent import MovieAgent
from app.models import MovieItem, SearchFilters


@pytest.mark.asyncio
async def test_agent_search_formats_results():
    agent = MovieAgent(client=AsyncMock())
    agent.client.search = AsyncMock(
        return_value=[
            MovieItem(
                id=1,
                title="Сериал",
                year=2021,
                rating=8.0,
                countries=["Россия"],
                genres=["детектив"],
                description="Русское описание сериала.",
                is_series=True,
            )
        ]
    )
    agent.client.enrich_watchability = AsyncMock(side_effect=lambda movies: movies)

    answer = await agent.search(
        SearchFilters(
            media_type="tv",
            year=2021,
            country_name="Россия",
            count=3,
            query_mode="filter",
        )
    )

    assert "Сериал" in answer
    assert "kinopoisk.ru/series/1/" in answer


@pytest.mark.asyncio
@patch("app.agent.resolve_search_filters", new_callable=AsyncMock)
async def test_agent_ask_title_search(_mock_resolve):
    _mock_resolve.return_value = SearchFilters(
        query_mode="title",
        title_query="Интерстеллар",
        restrict_media_type=False,
        user_text="Интерстеллар",
    )
    agent = MovieAgent(client=AsyncMock())
    agent.client.search_by_title = AsyncMock(return_value=[])
    agent.client.enrich_watchability = AsyncMock(side_effect=lambda movies: movies)

    await agent.ask("Интерстеллар")

    filters = agent.client.search_by_title.await_args.args[1]
    _mock_resolve.assert_awaited_once()
    assert filters.query_mode == "title"
    assert filters.title_query == "Интерстеллар"
    agent.client.search.assert_not_called()


@pytest.mark.asyncio
@patch("app.agent.resolve_search_filters", new_callable=AsyncMock)
async def test_agent_ask_parses_text(_mock_resolve):
    _mock_resolve.return_value = SearchFilters(
        media_type="tv",
        year=2025,
        company_query="Netflix",
        query_mode="filter",
        user_text="Сериалы Netflix 2025",
    )
    agent = MovieAgent(client=AsyncMock())
    agent.client.search = AsyncMock(return_value=[])
    agent.client.enrich_watchability = AsyncMock(side_effect=lambda movies: movies)

    await agent.ask("Сериалы Netflix 2025")

    _mock_resolve.assert_awaited_once()
    filters = agent.client.search.await_args.args[0]
    assert filters.media_type == "tv"
    assert filters.company_query == "Netflix"
