import logging

from app.context_builder import build_recommendation_cards
from app.messages import no_results_message
from app.response_formatter import format_recommendations
from app.tmdb_client import (
    discover,
    is_director_request,
    parse_count,
    parse_country_iso,
    parse_genres,
    parse_media_type,
    parse_year,
    search_person,
)

logger = logging.getLogger(__name__)


class MovieAgent:

    def ask(self, user_text: str) -> str:
        media_type = parse_media_type(user_text)
        year = parse_year(user_text)
        country_iso = parse_country_iso(user_text)
        genre_ids = parse_genres(user_text)
        count = parse_count(user_text)

        logger.info(
            "Request type=%s year=%s country=%s genres=%s count=%s",
            media_type,
            year,
            country_iso,
            genre_ids,
            count,
        )

        with_crew = None
        if is_director_request(user_text):
            persons = search_person(user_text)
            if not persons:
                logger.warning("Director not found for query")
                return (
                    "Не удалось найти режиссёра в TMDB. "
                    "Уточните имя и попробуйте снова."
                )
            with_crew = persons[0]["id"]
            logger.info("Director mode person_id=%s", with_crew)

        items = discover(
            media_type,
            year=year,
            country_iso=country_iso,
            genre_ids=genre_ids,
            with_crew=with_crew,
        )
        logger.info("Discover returned %d items", len(items))

        if not items:
            return no_results_message(media_type, year, country_iso, genre_ids)

        cards = build_recommendation_cards(items, media_type, limit=count)
        if not cards:
            return no_results_message(media_type, year, country_iso, genre_ids)

        return format_recommendations(cards, media_type, requested=count)
