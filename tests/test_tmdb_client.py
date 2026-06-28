from unittest.mock import patch

from app.tmdb_client import (
    _discover_params,
    _filter_by_origin_country,
    _genre_param,
    discover_tv,
    format_countries,
)


def test_genre_param_or_join():
    assert _genre_param([80, 9648]) == "80|9648"
    assert _genre_param(None) is None


def test_discover_params_tv_year_and_country():
    params = _discover_params(
        year=2021,
        country_iso="RU",
        genre_ids=[80, 9648],
        with_crew=None,
        year_key="first_air_date_year",
    )
    assert params["first_air_date_year"] == 2021
    assert params["with_origin_country"] == "RU"
    assert params["with_genres"] == "80|9648"


def test_filter_by_origin_country():
    items = [
        {"id": 1, "origin_country": ["RU"]},
        {"id": 2, "origin_country": ["KR"]},
        {"id": 3, "origin_country": ["RU", "US"]},
    ]
    filtered = _filter_by_origin_country(items, "RU")
    assert [i["id"] for i in filtered] == [1, 3]


def test_format_countries_tv_and_movie():
    assert format_countries({"origin_country": ["RU"]}, "tv") == "Россия"
    assert (
        format_countries(
            {"production_countries": [{"name": "США"}]},
            "movie",
        )
        == "США"
    )


@patch("app.tmdb_client._get")
def test_discover_tv_applies_country_post_filter(mock_get):
    mock_get.return_value = {
        "results": [
            {"id": 1, "name": "RU Show", "origin_country": ["RU"]},
            {"id": 2, "name": "KR Show", "origin_country": ["KR"]},
        ]
    }
    results = discover_tv(year=2021, country_iso="RU", genre_ids=[80])
    assert len(results) == 1
    assert results[0]["id"] == 1
    mock_get.assert_called_once()
