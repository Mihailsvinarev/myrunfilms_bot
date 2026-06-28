from app.models import MovieItem, WatchPlatform
from app.response_formatter import format_compact_caption, format_recommendations


def test_format_recommendations_with_kinopoisk_link():
    movies = [
        MovieItem(
            id=42,
            title="Тестовый фильм",
            year=2021,
            rating=8.1,
            countries=["Россия"],
            genres=["детектив"],
            description="Описание на русском.",
            is_series=False,
        )
    ]
    text = format_recommendations(movies, "movie", requested=3)
    assert "Нашёл 1 из 3" in text
    assert "Кинопоиск: https://www.kinopoisk.ru/film/42/" in text


def test_format_recommendations_with_watch_platforms():
    movies = [
        MovieItem(
            id=42,
            title="Тестовый фильм",
            year=2021,
            rating=8.1,
            countries=["Россия"],
            genres=["детектив"],
            description="Описание на русском.",
            is_series=False,
            watch_platforms=[
                WatchPlatform(name="Иви", url="https://ivi.ru/watch/1"),
                WatchPlatform(name="START", url="https://start.ru/watch/1"),
            ],
        )
    ]
    text = format_recommendations(movies, "movie", requested=1)

    assert "Где смотреть:" in text
    assert "IVI: https://ivi.ru/watch/1" in text
    assert "START: https://start.ru/watch/1" in text


def test_format_compact_caption():
    movie = MovieItem(
        id=1,
        title="Новинка",
        year=2025,
        tmdb_rating=8.4,
    )
    caption = format_compact_caption(movie, rating_label="8.4")
    assert "Новинка (2025)" in caption
    assert "⭐ 8.4" in caption
