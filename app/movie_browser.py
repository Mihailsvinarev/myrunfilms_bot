from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from telegram import InputMediaPhoto, Update
from telegram.error import BadRequest
from telegram.ext import CallbackQueryHandler, ContextTypes

from app.content_filters import has_poster
from app.keyboards import collections_keyboard
from app.models import MovieItem
from app.telegram_cards import (
    BROWSER_COLLECTIONS_CALLBACK,
    BROWSER_COMPACT_CALLBACK,
    BROWSER_DETAILS_CALLBACK,
    BROWSER_NEXT_CALLBACK,
    BROWSER_PREV_CALLBACK,
    BROWSER_RANDOM_CALLBACK,
    DisplayMode,
    build_card_keyboard,
    format_card_caption,
    next_index,
    prev_index,
    random_index,
)

logger = logging.getLogger(__name__)

STATE_KEY = "movie_browser"
TEXT_SEARCH_SOURCE = "text_search"
TEXT_SEARCH_GENRE = "query"
FILTER_SEARCH_SOURCE = "filters"
FILTER_SEARCH_GENRE = "ui"
BrowserAction = Literal["prev", "next", "random"]


@dataclass(slots=True)
class MovieBrowserState:
    collection_id: str
    genre_id: str
    movies: list[MovieItem]
    index: int = 0
    display_mode: DisplayMode = "compact"
    header: str | None = None
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
            "display_mode": self.display_mode,
            "header": self.header,
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
        display_mode = data.get("display_mode", "compact")
        if display_mode not in ("compact", "details"):
            display_mode = "compact"
        return cls(
            collection_id=str(data["collection_id"]),
            genre_id=str(data["genre_id"]),
            movies=movies,
            index=int(data.get("index", 0)),
            display_mode=display_mode,
            header=data.get("header"),
            message_id=data.get("message_id"),
            chat_id=data.get("chat_id"),
            text_mode=bool(data.get("text_mode", False)),
        )


def log_browser_state(state: MovieBrowserState, *, event: str) -> None:
    logger.info(
        "%s collection_id=%s genre_id=%s total=%d index=%d mode=%s",
        event,
        state.collection_id,
        state.genre_id,
        len(state.movies),
        state.index,
        state.display_mode,
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
            display_mode="compact",
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
    async def open_from_message(
        message,
        context: ContextTypes.DEFAULT_TYPE,
        *,
        source_id: str,
        genre_id: str,
        movies: list[MovieItem],
        header: str | None = None,
        status_message=None,
    ) -> None:
        if not movies:
            MovieBrowser.clear(context)
            return

        if status_message is not None:
            try:
                await status_message.delete()
            except BadRequest:
                pass

        state = MovieBrowserState(
            collection_id=source_id,
            genre_id=genre_id,
            movies=movies,
            index=0,
            display_mode="compact",
            header=header,
        )
        chat_id = message.chat_id
        sent = await MovieBrowser._send_card(context, chat_id, state)
        state.message_id = sent.message_id
        state.chat_id = chat_id
        state.text_mode = sent.photo is None
        MovieBrowser.save(context, state)
        log_browser_state(state, event="Movie browser opened from message")

    @staticmethod
    async def navigate(
        query,
        context: ContextTypes.DEFAULT_TYPE,
        action: BrowserAction,
    ) -> None:
        state = MovieBrowser.load(context)
        if state is None:
            await query.answer("Список фильмов не найден. Начните поиск заново.")
            return

        total = state.total
        if action == "prev":
            state.index = prev_index(state.index, total)
        elif action == "next":
            state.index = next_index(state.index, total)
        else:
            state.index = random_index(total, current=state.index)

        await query.answer()
        await MovieBrowser._update_card(query, context, state)
        MovieBrowser.save(context, state)
        log_browser_state(state, event="Movie browser navigate")

    @staticmethod
    async def set_display_mode(
        query,
        context: ContextTypes.DEFAULT_TYPE,
        mode: DisplayMode,
    ) -> None:
        state = MovieBrowser.load(context)
        if state is None:
            await query.answer("Список фильмов не найден. Начните поиск заново.")
            return

        state.display_mode = mode
        await query.answer()
        await MovieBrowser._update_card(query, context, state)
        MovieBrowser.save(context, state)
        log_browser_state(state, event=f"Movie browser mode={mode}")

    @staticmethod
    async def show_collections_menu(
        query,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        MovieBrowser.clear(context)
        await query.answer()
        await query.edit_message_text(
            "Выберите подборку:",
            reply_markup=collections_keyboard(),
        )

    @staticmethod
    async def _send_card(context: ContextTypes.DEFAULT_TYPE, chat_id: int, state):
        movie = state.current_movie()
        caption = format_card_caption(
            movie,
            index=state.index,
            total=state.total,
            mode=state.display_mode,
            header=state.header,
        )
        keyboard = build_card_keyboard(
            movie,
            mode=state.display_mode,
            include_menu_actions=state.collection_id != TEXT_SEARCH_SOURCE,
        )
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
        caption = format_card_caption(
            movie,
            index=state.index,
            total=state.total,
            mode=state.display_mode,
            header=state.header,
        )
        keyboard = build_card_keyboard(
            movie,
            mode=state.display_mode,
            include_menu_actions=state.collection_id != TEXT_SEARCH_SOURCE,
        )
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
        keyboard,
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

    async def browser_details(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        query = update.callback_query
        if not query:
            return
        await MovieBrowser.set_display_mode(query, context, "details")

    async def browser_compact(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        query = update.callback_query
        if not query:
            return
        await MovieBrowser.set_display_mode(query, context, "compact")

    async def browser_collections(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        query = update.callback_query
        if not query:
            return
        await MovieBrowser.show_collections_menu(query, context)

    return [
        CallbackQueryHandler(browser_prev, pattern=f"^{BROWSER_PREV_CALLBACK}$"),
        CallbackQueryHandler(browser_next, pattern=f"^{BROWSER_NEXT_CALLBACK}$"),
        CallbackQueryHandler(browser_random, pattern=f"^{BROWSER_RANDOM_CALLBACK}$"),
        CallbackQueryHandler(browser_details, pattern=f"^{BROWSER_DETAILS_CALLBACK}$"),
        CallbackQueryHandler(browser_compact, pattern=f"^{BROWSER_COMPACT_CALLBACK}$"),
        CallbackQueryHandler(
            browser_collections, pattern=f"^{BROWSER_COLLECTIONS_CALLBACK}$"
        ),
    ]
