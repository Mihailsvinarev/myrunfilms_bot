from __future__ import annotations

from app.models import MovieItem, SearchFilters


def genre_match_score(movie: MovieItem, genre_names: list[str] | None) -> int:
    if not genre_names:
        return 0
    movie_genres = {genre.lower() for genre in movie.genres}
    return sum(1 for genre in genre_names if genre.lower() in movie_genres)


def country_match_score(movie: MovieItem, country_name: str | None) -> int:
    if not country_name:
        return 0
    return 1 if country_name in movie.countries else 0


def year_match_score(
    movie: MovieItem, year: int | None, years: list[int] | None
) -> int:
    if years:
        if movie.year is None:
            return 0
        return 1 if movie.year in years else 0
    if year is None or movie.year is None:
        return 0
    return 1 if movie.year == year else 0


def rank_key(
    movie: MovieItem, filters: SearchFilters
) -> tuple[int, int, int, float, int, int]:
    return (
        genre_match_score(movie, filters.genre_names),
        country_match_score(movie, filters.country_name),
        year_match_score(movie, filters.year, filters.years),
        movie.rating or 0.0,
        movie.year or 0,
        movie.id,
    )


def rank_movies(movies: list[MovieItem], filters: SearchFilters) -> list[MovieItem]:
    return sorted(movies, key=lambda movie: rank_key(movie, filters), reverse=True)
