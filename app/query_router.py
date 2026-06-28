from __future__ import annotations

import logging

from app.gigachat_client import GigaChatClient
from app.models import SearchFilters
from app.query_parser import parse_search_filters, parse_vague_query

logger = logging.getLogger(__name__)


def _heuristic_fallback(text: str, deterministic: SearchFilters) -> SearchFilters:
    vague = parse_vague_query(text)
    if vague:
        logger.info("Using heuristic vague query parser")
        return vague
    logger.info("Using deterministic query parser fallback")
    return deterministic


async def resolve_search_filters(
    text: str,
    *,
    ai_parser: GigaChatClient | None = None,
) -> SearchFilters:
    deterministic = parse_search_filters(text)
    parser = ai_parser or GigaChatClient()

    if parser.is_available():
        try:
            logger.info("Using GigaChat query parser")
            query = await parser.parse_query(text)
            filters = parser.to_search_filters(query, text)
            return filters.model_copy(update={"user_text": filters.user_text or text})
        except Exception:
            logger.exception("GigaChat parse failed; using query_parser fallback")

    logger.warning("GigaChat unavailable; using query_parser fallback")
    return _heuristic_fallback(text, deterministic)
