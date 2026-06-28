from app.content_filters import (
    build_kinopoisk_url,
    excluded_genres_param,
    filter_excluded_genres,
    has_excluded_genre,
    has_russian_overview,
)


def test_excluded_genres_param():
    assert excluded_genres_param() == "16,99,10764"


def test_has_excluded_genre_from_item():
    assert has_excluded_genre({"genre_ids": [16, 18]})
    assert has_excluded_genre({"genre_ids": [99]})
    assert has_excluded_genre({"genre_ids": [10764]})
    assert not has_excluded_genre({"genre_ids": [18, 35]})


def test_filter_excluded_genres():
    items = [
        {"id": 1, "genre_ids": [18]},
        {"id": 2, "genre_ids": [16]},
        {"id": 3, "genre_ids": [99]},
    ]
    filtered = filter_excluded_genres(items)
    assert [item["id"] for item in filtered] == [1]


def test_has_russian_overview():
    assert has_russian_overview({}, {"overview": "Русское описание фильма"})
    assert not has_russian_overview({}, {"overview": "English only overview"})
    assert not has_russian_overview({}, {"overview": ""})


def test_build_kinopoisk_url():
    url = build_kinopoisk_url("Игра престолов", "2011")
    assert url.startswith("https://www.kinopoisk.ru/index.php?kp_query=")
    assert "2011" in url
