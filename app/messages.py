from app.tmdb_client import country_label


def no_results_message(
    media_type: str,
    year: int | None,
    country_iso: str | None,
    genre_ids: list[int] | None,
    *,
    company_query: str | None = None,
    exclude_animation: bool = False,
) -> str:
    kind = "сериалов" if media_type == "tv" else "фильмов"
    parts = [f"Не нашёл подходящих {kind} в TMDB"]

    if year:
        parts.append(f"за {year} год")
    if country_iso:
        parts.append(f"из {country_label(country_iso)}")
    if genre_ids:
        parts.append("с указанным жанром")
    if company_query:
        parts.append(f"от студии {company_query}")
    if exclude_animation:
        parts.append("без мультфильмов")

    parts.append("Попробуйте изменить фильтры.")
    return " ".join(parts)
