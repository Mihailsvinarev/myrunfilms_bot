import logging
import re

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from app.handlers.common import get_agent, present_search_results
from app.keyboards import MAIN_KEYBOARD
from app.movie_browser import TEXT_SEARCH_GENRE, TEXT_SEARCH_SOURCE

logger = logging.getLogger(__name__)

MENU_BUTTONS = re.compile(r"^(🎬 Подборки|Отмена)$")


def build_text_search_handler() -> MessageHandler:
    async def handle_text_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return
        if MENU_BUTTONS.match(update.message.text):
            return

        user_text = update.message.text
        user_id = update.effective_user.id if update.effective_user else "unknown"
        logger.info("Text search from user_id=%s: %s", user_id, user_text[:120])

        status_message = await update.message.reply_text("Ищу в Kinopoisk...")

        try:
            agent = get_agent(context)
            result = await agent.ask_movies(user_text)
            await present_search_results(
                update.message,
                context,
                result,
                source_id=TEXT_SEARCH_SOURCE,
                genre_id=TEXT_SEARCH_GENRE,
                status_message=status_message,
            )
        except Exception:
            logger.exception("Text search failed for user_id=%s", user_id)
            await update.message.reply_text(
                "Произошла ошибка при обработке запроса. Попробуйте позже.",
                reply_markup=MAIN_KEYBOARD,
            )

    return MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text_search,
    )
