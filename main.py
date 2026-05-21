import asyncio
import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.error import Conflict
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from app.agent import MovieAgent
from app.logging_setup import setup_logging

load_dotenv()
setup_logging()

logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
agent = MovieAgent()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    user_id = update.effective_user.id if update.effective_user else "unknown"
    logger.info("Message from user_id=%s: %s", user_id, user_text[:120])

    await update.message.reply_text("Думаю над фильмами...")

    try:
        answer = await asyncio.to_thread(agent.ask, user_text)
        await update.message.reply_text(answer)
        logger.info("Reply sent to user_id=%s", user_id)
    except Exception:
        logger.exception("Failed to process message from user_id=%s", user_id)
        await update.message.reply_text(
            "Произошла ошибка при обработке запроса. Попробуйте позже."
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error
    if isinstance(error, Conflict):
        logger.warning(
            "Conflict: another bot instance is polling (stop duplicate python main.py processes)"
        )
        return

    logger.error("Unhandled error: %s", error, exc_info=error)


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is not set in .env")

    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .read_timeout(120)
        .write_timeout(120)
        .connect_timeout(120)
        .pool_timeout(120)
        .build()
    )

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("Movie AI Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
