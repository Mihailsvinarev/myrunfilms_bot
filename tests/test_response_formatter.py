from app.response_formatter import RecommendationCard, format_recommendations

KP = "https://www.kinopoisk.ru/index.php?kp_query=test"


def test_format_recommendations_full_count():
    cards = [
        RecommendationCard(
            title="Сериал А",
            year="2021",
            rating="7.5",
            countries="Россия",
            genres="Детектив",
            overview="Описание А",
            kinopoisk_url=KP,
        ),
        RecommendationCard(
            title="Сериал Б",
            year="2021",
            rating="8.0",
            countries="Россия",
            genres="Детектив",
            overview="",
            kinopoisk_url=KP,
        ),
    ]
    text = format_recommendations(cards, "tv", requested=2)
    assert "Подборка из 2 сериалов" in text
    assert "Сериал А" in text
    assert "Кинопоиск:" in text
    assert "kinopoisk.ru" in text


def test_format_recommendations_partial_count():
    cards = [
        RecommendationCard(
            title="Сериал А",
            year="2021",
            rating="7.5",
            countries="Россия",
            genres="Детектив",
            overview="Описание",
            kinopoisk_url=KP,
        ),
    ]
    text = format_recommendations(cards, "tv", requested=3)
    assert "Нашёл 1 из 3 запрошенных сериалов" in text


def test_format_recommendations_empty():
    assert format_recommendations([], "movie", requested=5) == ""
