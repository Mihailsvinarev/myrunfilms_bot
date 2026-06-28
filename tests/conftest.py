import pytest

from app.models import MovieItem


@pytest.fixture
def sample_movie() -> MovieItem:
    return MovieItem(
        id=111,
        title="Тестовый сериал",
        year=2021,
        rating=7.8,
        countries=["Россия"],
        genres=["детектив", "драма"],
        description="Полное описание сериала на русском языке.",
        is_series=True,
    )
