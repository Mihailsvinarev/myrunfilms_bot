from app.content_filters import filter_movies, has_excluded_genre
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
    }
    defaults.update(kwargs)
    return MovieItem(**defaults)


def test_has_excluded_genre():
    assert has_excluded_genre(_movie(genres=["мультфильм"]))
    assert not has_excluded_genre(_movie(genres=["детектив"]))


def test_filter_movies_respects_limit_without_padding():
    movies = [
        _movie(id=1),
        _movie(id=2, genres=["мультфильм"], description="Русское."),
        _movie(id=3),
    ]
    result = filter_movies(movies, limit=3)
    assert len(result) == 2
    assert [movie.id for movie in result] == [1, 3]
