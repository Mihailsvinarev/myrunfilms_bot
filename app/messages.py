from app.models import SearchFilters


def no_results_message(filters: SearchFilters) -> str:
    if filters.query_mode == "title" and filters.title_query:
        return (
            f"Не нашёл фильм или сериал с названием «{filters.title_query}». "
            "Проверьте написание или попробуйте другое название."
        )
    if filters.query_mode == "similar" and filters.title_query:
        return (
            f"Не удалось подобрать фильмы, похожие на «{filters.title_query}». "
            "Проверьте название или измените запрос."
        )

    kind = "сериалов" if filters.media_type == "tv" else "фильмов"
    parts = [f"Не нашёл подходящих {kind} в Kinopoisk"]

    if filters.year:
        parts.append(f"за {filters.year} год")
    if filters.country_name:
        parts.append(f"из {filters.country_name}")
    if filters.genre_names:
        parts.append("с указанным жанром")
    if filters.company_query:
        parts.append(f"от студии {filters.company_query}")

    parts.append("Попробуйте изменить фильтры.")
    return " ".join(parts)
