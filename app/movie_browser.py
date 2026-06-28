from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Literal

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Update,
)
from telegram.error import BadRequest
from telegram.ext import CallbackQueryHandler, ContextTypes

from app.models import MovieItem
from app.telegram_utils import truncate_description

logger = logging.getLogger(__name__)

STATE_KEY = "movie_browser"
BROWSER_PREV_CALLBACK = "browser:prev"
BROWSER_NEXT_CALLBACK = "browser:next"
BROWSER_RANDOM_CALLBACK = "browser:random"
BROWSER_NOOP_PREV_CALLBACK = "browser:noop:prev"
BROWSER_NOOP_NEXT_CALLBACK = "browser:noop:next"

BrowserAction = Literal["prev", "next", "random"]
NOOP_MESSAGES = {
    "prev": "Это первый фильм в подборке.",
    "next": "Это последний фильм в подборке.",
}


@dataclass(slots=True)
class MovieBrowserState:
    collection_id: str
    genre_id: str
    movies: list[MovieItem]
    index: int = 0
    message_id: int | None = None
    chat_id: int | None = None
    text_mode: bool = False

    def current_movie(self) -> MovieItem:
        return self.movies[self.index]

    @property
    def total(self) -> int:
        return len(self.movies)

    def to_user_data(self) -> dict:
        return {
            "collection_id": self.collection_id,
            "genre_id": self.genre_id,
            "movies": [movie.model_dump() for movie in self.movies],
            "index": self.index,
            "message_id": self.message_id,
            "chat_id": self.chat_id,
            "text_mode": self.text_mode,
        }

    @classmethod
    def from_user_data(cls, data: dict | None) -> MovieBrowserState | None:
        if not data:
            return None
        movies_raw = data.get("movies") or []
        movies = [MovieItem.model_validate(item) for item in movies_raw]
        if not movies:
            return None
        return cls(
            collection_id=str(data["collection_id"]),
            genre_id=str(data["genre_id"]),
            movies=movies,
            index=int(data.get("index", 0)),
            message_id=data.get("message_id"),
            chat_id=data.get("chat_id"),
            text_mode=bool(data.get("text_mode", False)),
        )


def can_go_next(index: int, total: int) -> bool:
    return total > 0 and index < total - 1


def can_go_prev(index: int, total: int) -> bool:
    return total > 0 and index > 0


def next_index(current: int, total: int) -> int | None:
    if not can_go_next(current, total):
        return None
    return current + 1


def prev_index(current: int, total: int) -> int | None:
    if not can_go_prev(current, total):
        return None
    return current - 1


def random_index(total: int, *, current: int | None = None) -> int:
    if total <= 0:
        return 0
    if total == 1:
        return 0
    while True:
        picked = random.randint(0, total - 1)
        if current is None or picked != current:
            return picked


def has_poster(movie: MovieItem) -> bool:
    return bool(movie.poster_url and movie.poster_url.strip())


def format_movie_card_caption(movie: MovieItem, *, index: int, total: int) -> str:
    year = str(movie.year) if movie.year else "—"
    description = (
        truncate_description(movie.description) if movie.description.strip() else "—"
    )
    rating = movie.kp_rating_label if movie.kp_rating is not None else "—"
    position = f"📍 {index + 1} / {total}\n\n" if total > 1 else ""
    return (
        f"{position}"
        f"🎬 {movie.title}\n\n"
        f"⭐ {rating}\n"
        f"📅 {year}\n"
        f"🌍 {movie.countries_label}\n"
        f"🎭 {movie.genres_label}\n\n"
        f"📝 {description}\n\n"
        f"🔗 {movie.kinopoisk_url}"
    )


