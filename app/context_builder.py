import logging

from app.response_formatter import RecommendationCard
from app.tmdb_client import format_countries, get_details

logger = logging.getLogger(__name__)

OVERVIEW_MAX_LEN = 280


def _format_rating(value) -> str:
    if value is None:
        return "—"
    return f"{value:.1f}" if isinstance(value, (int, float)) else str(value)


def _format_year(release: str | None) -> str:
    if release and len(release) >= 4:
        return release[:4]
    return "—"


def _trim_overview(text: str | None) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= OVERVIEW_MAX_LEN:
        return text
    return text[: OVERVIEW_MAX_LEN - 3].rstrip() + "..."


def build_recommendation_cards(
    items: list[dict],
    media_type: str,
    *,
    limit: int = 5,
) -> list[RecommendationCard]:
    cards: list[RecommendationCard] = []

    for item in items[:limit]:
        item_id = item.get("id")
        if not item_id:
            continue

        details = get_details(media_type, item_id)
        title = (
            details.get("title")
            or details.get("name")
            or item.get("title")
            or item.get("name")
        )
        if not title:
            continue

        release = (
            details.get("release_date")
            or details.get("first_air_date")
            or item.get("release_date")
            or item.get("first_air_date")
        )
        genres = ", ".join(g["name"] for g in details.get("genres", [])) or "—"

        cards.append(
            RecommendationCard(
                title=title,
                year=_format_year(release),
                rating=_format_rating(
                    details.get("vote_average") or item.get("vote_average")
                ),
                countries=format_countries(details, media_type),
                genres=genres,
                overview=_trim_overview(
                    details.get("overview") or item.get("overview")
                ),
            )
        )
        logger.debug("Built card for %s (id=%s)", title, item_id)

    return cards
