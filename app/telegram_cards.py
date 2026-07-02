from __future__ import annotations

import random
from typing import Literal

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.models import MovieItem
from app.telegram_utils import truncate_description

DisplayMode = Literal["compact", "details"]
DETAILS_DESCRIPTION_MAX_LENGTH = 700

BROWSER_PREV_CALLBACK = "browser:prev"
BROWSER_NEXT_CALLBACK = "browser:next"
BROWSER_RANDOM_CALLBACK = "browser:random"
BROWSER_DETAILS_CALLBACK = "browser:details"
BROWSER_COMPACT_CALLBACK = "browser:compact"
BROWSER_COLLECTIONS_CALLBACK = "browser:collections"


def next_index(current: int, total: int) -> int:
    if total <= 0:
        return 0
    return (current + 1) % total


def prev_index(current: int, total: int) -> int:
    if total <= 0:
        return 0
    return (current - 1) % total


def random_index(total: int, *, current: int | None = None) -> int:
    if total <= 0:
        return 0
    if total == 1:
        return 0
    while True:
        picked = random.randint(0, total - 1)
        if current is None or picked != current:
            return picked


def format_position(*, index: int, total: int) -> str:
    if total <= 1:
        return ""
    return f"📍 {index + 1} / {total}\n\n"


def format_compact_caption(movie: MovieItem, *, index: int, total: int) -> str:
    year = str(movie.year) if movie.year else "—"
    rating = movie.kp_rating_label if movie.kp_rating is not None else "—"
    return (
        f"{format_position(index=index, total=total)}"
        f"🎬 {movie.title}\n"
        f"⭐ {rating}\n"
        f"📅 {year}\n"
        f"🌍 {movie.countries_label}\n"
        f"🎭 {movie.genres_label}"
    )


def format_details_caption(movie: MovieItem) -> str:
    year = str(movie.year) if movie.year else "—"
    rating = movie.kp_rating_label if movie.kp_rating is not None else "—"
    description = (
        truncate_description(
            movie.description,
            max_length=DETAILS_DESCRIPTION_MAX_LENGTH,
        )
        if movie.description.strip()
        else "—"
    )
    return (
        f"🎬 {movie.title}\n"
        f"⭐ {rating}\n"
        f"📅 {year}\n"
        f"🌍 {movie.countries_label}\n"
        f"🎭 {movie.genres_label}\n\n"
        f"📝 {description}\n\n"
        f"🔗 {movie.kinopoisk_url}"
    )


def format_card_caption(
    movie: MovieItem,
    *,
    index: int,
    total: int,
    mode: DisplayMode,
    header: str | None = None,
) -> str:
    if mode == "details":
        body = format_details_caption(movie)
    else:
        body = format_compact_caption(movie, index=index, total=total)
    if header and index == 0:
        return f"{header}\n\n{body}"
    return body


def build_compact_keyboard(
    movie: MovieItem,
    *,
    include_menu_actions: bool = True,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton("⬅ Предыдущий", callback_data=BROWSER_PREV_CALLBACK),
            InlineKeyboardButton("➡ Следующий", callback_data=BROWSER_NEXT_CALLBACK),
        ],
        [
            InlineKeyboardButton("ℹ Подробнее", callback_data=BROWSER_DETAILS_CALLBACK),
            InlineKeyboardButton("🔗 Кинопоиск", url=movie.kinopoisk_url),
        ],
    ]
    if include_menu_actions:
        rows.append(
            [
                InlineKeyboardButton(
                    "🎲 Случайный", callback_data=BROWSER_RANDOM_CALLBACK
                ),
                InlineKeyboardButton(
                    "🎬 Подборки", callback_data=BROWSER_COLLECTIONS_CALLBACK
                ),
            ]
        )
    return InlineKeyboardMarkup(rows)


def build_details_keyboard(
    movie: MovieItem,
    *,
    include_menu_actions: bool = True,
) -> InlineKeyboardMarkup:
    bottom_row = [InlineKeyboardButton("🔗 Кинопоиск", url=movie.kinopoisk_url)]
    if include_menu_actions:
        bottom_row.append(
            InlineKeyboardButton(
                "🎬 Подборки", callback_data=BROWSER_COLLECTIONS_CALLBACK
            )
        )
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⬅ Назад к карточке", callback_data=BROWSER_COMPACT_CALLBACK
                ),
                InlineKeyboardButton(
                    "➡ Следующий", callback_data=BROWSER_NEXT_CALLBACK
                ),
            ],
            bottom_row,
        ]
    )


def build_card_keyboard(
    movie: MovieItem,
    *,
    mode: DisplayMode,
    include_menu_actions: bool = True,
) -> InlineKeyboardMarkup:
    if mode == "details":
        return build_details_keyboard(movie, include_menu_actions=include_menu_actions)
    return build_compact_keyboard(movie, include_menu_actions=include_menu_actions)
