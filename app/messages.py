from app.tmdb_client import country_label


def no_results_message(
    media_type: str,
    year: int | None,
    country_iso: str | None,
    genre_ids: list[int] | None,
) -> str:
    kind = "сериалов" if media_type == "tv" else "фильмов"
    parts = [f"Не нашёл подходящих {kind} в TMDB"]

    if year:
        parts.append(f"за {year} год")
    if country_iso:
        parts.append(f"из {country_label(country_iso)}")
    if genre_ids:
        parts.append("с указанным жанром")

    parts.append("Попробуйте изменить год, страну или жанр.")
    return " ".join(parts)
