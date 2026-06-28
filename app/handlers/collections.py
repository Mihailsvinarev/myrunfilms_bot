from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes, MessageHandler, filters

from app.collections import get_collection
from app.genres import (
    get_genre,
    parse_collection_callback,
    parse_collection_genre_callback,
)
from app.handlers.common import get_agent
from app.keyboards import collection_genres_keyboard, collections_keyboard
from app.movie_browser import MovieBrowser


def build_collections_handler() -> MessageHandler:
    async def show_collections_menu(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not update.message:
            return
        await update.message.reply_text(
            "Выберите подборку:",
            reply_markup=collections_keyboard(),
        )

    return MessageHandler(filters.Regex(r"^🎬 Подборки$"), show_collections_menu)


def build_collection_callbacks() -> list[CallbackQueryHandler]:
    async def collection_chosen(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        query = update.callback_query
        await query.answer()
        collection_id = parse_collection_callback(query.data or "")
        collection = get_collection(collection_id) if collection_id else None
        if not collection:
            await query.edit_message_text("Неизвестная подборка.")
            return
        await query.edit_message_text(
            f"{collection.title}\n\nВыберите приоритетный жанр:",
            reply_markup=collection_genres_keyboard(collection.id),
        )

    async def collection_genre_chosen(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        query = update.callback_query
        await query.answer()
        parsed = parse_collection_genre_callback(query.data or "")
        if not parsed:
            await query.edit_message_text("Не удалось распознать выбор жанра.")
            return

        collection_id, genre_id = parsed
        collection = get_collection(collection_id)
        genre = get_genre(genre_id)
        if not collection or not genre:
            await query.edit_message_text("Неизвестная подборка или жанр.")
            return

        await query.edit_message_text("Ищу в Kinopoisk...")
        agent = get_agent(context)
        result = await agent.fetch_collection(collection_id, genre_id)
        if result.error:
            MovieBrowser.clear(context)
            await query.edit_message_text(result.error)
            return

        await MovieBrowser.open(
            query,
            context,
            collection_id=collection_id,
            genre_id=genre_id,
            movies=result.movies,
        )

    return [
        CallbackQueryHandler(collection_chosen, pattern=r"^collection:"),
        CallbackQueryHandler(collection_genre_chosen, pattern=r"^collection_genre:"),
    ]
