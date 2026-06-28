from __future__ import annotations

import logging

import httpx

from app.collections import EMPTY_COLLECTION_MESSAGE, get_collection, search_collection
from app.content_filters import filter_movies
from app.gigachat_client import GigaChatClient
from app.kinopoisk_client import KinopoiskClient
from app.kinopoisk_errors import format_kinopoisk_error, run_kinopoisk
from app.messages import no_results_message
from app.models import SearchFilters, SearchResult
from app.protocols import MovieRepository
from app.query_parser import filters_from_ui, is_director_request
from app.query_router import resolve_search_filters
from app.ranker import rank_movies
from app.response_formatter import format_recommendations

logger = logging.getLogger(__name__)


class MovieAgent:
    def __init__(
        self,
        client: MovieRepository | None = None,
        ai_parser: GigaChatClient | None = None,
    ):
        self.client: MovieRepository = client or KinopoiskClient()
        self.ai_parser = ai_parser or GigaChatClient()

    async def close(self) -> None:
        await self.client.close()
        await self.ai_parser.close()

    async def search(self, filters: SearchFilters) -> str:
        logger.info(
            "Search mode=%s type=%s year=%s country=%s genres=%s count=%s "
            "company=%s title=%s",
            filters.query_mode,
            filters.media_type,
            filters.year,
            filters.country_name,
            filters.genre_names,
            filters.count,
            filters.company_query,
            filters.title_query,
        )

        try:
            if filters.query_mode == "title" and filters.title_query:
                raw = await self.client.search_by_title(filters.title_query, filters)
            elif filters.query_mode == "similar" and filters.title_query:
                raw = await self.client.search_similar(filters.title_query, filters)
            elif filters.user_text and is_director_request(filters.user_text):
                raw = await self.client.search_by_text(filters.user_text, filters)
            else:
                raw = await self.client.search(filters)
        except RuntimeError as exc:
            return str(exc)
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Kinopoisk HTTP %s: %s", exc.response.status_code, exc.request.url
            )
            return format_kinopoisk_error(exc)
        except httpx.HTTPError:
            logger.exception("Kinopoisk network error")
            return "Не удалось связаться с Kinopoisk API. Попробуйте позже."
        except Exception:
            logger.exception("Kinopoisk search failed")
            return "Ошибка при обращении к Kinopoisk API. Попробуйте позже."

        movies = filter_movies(rank_movies(raw, filters), limit=filters.count)
        movies = await self.client.enrich_watchability(movies)
        logger.info("Filtered to %d movies", len(movies))

        if not movies:
            return no_results_message(filters)

        formatted = format_recommendations(
            movies, filters.media_type, requested=filters.count
        )
        if filters.query_mode == "similar" and filters.title_query:
            return f"Похожие на «{filters.title_query}»:\n\n{formatted}"
        return formatted

    async def ask(self, user_text: str) -> str:
        filters = await resolve_search_filters(
            user_text,
            ai_parser=self.ai_parser,
        )
        return await self.search(filters)

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
