from app.models import MovieItem, SearchFilters
from app.ranker import rank_movies


def _movie(
    movie_id: int,
    *,
    rating: float | None,
    year: int | None,
    countries: list[str] | None = None,
    genres: list[str] | None = None,
) -> MovieItem:
    return MovieItem(
        id=movie_id,
        title=f"Фильм {movie_id}",
        year=year,
        rating=rating,
        countries=countries or [],
        genres=genres or [],
        description="Русское описание.",
    )


def test_rank_movies_by_rating_when_no_filters():
    movies = [
        _movie(1, rating=7.0, year=2020),
        _movie(2, rating=9.1, year=2020),
        _movie(3, rating=8.0, year=2020),
    ]
    ranked = rank_movies(movies, SearchFilters())
    assert [movie.id for movie in ranked] == [2, 3, 1]


def test_rank_movies_prefers_genre_country_and_year_matches():
    movies = [
        _movie(
            1,
            rating=9.5,
            year=2025,
            countries=["США"],
            genres=["боевик"],
        ),
        _movie(
            2,
            rating=8.0,
            year=2026,
            countries=["Россия"],
            genres=["детектив", "драма"],
        ),
        _movie(
            3,
            rating=8.5,
            year=2026,
            countries=["Россия"],
            genres=["детектив"],
        ),
    ]
    filters = SearchFilters(
        media_type="tv",
        year=2026,
        country_name="Россия",
        genre_names=["детектив"],
    )

    ranked = rank_movies(movies, filters)

    assert [movie.id for movie in ranked] == [3, 2, 1]


def test_rank_movies_keeps_stable_order_for_equal_scores():
    movies = [
        _movie(10, rating=8.0, year=2024, countries=["Россия"], genres=["драма"]),
        _movie(20, rating=8.0, year=2024, countries=["Россия"], genres=["драма"]),
    ]
    filters = SearchFilters(
        year=2024,
        country_name="Россия",
        genre_names=["драма"],
    )

    ranked = rank_movies(movies, filters)

    assert [movie.id for movie in ranked] == [20, 10]


def test_rank_movies_supports_multiple_years():
    movies = [
        _movie(1, rating=8.0, year=2023),
        _movie(2, rating=9.0, year=2025),
        _movie(3, rating=7.0, year=2020),
    ]
    filters = SearchFilters(years=[2023, 2025])
    ranked = rank_movies(movies, filters)
    assert [movie.id for movie in ranked] == [2, 1, 3]
