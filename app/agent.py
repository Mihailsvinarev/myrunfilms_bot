import logging

from app.context_builder import build_recommendation_context
from app.llm_client import explain_recommendations
from app.messages import no_results_message
from app.tmdb_client import (
    country_label,
    discover,
    is_director_request,
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
        country = country_label(country_iso)

        logger.info(
            "Request type=%s year=%s country=%s genres=%s",
            media_type,
            year,
            country_iso,
            genre_ids,
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

        context = build_recommendation_context(items, media_type)
        if not context.strip():
            return no_results_message(media_type, year, country_iso, genre_ids)

        prompt = f"""
Пользователь запросил:
{user_text}

Тип: {media_type}
Год: {year or "не указан"}
Страна: {country or "не указана"}

Вот результаты TMDB (уже отфильтрованы):

{context}

Задача:
- выбери лучшие варианты из списка выше
- кратко объясни, почему они подходят
- не добавляй фильмы и сериалы, которых нет в списке
- отвечай на русском
"""

        return explain_recommendations(prompt)
