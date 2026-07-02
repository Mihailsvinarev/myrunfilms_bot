from app.content_filters import (
    filter_movies,
    has_excluded_country,
    has_excluded_genre,
    has_poster,
    is_allowed_movie,
)
from app.models import MovieItem


def _movie(**kwargs) -> MovieItem:
    defaults = {
        "id": 1,
        "title": "Тест",
        "year": 2021,
        "rating": 7.0,
        "countries": ["Россия"],
        "genres": ["детектив"],
        "description": "Русское описание.",
        "is_series": True,
        "poster_url": "https://example.com/poster.jpg",
    }
    defaults.update(kwargs)
    return MovieItem(**defaults)


def test_has_excluded_genre():
    assert has_excluded_genre(_movie(genres=["мультфильм"]))
    assert has_excluded_genre(_movie(genres=["концерт"]))
    assert not has_excluded_genre(_movie(genres=["детектив"]))


def test_has_excluded_country():
    assert has_excluded_country(_movie(countries=["Индия", "США"]))
    assert not has_excluded_country(_movie(countries=["Россия"]))


def test_has_poster():
    assert has_poster(_movie(poster_url="https://example.com/poster.jpg")) is True
    assert has_poster(_movie(poster_url=None)) is False
    assert has_poster(_movie(poster_url="   ")) is False


def test_is_allowed_movie_requires_poster():
    assert is_allowed_movie(_movie(poster_url=None)) is False
    assert is_allowed_movie(_movie(poster_url="https://example.com/poster.jpg")) is True


def test_filter_movies_skips_items_without_poster():
    movies = [
        _movie(id=1, poster_url="https://example.com/1.jpg"),
        _movie(id=2, poster_url=None),
        _movie(id=3, poster_url="https://example.com/3.jpg"),
    ]
    result = filter_movies(movies, limit=3)
    assert [movie.id for movie in result] == [1, 3]


def test_filter_movies_respects_limit_without_padding():
    movies = [
        _movie(id=1),
        _movie(id=2, genres=["мультфильм"], description="Русское."),
        _movie(id=3),
    ]
    result = filter_movies(movies, limit=3)
    assert len(result) == 2
    assert [movie.id for movie in result] == [1, 3]
