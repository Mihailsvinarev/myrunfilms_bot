import logging

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.handlers.common import get_agent, present_search_results
from app.keyboards import (
    MAIN_KEYBOARD,
    company_keyboard,
    country_keyboard,
    genre_keyboard,
    media_keyboard,
    year_keyboard,
)
from app.movie_browser import FILTER_SEARCH_GENRE, FILTER_SEARCH_SOURCE
from app.query_parser import parse_year

logger = logging.getLogger(__name__)

GENRE, YEAR, COUNTRY, MEDIA, COMPANY = range(5)

YEAR_STEP_TEXT = (
    "Шаг 2/5 — годы выхода.\n"
    "Можно выбрать несколько, затем «Готово». "
    "Или введите год текстом и нажмите «Пропустить»:"
)


def _default_filters() -> dict:
    return {
        "genre_names": None,
        "years": [],
        "country_iso": None,
        "media_type": "movie",
        "company_query": None,
        "count": 5,
    }


async def _run_filter_search(message, context: ContextTypes.DEFAULT_TYPE) -> int:
    agent = get_agent(context)
    status_message = await message.reply_text("Ищу в Kinopoisk...")
    try:
        result = await agent.search_from_ui_movies(context.user_data.get("filters", {}))
        await present_search_results(
            message,
            context,
            result,
            source_id=FILTER_SEARCH_SOURCE,
            genre_id=FILTER_SEARCH_GENRE,
            status_message=status_message,
        )
    except Exception:
        logger.exception("Filter search failed")
        await message.reply_text(
            "Произошла ошибка при поиске. Попробуйте снова.",
            reply_markup=MAIN_KEYBOARD,
        )
    context.user_data.pop("filters", None)
    return ConversationHandler.END


def build_filter_conversation() -> ConversationHandler:
    async def start_filters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data["filters"] = _default_filters()
        await update.message.reply_text(
            "Шаг 1/5 — выберите жанр или нажмите «Пропустить»:",
            reply_markup=genre_keyboard(),
        )
        return GENRE

    async def genre_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        data = query.data.removeprefix("genre:")
        if data != "skip":
            context.user_data["filters"]["genre_names"] = data.split("|")
        await query.edit_message_text(
            YEAR_STEP_TEXT,
            reply_markup=year_keyboard(context.user_data["filters"].get("years")),
        )
        return YEAR

    async def year_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        data = query.data.removeprefix("year:")
        filters_data = context.user_data["filters"]

        if data == "skip":
            filters_data["years"] = []
        elif data == "done":
            if not filters_data.get("years"):
                filters_data["years"] = []
            await query.edit_message_text(
                "Шаг 3/5 — страна производства.\n"
                "Выберите страну или нажмите «Пропустить»:",
                reply_markup=country_keyboard(),
            )
            return COUNTRY
        elif data.startswith("toggle:"):
            year = int(data.removeprefix("toggle:"))
            years = filters_data.setdefault("years", [])
            if year in years:
                years.remove(year)
            else:
                years.append(year)
            await query.edit_message_text(
                YEAR_STEP_TEXT,
                reply_markup=year_keyboard(years),
            )
            return YEAR

        await query.edit_message_text(
            "Шаг 3/5 — страна производства.\n"
            "Выберите страну или нажмите «Пропустить»:",
            reply_markup=country_keyboard(),
        )
        return COUNTRY

    async def year_typed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        year = parse_year(update.message.text)
        if year is None:
            years = context.user_data["filters"].get("years", [])
            await update.message.reply_text(
                "Не понял год. Введите, например: 2019",
                reply_markup=year_keyboard(years),
            )
            return YEAR
        years = context.user_data["filters"].setdefault("years", [])
        if year not in years:
            years.append(year)
        await update.message.reply_text(
            YEAR_STEP_TEXT,
            reply_markup=year_keyboard(years),
        )
        return YEAR

    async def country_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        data = query.data.removeprefix("country:")
        if data != "skip":
            context.user_data["filters"]["country_iso"] = data
        await query.edit_message_text(
            "Шаг 4/5 — тип контента.\n" "Выберите формат и нажмите «Далее»:",
            reply_markup=media_keyboard(),
        )
        return MEDIA

    async def media_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        data = query.data
        filters_data = context.user_data["filters"]

        if data.startswith("media:"):
            action = data.removeprefix("media:")
            if action in ("movie", "tv"):
                filters_data["media_type"] = action
            elif action == "next":
                await query.edit_message_text(
                    "Шаг 5/5 — студия (Netflix, Marvel, HBO…).\n"
                    "Выберите из списка, введите название текстом или пропустите:",
                    reply_markup=company_keyboard(),
                )
                return COMPANY

        await query.edit_message_text(
            "Шаг 4/5 — тип контента.\n" "Выберите формат и нажмите «Далее»:",
            reply_markup=media_keyboard(),
        )
        return MEDIA

    async def company_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        data = query.data.removeprefix("company:")
        if data != "skip":
            context.user_data["filters"]["company_query"] = data
        return await _run_filter_search(query.message, context)

    async def company_typed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = update.message.text.strip()
        if len(text) < 2:
            await update.message.reply_text(
                "Введите название студии или нажмите «Пропустить» на клавиатуре выше.",
                reply_markup=company_keyboard(),
            )
            return COMPANY
        context.user_data["filters"]["company_query"] = text
        return await _run_filter_search(update.message, context)

    async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data.pop("filters", None)
        await update.message.reply_text(
            "Подбор отменён. Выберите режим ниже.",
            reply_markup=MAIN_KEYBOARD,
        )
        return ConversationHandler.END

    return ConversationHandler(
        entry_points=[CommandHandler("filters", start_filters)],
        states={
            GENRE: [CallbackQueryHandler(genre_chosen, pattern=r"^genre:")],
            YEAR: [
                CallbackQueryHandler(year_chosen, pattern=r"^year:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, year_typed),
            ],
            COUNTRY: [CallbackQueryHandler(country_chosen, pattern=r"^country:")],
            MEDIA: [CallbackQueryHandler(media_chosen, pattern=r"^media:")],
            COMPANY: [
                CallbackQueryHandler(company_chosen, pattern=r"^company:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, company_typed),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Regex(r"^Отмена$"), cancel),
        ],
        allow_reentry=True,
    )
