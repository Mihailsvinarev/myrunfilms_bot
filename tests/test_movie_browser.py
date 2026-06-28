import random

from app.genres import PARSER_GENRE_KEYWORDS, filter_genres, get_genre
from app.models import MovieItem
from app.movie_browser import (
    MovieBrowserState,
    build_browser_keyboard,
    can_go_next,
    can_go_prev,
    format_movie_card_caption,
    has_poster,
    next_index,
    prev_index,
    random_index,
)
from app.telegram_utils import DESCRIPTION_MAX_LENGTH


def _movie(
    *,
    movie_id: int = 1,
    title: str = "Фильм",
    poster_url: str | None = "https://example.com/poster.jpg",
    description: str = "Описание",
    genres: list[str] | None = None,
) -> MovieItem:
    return MovieItem(
        id=movie_id,
        title=title,
        year=2025,
        kp_rating=7.2,
        genres=genres or ["драма"],
        countries=["Россия"],
        description=description,
        poster_url=poster_url,
    )


def test_next_index_moves_forward():
    assert next_index(0, 3) == 1
    assert next_index(1, 3) == 2


def test_next_index_stops_at_end():
    assert next_index(2, 3) is None


def test_prev_index_moves_backward():
    assert prev_index(2, 3) == 1
    assert prev_index(1, 3) == 0


def test_prev_index_stops_at_start():
    assert prev_index(0, 3) is None


def test_can_go_flags():
    assert can_go_prev(0, 3) is False
    assert can_go_next(2, 3) is False
    assert can_go_prev(1, 3) is True
    assert can_go_next(0, 3) is True


def test_single_item_navigation_is_blocked():
    assert next_index(0, 1) is None
    assert prev_index(0, 1) is None
    assert can_go_next(0, 1) is False
    assert can_go_prev(0, 1) is False


def test_random_index_stays_in_bounds():
    random.seed(0)
    for _ in range(20):
        index = random_index(5, current=0)
        assert 0 <= index < 5
        assert index != 0


def test_random_index_on_empty_list():
    assert random_index(0) == 0


def test_empty_state_from_user_data():
    assert MovieBrowserState.from_user_data({"movies": []}) is None
    assert MovieBrowserState.from_user_data(None) is None


def test_state_roundtrip_preserves_index():
    movie = _movie()
    state = MovieBrowserState(
        collection_id="new_russian_movies",
        genre_id="detective",
        movies=[movie],
        index=0,
        message_id=42,
        chat_id=100,
        text_mode=True,
    )
    restored = MovieBrowserState.from_user_data(state.to_user_data())
    assert restored is not None
    assert restored.collection_id == "new_russian_movies"
    assert restored.genre_id == "detective"
    assert restored.index == 0
    assert restored.message_id == 42
    assert restored.chat_id == 100
    assert restored.text_mode is True
    assert restored.current_movie().title == "Фильм"


def test_has_poster():
    assert has_poster(_movie(poster_url="https://example.com/poster.jpg")) is True
    assert has_poster(_movie(poster_url=None)) is False
    assert has_poster(_movie(poster_url="   ")) is False


def test_format_movie_card_caption_contains_fields():
    caption = format_movie_card_caption(_movie(title="Холоп 3"), index=0, total=1)
    assert "🎬 Холоп 3" in caption
    assert "⭐ 7.2" in caption
    assert "📅 2025" in caption
    assert "🌍 Россия" in caption
    assert "🎭 драма" in caption
    assert "📝 Описание" in caption
    assert "🔗 https://www.kinopoisk.ru/film/1/" in caption


def test_format_movie_card_shows_position_for_multiple_items():
    caption = format_movie_card_caption(_movie(), index=1, total=3)
    assert "📍 2 / 3" in caption


def test_format_movie_card_truncates_long_description():
    long_text = "а" * (DESCRIPTION_MAX_LENGTH + 50)
    caption = format_movie_card_caption(_movie(description=long_text), index=0, total=1)
    description_line = next(
        line for line in caption.splitlines() if line.startswith("📝 ")
    )
    assert len(description_line) <= DESCRIPTION_MAX_LENGTH + len("📝 ")


def test_build_browser_keyboard_disables_edges():
    movie = _movie()
    keyboard = build_browser_keyboard(movie, index=0, total=1)
    prev_data = keyboard.inline_keyboard[0][0].callback_data
    next_data = keyboard.inline_keyboard[0][1].callback_data
    assert prev_data == "browser:noop:prev"
    assert next_data == "browser:noop:next"


def test_parser_genres_include_filter_only_thriller():
    assert get_genre("thriller") is None
    assert "триллер" in PARSER_GENRE_KEYWORDS
    assert any(genre.id == "thriller" for genre in filter_genres())
