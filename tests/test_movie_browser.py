import random

from app.content_filters import has_poster
from app.genres import PARSER_GENRE_KEYWORDS, filter_genres, get_genre
from app.models import MovieItem
from app.movie_browser import MovieBrowserState
from app.telegram_cards import (
    BROWSER_COMPACT_CALLBACK,
    BROWSER_DETAILS_CALLBACK,
    DETAILS_DESCRIPTION_MAX_LENGTH,
    build_card_keyboard,
    build_compact_keyboard,
    build_details_keyboard,
    format_card_caption,
    format_compact_caption,
    format_details_caption,
    next_index,
    prev_index,
    random_index,
)


def _movie(
    *,
    movie_id: int = 1,
    title: str = "Фильм",
    poster_url: str | None = "https://example.com/poster.jpg",
    description: str = "Короткое описание фильма.",
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


def test_next_index_wraps_to_first_from_last():
    assert next_index(2, 3) == 0


def test_prev_index_wraps_to_last_from_first():
    assert prev_index(0, 3) == 2


def test_next_index_moves_forward():
    assert next_index(0, 3) == 1


def test_prev_index_moves_backward():
    assert prev_index(2, 3) == 1


def test_random_index_stays_in_bounds():
    random.seed(0)
    for _ in range(20):
        index = random_index(5, current=0)
        assert 0 <= index < 5
        assert index != 0


def test_random_index_on_empty_list():
    assert random_index(0) == 0


def test_compact_caption_contains_core_fields_without_description():
    caption = format_compact_caption(_movie(title="Холоп 3"), index=0, total=1)
    assert "🎬 Холоп 3" in caption
    assert "⭐ 7.2" in caption
    assert "📅 2025" in caption
    assert "🌍 Россия" in caption
    assert "🎭 драма" in caption
    assert "📝" not in caption
    assert "🔗" not in caption


def test_compact_caption_shows_position_for_multiple_items():
    caption = format_compact_caption(_movie(), index=1, total=3)
    assert "📍 2 / 3" in caption


def test_details_caption_contains_description_and_link():
    caption = format_details_caption(_movie(description="Подробное описание."))
    assert "📝 Подробное описание." in caption
    assert "🔗 https://www.kinopoisk.ru/film/1/" in caption


def test_details_caption_truncates_long_description():
    long_text = "а" * (DETAILS_DESCRIPTION_MAX_LENGTH + 50)
    caption = format_details_caption(_movie(description=long_text))
    description_line = next(
        line for line in caption.splitlines() if line.startswith("📝 ")
    )
    assert len(description_line) <= DETAILS_DESCRIPTION_MAX_LENGTH + len("📝 ")


def test_format_card_caption_switches_modes():
    movie = _movie()
    compact = format_card_caption(movie, index=0, total=2, mode="compact")
    details = format_card_caption(movie, index=0, total=2, mode="details")
    assert "📝" not in compact
    assert "📝" in details


def test_format_card_caption_includes_header_on_first_card():
    movie = _movie()
    caption = format_card_caption(
        movie,
        index=0,
        total=2,
        mode="compact",
        header="Похожие на «Интерстеллар»",
    )
    assert caption.startswith("Похожие на «Интерстеллар»")
    assert "🎬 Фильм" in caption

    next_caption = format_card_caption(
        movie,
        index=1,
        total=2,
        mode="compact",
        header="Похожие на «Интерстеллар»",
    )
    assert not next_caption.startswith("Похожие на «Интерстеллар»")


def test_build_compact_keyboard_layout():
    keyboard = build_compact_keyboard(_movie())
    labels = [button.text for row in keyboard.inline_keyboard for button in row]
    assert labels == [
        "⬅ Предыдущий",
        "➡ Следующий",
        "ℹ Подробнее",
        "🔗 Кинопоиск",
        "🎲 Случайный",
        "🎬 Подборки",
    ]


def test_build_details_keyboard_layout():
    keyboard = build_details_keyboard(_movie())
    labels = [button.text for row in keyboard.inline_keyboard for button in row]
    assert labels == [
        "⬅ Назад к карточке",
        "➡ Следующий",
        "🔗 Кинопоиск",
        "🎬 Подборки",
    ]


def test_build_compact_keyboard_without_menu_actions():
    keyboard = build_compact_keyboard(_movie(), include_menu_actions=False)
    labels = [button.text for row in keyboard.inline_keyboard for button in row]
    assert labels == [
        "⬅ Предыдущий",
        "➡ Следующий",
        "ℹ Подробнее",
        "🔗 Кинопоиск",
    ]


def test_build_details_keyboard_without_menu_actions():
    keyboard = build_details_keyboard(_movie(), include_menu_actions=False)
    labels = [button.text for row in keyboard.inline_keyboard for button in row]
    assert labels == [
        "⬅ Назад к карточке",
        "➡ Следующий",
        "🔗 Кинопоиск",
    ]


def test_build_card_keyboard_uses_mode():
    movie = _movie()
    compact = build_card_keyboard(movie, mode="compact")
    details = build_card_keyboard(movie, mode="details")
    assert compact.inline_keyboard[1][0].callback_data == BROWSER_DETAILS_CALLBACK
    assert details.inline_keyboard[0][0].callback_data == BROWSER_COMPACT_CALLBACK


def test_has_poster():
    assert has_poster(_movie(poster_url="https://example.com/poster.jpg")) is True
    assert has_poster(_movie(poster_url=None)) is False
    assert has_poster(_movie(poster_url="   ")) is False


def test_state_roundtrip_preserves_mode_and_index():
    movie = _movie()
    state = MovieBrowserState(
        collection_id="new_russian_movies",
        genre_id="detective",
        movies=[movie],
        index=0,
        display_mode="details",
        message_id=42,
        chat_id=100,
        text_mode=True,
    )
    restored = MovieBrowserState.from_user_data(state.to_user_data())
    assert restored is not None
    assert restored.display_mode == "details"
    assert restored.index == 0
    assert restored.current_movie().title == "Фильм"


def test_empty_state_from_user_data():
    assert MovieBrowserState.from_user_data({"movies": []}) is None
    assert MovieBrowserState.from_user_data(None) is None


def test_parser_genres_include_filter_only_thriller():
    assert get_genre("thriller") is None
    assert "триллер" in PARSER_GENRE_KEYWORDS
    assert any(genre.id == "thriller" for genre in filter_genres())
