import logging

from app.tmdb_client import format_countries, get_details

logger = logging.getLogger(__name__)


def build_recommendation_context(
    items: list[dict],
    media_type: str,
    *,
    limit: int = 5,
) -> str:
    context = ""

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
        overview = details.get("overview") or item.get("overview")
        rating = details.get("vote_average") or item.get("vote_average")
        release = (
            details.get("release_date")
            or details.get("first_air_date")
            or item.get("release_date")
            or item.get("first_air_date")
        )
        genres = ", ".join(g["name"] for g in details.get("genres", []))
        countries = format_countries(details, media_type)
        cast = ", ".join(
            actor["name"]
            for actor in details.get("credits", {}).get("cast", [])[:5]
        )

        director = "—"
        for crew_member in details.get("credits", {}).get("crew", []):
            if crew_member.get("job") == "Director":
                director = crew_member.get("name", "—")
                break

        context += f"""
Название: {title}
Режиссер: {director}
Страна: {countries}
Жанры: {genres}
Актеры: {cast}
Рейтинг: {rating}
Дата: {release}
Описание: {overview}
---
"""

        logger.debug("Added context for %s (id=%s)", title, item_id)

    return context
