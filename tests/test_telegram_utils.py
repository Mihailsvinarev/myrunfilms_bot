from app.models import MovieItem
from app.response_formatter import format_recommendations
from app.telegram_utils import (
    TELEGRAM_MESSAGE_LIMIT,
    split_telegram_message,
    truncate_description,
)


def test_truncate_description():
    text = "а" * 400
    result = truncate_description(text, max_length=350)
    assert len(result) == 350
    assert result.endswith("…")


def test_format_recommendations_fits_telegram_limit():
    movies = [
        MovieItem(
            id=index,
            title=f"Сериал {index}",
            year=2026,
            rating=8.0,
            countries=["Россия"],
            genres=["детектив"],
            description="Описание на русском. " * 80,
            is_series=True,
        )
        for index in range(5)
    ]
    text = format_recommendations(movies, "tv", requested=5)
    assert all(
        len(chunk) <= TELEGRAM_MESSAGE_LIMIT for chunk in split_telegram_message(text)
    )


def test_split_telegram_message_on_long_text():
    text = "x" * 5000
    chunks = split_telegram_message(text, limit=1000)
    assert len(chunks) > 1
    assert all(len(chunk) <= 1000 for chunk in chunks)
