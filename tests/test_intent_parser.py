import pytest

from app.query_parser import parse_query_mode, parse_search_filters, parse_title_query
from app.title_matching import title_matches


def test_parse_query_mode_title():
    assert parse_query_mode("Интерстеллар") == "title"
    assert parse_title_query("Интерстеллар", "title") == "Интерстеллар"


def test_parse_query_mode_similar():
    assert parse_query_mode("похожие на Интерстеллар") == "similar"
    assert parse_title_query("фильмы в стиле Интерстеллар", "similar") == "Интерстеллар"
    assert parse_title_query("5 фильмов как Interstellar", "similar") == "Interstellar"


def test_parse_query_mode_filter():
    assert parse_query_mode("3 детективных сериала России 2021") == "filter"
    assert parse_query_mode("Сериалы Netflix 2025") == "filter"


def test_parse_search_filters_title_does_not_restrict_media_type():
    filters = parse_search_filters("Интерстеллар")
    assert filters.query_mode == "title"
    assert filters.title_query == "Интерстеллар"
    assert filters.restrict_media_type is False
    assert filters.is_series is None


@pytest.mark.parametrize(
    "query,title,alternative,expected",
    [
        ("Интерстеллар", "Интерстеллар", "Interstellar", True),
        ("Interstellar", "Интерстеллар", "Interstellar", True),
        ("Интерстеллар", "Интерстеллар 5555", "Interstella 5555", False),
        ("Интерстеллар", "Наука «Интерстеллар»", "The Science of Interstellar", False),
    ],
)
def test_title_matches(query, title, alternative, expected):
    assert title_matches(query, title, alternative) is expected
