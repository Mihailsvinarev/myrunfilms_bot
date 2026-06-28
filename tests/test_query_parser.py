import pytest

from app.query_parser import (
    country_name_from_iso,
    parse_company,
    parse_count,
    parse_country_name,
    parse_genre_names,
    parse_search_filters,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("3 детективных сериала России за 2021", 3),
        ("подбери пять фильмов", 5),
        ("три сериала детектив", 3),
        ("фильм комедия 2015", 5),
    ],
)
def test_parse_count(text, expected):
    assert parse_count(text) == expected


def test_parse_search_filters_netflix_tv():
    filters = parse_search_filters("Сериалы Netflix 2025")
    assert filters.media_type == "tv"
    assert filters.year == 2025
    assert filters.company_query == "Netflix"


def test_parse_country_genitive():
    assert parse_country_name("сериалы России") == "Россия"
    assert country_name_from_iso("RU") == "Россия"


def test_parse_genres_detective():
    assert parse_genre_names("детективный сериал") == ["детектив"]


def test_parse_company():
    assert parse_company("фильмы Netflix") == "Netflix"
