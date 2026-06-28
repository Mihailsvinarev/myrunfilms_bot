import pytest

from app.tmdb_client import (
    country_label,
    is_director_request,
    parse_count,
    parse_country_iso,
    parse_genres,
    parse_media_type,
    parse_year,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("3 детективных сериала России за 2021", 3),
        ("подбери пять фильмов", 5),
        ("три сериала детектив", 3),
        ("фильм комедия 2015", 5),
        ("дай 10 вариантов сериал", 10),
        ("один фильм ужасов", 1),
    ],
)
def test_parse_count(text, expected):
    assert parse_count(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("российский сериал", "tv"),
        ("фильм боевик", "movie"),
        ("детектив 2020", "movie"),
    ],
)
def test_parse_media_type(text, expected):
    assert parse_media_type(text) == expected


def test_parse_year():
    assert parse_year("сериал 2021 год") == 2021
    assert parse_year("без года") is None


def test_parse_country_genitive():
    assert parse_country_iso("сериалы России") == "RU"
    assert parse_country_iso("корейский сериал") == "KR"
    assert parse_country_iso("французский фильм") == "FR"
    assert parse_country_iso("без страны") is None


def test_parse_genres_detective():
    assert parse_genres("детективный сериал") == [80, 9648]


def test_parse_year_does_not_affect_count():
    assert parse_count("3 сериала за 2021 год") == 3


def test_country_label():
    assert country_label("RU") == "Россия"
    assert country_label(None) is None


def test_is_director_request():
    assert is_director_request("фильмы режиссёра Нолана")
    assert not is_director_request("3 сериала России")