def build_browser_keyboard(
    movie: MovieItem,
    *,
    index: int,
    total: int,
) -> InlineKeyboardMarkup:
    prev_active = can_go_prev(index, total)
    next_active = can_go_next(index, total)
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⬅ Предыдущий" if prev_active else "▫️ Предыдущий",
                    callback_data=(
                        BROWSER_PREV_CALLBACK
                        if prev_active
                        else BROWSER_NOOP_PREV_CALLBACK
                    ),
                ),
                InlineKeyboardButton(
                    "➡ Следующий" if next_active else "▫️ Следующий",
                    callback_data=(
                        BROWSER_NEXT_CALLBACK
                        if next_active
                        else BROWSER_NOOP_NEXT_CALLBACK
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    "🎲 Другой случайный", callback_data=BROWSER_RANDOM_CALLBACK
                ),
                InlineKeyboardButton("🔗 Открыть Кинопоиск", url=movie.kinopoisk_url),
            ],
        ]
    )


def log_browser_state(state: MovieBrowserState, *, event: str) -> None:
    logger.info(
        "%s collection_id=%s genre_id=%s total=%d index=%d",
        event,
        state.collection_id,
        state.genre_id,
        len(state.movies),
        state.index,
    )


def _is_not_modified_error(exc: BadRequest) -> bool:
    return "message is not modified" in str(exc).lower()


class MovieBrowser:
    @staticmethod
    def load(context) -> MovieBrowserState | None:
        raw = context.user_data.get(STATE_KEY)
        if not isinstance(raw, dict):
            return None
        return MovieBrowserState.from_user_data(raw)

    @staticmethod
    def save(context, state: MovieBrowserState) -> None:
        context.user_data[STATE_KEY] = state.to_user_data()

    @staticmethod
    def clear(context) -> None:
        context.user_data.pop(STATE_KEY, None)

    @staticmethod
    async def open(
        query,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        collection_id: str,
        genre_id: str,
        movies: list[MovieItem],
    ) -> None:
        if not movies:
            MovieBrowser.clear(context)
            return

        state = MovieBrowserState(
            collection_id=collection_id,
            genre_id=genre_id,
            movies=movies,
            index=0,
        )
        chat_id = query.message.chat_id
        await query.message.delete()
        sent = await MovieBrowser._send_card(context, chat_id, state)
        state.message_id = sent.message_id
        state.chat_id = chat_id
        state.text_mode = sent.photo is None
        MovieBrowser.save(context, state)
        log_browser_state(state, event="Movie browser opened")

    @staticmethod
    async def navigate(
        query,
        context: ContextTypes.DEFAULT_TYPE,
        action: BrowserAction,
    ) -> None:
        state = MovieBrowser.load(context)
        if state is None:
            await query.answer("Подборка не найдена. Выберите подборку заново.")
            return

        total = state.total
        if action == "prev":
            new_index = prev_index(state.index, total)
            if new_index is None:
                await query.answer(NOOP_MESSAGES["prev"])
                return
            state.index = new_index
        elif action == "next":
            new_index = next_index(state.index, total)
            if new_index is None:
                await query.answer(NOOP_MESSAGES["next"])
                return
            state.index = new_index
        else:
            state.index = random_index(total, current=state.index)

        await query.answer()
        await MovieBrowser._update_card(query, context, state)
        MovieBrowser.save(context, state)
        log_browser_state(state, event="Movie browser navigate")

    @staticmethod
    async def noop(query, *, edge: Literal["prev", "next"]) -> None:
        await query.answer(NOOP_MESSAGES[edge])

    @staticmethod
    async def _send_card(context: ContextTypes.DEFAULT_TYPE, chat_id: int, state):
        movie = state.current_movie()
        caption = format_movie_card_caption(movie, index=state.index, total=state.total)
        keyboard = build_browser_keyboard(movie, index=state.index, total=state.total)
        bot = context.bot

        if has_poster(movie):
            try:
                return await bot.send_photo(
                    chat_id=chat_id,
                    photo=movie.poster_url,
                    caption=caption,
                    reply_markup=keyboard,
                )
            except BadRequest:
                logger.warning(
                    "Poster upload failed on open movie_id=%s, using text card",
                    movie.id,
                )

        return await bot.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=keyboard,
        )

    @staticmethod
    async def _update_card(
        query,
        context: ContextTypes.DEFAULT_TYPE,
        state: MovieBrowserState,
    ) -> None:
        movie = state.current_movie()
        caption = format_movie_card_caption(movie, index=state.index, total=state.total)
        keyboard = build_browser_keyboard(movie, index=state.index, total=state.total)
        wants_photo = has_poster(movie)

        if wants_photo and not state.text_mode:
            try:
                await query.edit_message_media(
                    media=InputMediaPhoto(
                        media=movie.poster_url,
                        caption=caption,
                    ),
                    reply_markup=keyboard,
                )
                return
            except BadRequest as exc:
                if _is_not_modified_error(exc):
                    await query.edit_message_reply_markup(reply_markup=keyboard)
                    return
                logger.warning(
                    "Poster edit failed movie_id=%s, falling back to text card",
                    movie.id,
                )
                state.text_mode = True

        if wants_photo and state.text_mode:
            await MovieBrowser._replace_message(
                query, context, state, caption, keyboard, photo=True
            )
            return

        if not wants_photo and not state.text_mode:
            await MovieBrowser._replace_message(
                query, context, state, caption, keyboard, photo=False
            )
            return

        try:
            await query.edit_message_text(text=caption, reply_markup=keyboard)
        except BadRequest as exc:
            if _is_not_modified_error(exc):
                await query.edit_message_reply_markup(reply_markup=keyboard)
                return
            raise

    @staticmethod
    async def _replace_message(
        query,
        context: ContextTypes.DEFAULT_TYPE,
        state: MovieBrowserState,
        caption: str,
        keyboard: InlineKeyboardMarkup,
        *,
        photo: bool,
    ) -> None:
        chat_id = query.message.chat_id
        movie = state.current_movie()
        await query.message.delete()

        if photo and has_poster(movie):
            try:
                sent = await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=movie.poster_url,
                    caption=caption,
                    reply_markup=keyboard,
                )
                state.text_mode = False
            except BadRequest:
                logger.warning(
                    "Poster replace failed movie_id=%s, using text card",
                    movie.id,
                )
                sent = await context.bot.send_message(
                    chat_id=chat_id,
                    text=caption,
                    reply_markup=keyboard,
                )
                state.text_mode = True
        else:
            sent = await context.bot.send_message(
                chat_id=chat_id,
                text=caption,
                reply_markup=keyboard,
            )
            state.text_mode = True

        state.message_id = sent.message_id
        state.chat_id = chat_id


