import pytest

from app.tmdb_client import (
    parse_company,
    parse_exclude_animation,
    resolve_network_id,
    _discover_params,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("фильмы Netflix", "Netflix"),
        ("сериалы HBO 2020", "HBO"),
        ("Сериалы Netflix 2025", "Netflix"),
        ("MARVEL без мультфильмов", "Marvel"),
        ("обычный запрос", None),
    ],
)
def test_parse_company(text, expected):
    assert parse_company(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Marvel без мультфильмов", True),
        ("фильм без мультиков", True),
        ("обычный фильм", False),
    ],
)
def test_parse_exclude_animation(text, expected):
    assert parse_exclude_animation(text) == expected


def test_discover_params_company_and_no_animation():
    params = _discover_params(
        year=2021,
        country_iso="US",
        genre_ids=[28],
        with_crew=None,
        exclude_animation=True,
        company_id=12345,
        year_key="primary_release_year",
    )
    assert params["without_genres"] == "16,99,10764"
    assert params["with_companies"] == "12345"


def test_resolve_network_id_netflix():
    assert resolve_network_id("Netflix") == 213


def test_discover_params_tv_network():
    params = _discover_params(
        year=2025,
        network_id=213,
        year_key="first_air_date_year",
        media_type="tv",
    )
    assert params["with_networks"] == "213"
    assert params["first_air_date_year"] == 2025
    assert params["vote_count.gte"] == 5
    assert "with_companies" not in params
