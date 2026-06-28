import logging

from app.context_builder import build_recommendation_cards
from app.messages import no_results_message
from app.response_formatter import format_recommendations
from app.search_request import SearchRequest
from app.tmdb_client import (
    discover,
    is_director_request,
    parse_company,
    parse_count,
    parse_country_iso,
    parse_exclude_animation,
    parse_genres,
    parse_media_type,
    parse_year,
    resolve_company_id,
    resolve_network_id,
    search_person,
)

logger = logging.getLogger(__name__)


class MovieAgent:

    def _resolve_studio(
        self, request: SearchRequest
    ) -> tuple[int | None, int | None, str | None]:
        """Returns (company_id, network_id, error_message)."""
        if request.company_id:
            return request.company_id, None, None

        query = request.company_query
        if not query:
            return None, None, None

        if request.media_type == "tv":
            network_id = resolve_network_id(query)
            if network_id:
                return None, network_id, None

        company_id = resolve_company_id(query)
        if not company_id:
            return None, None, f"Не удалось найти студию «{query}» в TMDB."
        return company_id, None, None

    def search(self, request: SearchRequest) -> str:
        company_id, network_id, error = self._resolve_studio(request)
        if error:
            return error

        logger.info(
            "Search type=%s year=%s country=%s genres=%s count=%s "
            "animation_excluded=%s company=%s network_id=%s",
            request.media_type,
            request.year,
            request.country_iso,
            request.genre_ids,
            request.count,
            request.exclude_animation,
            request.company_query,
            network_id,
        )

        with_crew = request.with_crew
        if request.user_text and is_director_request(request.user_text):
            persons = search_person(request.user_text)
            if not persons:
                return (
                    "Не удалось найти режиссёра в TMDB. "
                    "Уточните имя и попробуйте снова."
                )
            with_crew = persons[0]["id"]

        items = discover(
            request.media_type,
            year=request.year,
            country_iso=request.country_iso,
            genre_ids=request.genre_ids,
            with_crew=with_crew,
            exclude_animation=request.exclude_animation,
            company_id=company_id,
            network_id=network_id,
        )
        logger.info("Discover returned %d items", len(items))

        if not items:
            return no_results_message(
                request.media_type,
                request.year,
                request.country_iso,
                request.genre_ids,
                company_query=request.company_query,
                exclude_animation=request.exclude_animation,
            )

        cards = build_recommendation_cards(items, request.media_type, limit=request.count)
        if not cards:
            return no_results_message(
                request.media_type,
                request.year,
                request.country_iso,
                request.genre_ids,
                company_query=request.company_query,
                exclude_animation=request.exclude_animation,
            )

        return format_recommendations(cards, request.media_type, requested=request.count)

    def ask(self, user_text: str) -> str:
        request = SearchRequest(
            media_type=parse_media_type(user_text),
            year=parse_year(user_text),
            country_iso=parse_country_iso(user_text),
            genre_ids=parse_genres(user_text),
            count=parse_count(user_text),
            exclude_animation=parse_exclude_animation(user_text),
            company_query=parse_company(user_text),
            user_text=user_text,
        )
        return self.search(request)

    def search_from_filters(self, filters: dict) -> str:
        request = SearchRequest(
            media_type=filters.get("media_type", "movie"),
            year=filters.get("year"),
            country_iso=filters.get("country_iso"),
            genre_ids=filters.get("genre_ids"),
            count=filters.get("count", 5),
            exclude_animation=filters.get("exclude_animation", False),
            company_query=filters.get("company_query"),
        )
        return self.search(request)
