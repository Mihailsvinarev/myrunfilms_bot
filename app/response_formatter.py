from __future__ import annotations

from app.models import MovieItem
from app.platform_labels import platform_label
from app.telegram_utils import truncate_description


def format_compact_caption(movie: MovieItem, *, rating_label: str) -> str:
    year = str(movie.year) if movie.year else "—"
    return f"{movie.title} ({year})\n⭐ {rating_label}"


def format_compact_list(
    movies: list[MovieItem],
    *,
    rating_label_fn,
    header: str,
) -> str:
    lines = [header, ""]
    for index, movie in enumerate(movies, start=1):
        year = str(movie.year) if movie.year else "—"
        lines.append(f"{index}. {movie.title} ({year}) — ⭐ {rating_label_fn(movie)}")
    return "\n".join(lines).strip()


def format_recommendations(
    movies: list[MovieItem],
    media_type: str,
    *,
    requested: int,
) -> str:
    if not movies:
        return ""

    icon = "📺" if media_type == "tv" else "🎬"
    kind = "сериалов" if media_type == "tv" else "фильмов"
    lines: list[str] = []

    if len(movies) < requested:
        lines.append(f"Нашёл {len(movies)} из {requested} запрошенных {kind}:\n")
    else:
        lines.append(f"Подборка из {len(movies)} {kind}:\n")

    for movie in movies:
        year = str(movie.year) if movie.year else "—"
        lines.append(f"{icon} {movie.title} ({year})")
        lines.append(
            f"⭐ {movie.rating_label} | {movie.countries_label} | {movie.genres_label}"
        )
        if movie.description:
            lines.append(truncate_description(movie.description))
        if movie.watch_platforms:
            lines.append("Где смотреть:")
            for platform in movie.watch_platforms:
                lines.append(f"{platform_label(platform.name)}: {platform.url}")
        lines.append(f"Кинопоиск: {movie.kinopoisk_url}")
        lines.append("")

    return "\n".join(lines).strip()
