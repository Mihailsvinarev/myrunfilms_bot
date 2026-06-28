from unittest.mock import patch

from app.context_builder import build_recommendation_cards


@patch("app.context_builder.get_details")
def test_build_recommendation_cards_skips_excluded_and_non_russian(
    mock_get_details,
    sample_tv_discover_item,
    sample_tv_details,
):
    mock_get_details.return_value = sample_tv_details
    animation_item = {**sample_tv_discover_item, "id": 222, "genre_ids": [16]}

    cards = build_recommendation_cards(
        [animation_item, sample_tv_discover_item],
        "tv",
        limit=5,
    )

    assert len(cards) == 1
    assert cards[0].title == "Тестовый сериал"
    assert cards[0].kinopoisk_url.startswith("https://www.kinopoisk.ru/")


@patch("app.context_builder.get_details")
def test_build_recommendation_cards_respects_limit_without_padding(
    mock_get_details,
    sample_tv_discover_item,
    sample_tv_details,
):
    mock_get_details.return_value = sample_tv_details
    items = [{**sample_tv_discover_item, "id": i} for i in range(1, 8)]

    cards = build_recommendation_cards(items, "tv", limit=3)

    assert len(cards) == 3

