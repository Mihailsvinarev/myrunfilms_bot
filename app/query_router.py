from __future__ import annotations

import logging

from app.models import SearchFilters
from app.protocols import NaturalLanguageQueryParser
from app.query_parser import (
    has_explicit_media_type,
    parse_search_filters,
    parse_vague_query,
)

logger = logging.getLogger(__name__)


def _heuristic_fallback(text: str, deterministic: SearchFilters) -> SearchFilters:
    vague = parse_vague_query(text)
    if vague:
        logger.info("Using heuristic vague query parser")
        return vague
    logger.info("Using deterministic query parser fallback")
    return deterministic


def _apply_similar_intent(text: str, filters: SearchFilters) -> SearchFilters:
    if filters.query_mode == "similar" and filters.title_query:
        return filters

    deterministic = parse_search_filters(text)
    if deterministic.query_mode != "similar" or not deterministic.title_query:
        return filters

    return filters.model_copy(
        update={
            "query_mode": "similar",
            "title_query": deterministic.title_query,
            "restrict_media_type": deterministic.restrict_media_type,
            "genre_names": None,
            "country_name": filters.country_name,
            "year": filters.year,
        }
    )


def _apply_topic_intent(text: str, filters: SearchFilters) -> SearchFilters:
    deterministic = parse_search_filters(text)
    updates: dict[str, object] = {}

    if deterministic.topic_query and not filters.topic_query:
        updates["topic_query"] = deterministic.topic_query
    if deterministic.genre_names and not filters.genre_names:
        updates["genre_names"] = deterministic.genre_names
    if deterministic.media_type == "tv" and has_explicit_media_type(text):
        if filters.media_type != "tv":
            updates["media_type"] = "tv"
        updates["restrict_media_type"] = True
    if deterministic.query_mode == "filter" and filters.query_mode != "similar":
        updates["query_mode"] = "filter"
        updates["title_query"] = None

    if not updates:
        return filters
    return filters.model_copy(update=updates)


async def resolve_search_filters(
    text: str,
    *,
    ai_parser: NaturalLanguageQueryParser,
) -> SearchFilters:
    deterministic = parse_search_filters(text)

    if ai_parser.is_available():
        try:
            logger.info("Using GigaChat query parser")
            query = await ai_parser.parse_query(text)
            filters = ai_parser.to_search_filters(query, text)
            filters = filters.model_copy(
                update={"user_text": filters.user_text or text}
            )
            return _apply_topic_intent(text, _apply_similar_intent(text, filters))
        except Exception:
            logger.exception("GigaChat parse failed; using query_parser fallback")

    logger.warning("GigaChat unavailable; using query_parser fallback")
    return _heuristic_fallback(text, deterministic)