def build_browser_handlers() -> list[CallbackQueryHandler]:
    async def browser_prev(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query:
            return
        await MovieBrowser.navigate(query, context, "prev")

    async def browser_next(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query:
            return
        await MovieBrowser.navigate(query, context, "next")

    async def browser_random(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        query = update.callback_query
        if not query:
            return
        await MovieBrowser.navigate(query, context, "random")

    async def browser_noop_prev(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        query = update.callback_query
        if query:
            await MovieBrowser.noop(query, edge="prev")

    async def browser_noop_next(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        query = update.callback_query
        if query:
            await MovieBrowser.noop(query, edge="next")

    return [
        CallbackQueryHandler(browser_prev, pattern=f"^{BROWSER_PREV_CALLBACK}$"),
        CallbackQueryHandler(browser_next, pattern=f"^{BROWSER_NEXT_CALLBACK}$"),
        CallbackQueryHandler(browser_random, pattern=f"^{BROWSER_RANDOM_CALLBACK}$"),
        CallbackQueryHandler(
            browser_noop_prev, pattern=f"^{BROWSER_NOOP_PREV_CALLBACK}$"
        ),
        CallbackQueryHandler(
            browser_noop_next, pattern=f"^{BROWSER_NOOP_NEXT_CALLBACK}$"
        ),
    ]
