import logging
import os

from dotenv import load_dotenv
from telegram.error import Conflict
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from app.agent import MovieAgent
from app.bot_handlers import (
    build_filter_conversation,
    build_text_search_handler,
    start_command,
    text_search_hint,
)
from app.keyboards import MAIN_KEYBOARD
from app.logging_setup import setup_logging

load_dotenv()
setup_logging()

logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
agent = MovieAgent()


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

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(build_filter_conversation(agent))
    app.add_handler(
        MessageHandler(
            filters.Regex(r"^🔍 Поиск по тексту$"),
            text_search_hint,
        )
    )
    app.add_handler(build_text_search_handler(agent))
    app.add_error_handler(error_handler)

    logger.info("Movie AI Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
