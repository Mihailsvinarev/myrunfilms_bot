from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from app.collections import COLLECTIONS
from app.genres import (
    GENRES,
    build_collection_callback,
    build_collection_genre_callback,
    filter_genres,
)
from app.query_parser import COUNTRY_ISO_TO_NAME

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [["🎬 Подборки"]],
    resize_keyboard=True,
)

GENRE_OPTIONS = filter_genres()

YEAR_OPTIONS = [2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018]

COMPANY_PRESETS: list[tuple[str, str]] = [
    ("Netflix", "Netflix"),
    ("Marvel", "Marvel"),
    ("HBO", "HBO"),
    ("Disney", "Disney"),
    ("Warner", "Warner"),
    ("Amazon", "Amazon"),
]


def genre_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for genre in GENRE_OPTIONS:
        data = "genre:" + "|".join([genre.kinopoisk_value or ""])
        row.append(InlineKeyboardButton(genre.title, callback_data=data))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("⏭ Пропустить", callback_data="genre:skip")])
    return InlineKeyboardMarkup(rows)


def year_keyboard(selected_years: list[int] | None = None) -> InlineKeyboardMarkup:
    selected = set(selected_years or [])
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for year in YEAR_OPTIONS:
        label = f"✅ {year}" if year in selected else str(year)
        row.append(InlineKeyboardButton(label, callback_data=f"year:toggle:{year}"))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append(
        [
            InlineKeyboardButton("Готово →", callback_data="year:done"),
            InlineKeyboardButton("⏭ Пропустить", callback_data="year:skip"),
        ]
    )
    return InlineKeyboardMarkup(rows)


def country_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for iso, name in COUNTRY_ISO_TO_NAME.items():
        row.append(InlineKeyboardButton(name, callback_data=f"country:{iso}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("⏭ Пропустить", callback_data="country:skip")])
    return InlineKeyboardMarkup(rows)


def media_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🎬 Фильм", callback_data="media:movie"),
                InlineKeyboardButton("📺 Сериал", callback_data="media:tv"),
            ],
            [InlineKeyboardButton("Далее →", callback_data="media:next")],
        ]
    )


def company_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for label, query in COMPANY_PRESETS:
        row.append(InlineKeyboardButton(label, callback_data=f"company:{query}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("⏭ Пропустить", callback_data="company:skip")])
    return InlineKeyboardMarkup(rows)


def collections_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for collection in COLLECTIONS:
        row.append(
            InlineKeyboardButton(
                collection.title,
                callback_data=build_collection_callback(collection.id),
            )
        )
        if len(row) == 1:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def collection_genres_keyboard(collection_id: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for genre in GENRES:
        row.append(
            InlineKeyboardButton(
                genre.title,
                callback_data=build_collection_genre_callback(collection_id, genre.id),
            )
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)
