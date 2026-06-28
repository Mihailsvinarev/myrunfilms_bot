from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from app.tmdb_client import COUNTRY_NAMES

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [["🔍 Поиск по тексту", "⚙️ Подбор по фильтрам"]],
    resize_keyboard=True,
)

GENRE_OPTIONS: list[tuple[str, list[int] | None]] = [
    ("🕵 Детектив", [80, 9648]),
    ("😂 Комедия", [35]),
    ("🎭 Драма", [18]),
    ("👻 Ужасы", [27]),
    ("🚀 Фантастика", [878]),
    ("💥 Боевик", [28]),
    ("💘 Мелодрама", [10749]),
    ("🔪 Триллер", [53]),
]

YEAR_OPTIONS = [2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018]

COMPANY_PRESETS: list[tuple[str, str]] = [
    ("Netflix", "Netflix"),
    ("Marvel", "Marvel"),
    ("HBO", "HBO"),
    ("Disney", "Disney"),
    ("Warner", "Warner Bros"),
    ("Amazon", "Amazon Studios"),
]


def genre_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for label, ids in GENRE_OPTIONS:
        data = "genre:skip" if ids is None else "genre:" + "|".join(str(i) for i in ids)
        row.append(InlineKeyboardButton(label, callback_data=data))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("⏭ Пропустить", callback_data="genre:skip")])
    return InlineKeyboardMarkup(rows)


def year_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for year in YEAR_OPTIONS:
        row.append(InlineKeyboardButton(str(year), callback_data=f"year:{year}"))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("⏭ Пропустить", callback_data="year:skip")])
    return InlineKeyboardMarkup(rows)


def country_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for iso, name in COUNTRY_NAMES.items():
        row.append(InlineKeyboardButton(name, callback_data=f"country:{iso}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("⏭ Пропустить", callback_data="country:skip")])
    return InlineKeyboardMarkup(rows)


def media_keyboard(exclude_animation: bool) -> InlineKeyboardMarkup:
    anim_label = (
        "✅ Без мультфильмов"
        if exclude_animation
        else "⬜ Без мультфильмов"
    )
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🎬 Фильм", callback_data="media:movie"),
                InlineKeyboardButton("📺 Сериал", callback_data="media:tv"),
            ],
            [InlineKeyboardButton(anim_label, callback_data="anim:toggle")],
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
