import pytest


@pytest.fixture
def sample_tv_discover_item():
    return {
        "id": 111,
        "name": "Тестовый сериал",
        "origin_country": ["RU"],
        "first_air_date": "2021-03-01",
        "vote_average": 7.5,
        "overview": "Краткое описание из discover",
    }


@pytest.fixture
def sample_tv_details():
    return {
        "name": "Тестовый сериал",
        "first_air_date": "2021-03-01",
        "vote_average": 7.8,
        "origin_country": ["RU"],
        "genres": [{"name": "Детектив"}, {"name": "Драма"}],
        "overview": "Полное описание сериала из TMDB.",
        "credits": {
            "cast": [{"name": "Актёр Один"}],
            "crew": [{"job": "Director", "name": "Режиссёр"}],
        },
    }
