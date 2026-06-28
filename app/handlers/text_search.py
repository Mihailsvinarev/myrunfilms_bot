import logging
import re

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from app.handlers.common import get_agent, send_long_reply
from app.keyboards import MAIN_KEYBOARD

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

        await update.message.reply_text("Ищу в Kinopoisk...")

        try:
            agent = get_agent(context)
            answer = await agent.ask(user_text)
            await send_long_reply(update.message, answer)
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
