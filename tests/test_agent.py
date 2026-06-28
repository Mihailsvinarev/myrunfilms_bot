from unittest.mock import patch

from app.agent import MovieAgent
from app.messages import no_results_message


def test_no_results_message():
    msg = no_results_message("tv", 2021, "RU", [80, 9648])
    assert "сериалов" in msg
    assert "2021" in msg
    assert "Россия" in msg
    assert "жанром" in msg


@patch("app.agent.build_recommendation_cards")
@patch("app.agent.discover")
def test_agent_ask_formats_without_llm(mock_discover, mock_build_cards):
    mock_discover.return_value = [
        {"id": 1, "name": "Сериал", "origin_country": ["RU"]},
    ]
    from app.response_formatter import RecommendationCard

    mock_build_cards.return_value = [
        RecommendationCard(
            title="Сериал",
            year="2021",
            rating="8.0",
            countries="Россия",
            genres="Детектив",
            overview="Описание",
            kinopoisk_url="https://www.kinopoisk.ru/index.php?kp_query=test",
        ),
    ]

    answer = MovieAgent().ask("3 детективных сериала России за 2021")

    assert "Сериал" in answer
    assert "Россия" in answer
    mock_discover.assert_called_once()
    call_kwargs = mock_discover.call_args.kwargs
    assert call_kwargs["country_iso"] == "RU"
    assert call_kwargs["year"] == 2021
    mock_build_cards.assert_called_once()
    assert mock_build_cards.call_args.kwargs["limit"] == 3


@patch("app.agent.build_recommendation_cards")
@patch("app.agent.discover")
def test_agent_ask_netflix_tv_uses_network(mock_discover, mock_build_cards):
    from app.response_formatter import RecommendationCard

    mock_discover.return_value = [{"id": 1, "name": "Show"}]
    mock_build_cards.return_value = [
        RecommendationCard(
            title="Show",
            year="2025",
            rating="8.0",
            countries="США",
            genres="Драма",
            overview="Описание сериала",
            kinopoisk_url="https://www.kinopoisk.ru/index.php?kp_query=test",
        ),
    ]

    MovieAgent().ask("Сериалы Netflix 2025")

    kwargs = mock_discover.call_args.kwargs
    assert kwargs["network_id"] == 213
    assert kwargs.get("company_id") is None
    assert kwargs["year"] == 2025


@patch("app.agent.search_person")
@patch("app.agent.discover")
def test_agent_director_not_found(mock_discover, mock_search_person):
    mock_search_person.return_value = []
    answer = MovieAgent().ask("фильмы режиссёра Неизвестный")
    assert "режиссёра" in answer.lower()
    mock_discover.assert_not_called()
