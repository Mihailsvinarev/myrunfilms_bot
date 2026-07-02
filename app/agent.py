from __future__ import annotations

import logging

from app.collections import EMPTY_COLLECTION_MESSAGE, get_collection, search_collection
from app.content_filters import filter_movies
from app.kinopoisk_errors import run_kinopoisk
from app.messages import no_results_message
from app.models import MovieItem, SearchFilters, SearchResult
from app.protocols import MovieRepository, NaturalLanguageQueryParser
from app.query_parser import filters_from_ui, is_director_request
from app.query_router import resolve_search_filters
from app.ranker import rank_movies
from app.response_formatter import format_recommendations

logger = logging.getLogger(__name__)


class MovieAgent:
    def __init__(
        self,
        client: MovieRepository,
        ai_parser: NaturalLanguageQueryParser,
    ):
        self.client = client
        self.ai_parser = ai_parser

    async def close(self) -> None:
        await self.client.close()
        await self.ai_parser.close()

    async def search_movies(self, filters: SearchFilters) -> SearchResult:
        logger.info(
            "Search mode=%s type=%s year=%s country=%s genres=%s topic=%s count=%s "
            "company=%s title=%s",
            filters.query_mode,
            filters.media_type,
            filters.year,
            filters.country_name,
            filters.genre_names,
            filters.topic_query,
            filters.count,
            filters.company_query,
            filters.title_query,
        )

        raw, error = await run_kinopoisk(
            lambda: self._fetch_raw_movies(filters),
            log_context=f"Search mode={filters.query_mode}",
        )
        if error:
            return SearchResult(movies=[], error=error)

        assert raw is not None
        movies = filter_movies(rank_movies(raw, filters), limit=filters.count)
        movies = await self.client.enrich_watchability(movies)
        logger.info("Filtered to %d movies", len(movies))

        if not movies:
            return SearchResult(movies=[], error=no_results_message(filters))

        header = None
        if filters.query_mode == "similar" and filters.title_query:
            header = f"Похожие на «{filters.title_query}»"
        return SearchResult(movies=movies, header=header)

    async def search(self, filters: SearchFilters) -> str:
        result = await self.search_movies(filters)
        if result.error:
            return result.error
        formatted = format_recommendations(
            result.movies, filters.media_type, requested=filters.count
        )
        if result.header:
            return f"{result.header}:\n\n{formatted}"
        return formatted

    async def _fetch_raw_movies(self, filters: SearchFilters) -> list[MovieItem]:
        if filters.query_mode == "title" and filters.title_query:
            return await self.client.search_by_title(filters.title_query, filters)
        if filters.query_mode == "similar" and filters.title_query:
            return await self.client.search_similar(filters.title_query, filters)
        if filters.user_text and is_director_request(filters.user_text):
            return await self.client.search_by_text(filters.user_text, filters)
        return await self.client.search(filters)

    async def ask_movies(self, user_text: str) -> SearchResult:
        filters = await resolve_search_filters(
            user_text,
            ai_parser=self.ai_parser,
        )
        return await self.search_movies(filters)

    async def ask(self, user_text: str) -> str:
        filters = await resolve_search_filters(
            user_text,
            ai_parser=self.ai_parser,
        )
        return await self.search(filters)

    async def search_from_ui_movies(self, data: dict) -> SearchResult:
        filters = filters_from_ui(data)
        return await self.search_movies(filters)

    async def search_from_ui(self, data: dict) -> str:
        filters = filters_from_ui(data)
        return await self.search(filters)

    async def fetch_collection(
        self,
        collection_id: str,
        genre_id: str,
    ) -> SearchResult:
        collection = get_collection(collection_id)
        if collection is None:
            return SearchResult(movies=[], error=EMPTY_COLLECTION_MESSAGE)

        movies, error = await run_kinopoisk(
            lambda: search_collection(self.client, collection_id, genre_id),
            log_context=f"Collection {collection_id}/{genre_id}",
        )
        if error:
            return SearchResult(movies=[], error=error)
        if not movies:
            return SearchResult(movies=[], error=EMPTY_COLLECTION_MESSAGE)
        return SearchResult(movies=movies)
