import asyncio
import logging
import re

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.agent import MovieAgent
from app.keyboards import (
    MAIN_KEYBOARD,
    company_keyboard,
    country_keyboard,
    genre_keyboard,
    media_keyboard,
    year_keyboard,
)
from app.tmdb_client import parse_year

logger = logging.getLogger(__name__)

GENRE, YEAR, COUNTRY, MEDIA, COMPANY = range(5)

TEXT_SEARCH_HINT = (
    "Напишите запрос текстом, например:\n"
    "• 3 детективных сериала России 2021\n"
    "• фильмы Netflix\n"
    "• Marvel без мультфильмов\n"
    "• HBO сериал 2020"
)


def _default_filters() -> dict:
    return {
        "genre_ids": None,
        "year": None,
        "country_iso": None,
        "media_type": "movie",
        "exclude_animation": False,
        "company_query": None,
        "count": 5,
    }


def build_filter_conversation(agent: MovieAgent) -> ConversationHandler:
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
            context.user_data["filters"]["genre_ids"] = [
                int(part) for part in data.split("|")
            ]
        await query.edit_message_text(
            "Шаг 2/5 — год выхода.\n"
            "Выберите год, введите его текстом (например 2017) или нажмите «Пропустить»:",
            reply_markup=year_keyboard(),
        )
        return YEAR

    async def year_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        data = query.data.removeprefix("year:")
        if data != "skip":
            context.user_data["filters"]["year"] = int(data)
        await query.edit_message_text(
            "Шаг 3/5 — страна производства.\n"
            "Выберите страну или нажмите «Пропустить»:",
            reply_markup=country_keyboard(),
        )
        return COUNTRY

    async def year_typed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        year = parse_year(update.message.text)
        if year is None:
            await update.message.reply_text(
                "Не понял год. Введите, например: 2019",
                reply_markup=year_keyboard(),
            )
            return YEAR
        context.user_data["filters"]["year"] = year
        await update.message.reply_text(
            "Шаг 3/5 — страна производства.\n"
            "Выберите страну или нажмите «Пропустить»:",
            reply_markup=country_keyboard(),
        )
        return COUNTRY

    async def country_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        data = query.data.removeprefix("country:")
        if data != "skip":
            context.user_data["filters"]["country_iso"] = data
        exclude = context.user_data["filters"]["exclude_animation"]
        await query.edit_message_text(
            "Шаг 4/5 — тип и мультфильмы.\n"
            "Выберите формат, при необходимости включите «Без мультфильмов», "
            "затем нажмите «Далее»:",
            reply_markup=media_keyboard(exclude),
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

        elif data == "anim:toggle":
            filters_data["exclude_animation"] = not filters_data["exclude_animation"]

        await query.edit_message_text(
            "Шаг 4/5 — тип и мультфильмы.\n"
            "Выберите формат, при необходимости включите «Без мультфильмов», "
            "затем нажмите «Далее»:",
            reply_markup=media_keyboard(filters_data["exclude_animation"]),
        )
        return MEDIA

    async def company_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        data = query.data.removeprefix("company:")
        if data != "skip":
            context.user_data["filters"]["company_query"] = data
        return await _run_filter_search(query.message, context, agent)

    async def company_typed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = update.message.text.strip()
        if len(text) < 2:
            await update.message.reply_text(
                "Введите название студии или нажмите «Пропустить» на клавиатуре выше.",
                reply_markup=company_keyboard(),
            )
            return COMPANY
        context.user_data["filters"]["company_query"] = text
        return await _run_filter_search(update.message, context, agent)

    async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data.pop("filters", None)
        await update.message.reply_text(
            "Подбор отменён. Выберите режим ниже.",
            reply_markup=MAIN_KEYBOARD,
        )
        return ConversationHandler.END

    return ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(r"^⚙️ Подбор по фильтрам$"),
                start_filters,
            ),
            CommandHandler("filters", start_filters),
        ],
        states={
            GENRE: [CallbackQueryHandler(genre_chosen, pattern=r"^genre:")],
            YEAR: [
                CallbackQueryHandler(year_chosen, pattern=r"^year:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, year_typed),
            ],
            COUNTRY: [CallbackQueryHandler(country_chosen, pattern=r"^country:")],
            MEDIA: [CallbackQueryHandler(media_chosen, pattern=r"^(media:|anim:)")],
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


async def _run_filter_search(message, context: ContextTypes.DEFAULT_TYPE, agent: MovieAgent) -> int:
    await message.reply_text("Ищу в TMDB...")
    try:
        answer = await asyncio.to_thread(
            agent.search_from_filters,
            context.user_data.get("filters", {}),
        )
        await message.reply_text(answer, reply_markup=MAIN_KEYBOARD)
    except Exception:
        logger.exception("Filter search failed")
        await message.reply_text(
            "Произошла ошибка при поиске. Попробуйте снова.",
            reply_markup=MAIN_KEYBOARD,
        )
    context.user_data.pop("filters", None)
    return ConversationHandler.END


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я подбираю фильмы и сериалы через TMDB.\n\n"
        "⚙️ Подбор по фильтрам — пошаговый выбор жанра, года, страны, типа и студии.\n"
        "🔍 Поиск по тексту — свободный запрос, включая Netflix, Marvel, HBO.\n\n"
        "Отмена подбора: /cancel",
        reply_markup=MAIN_KEYBOARD,
    )


async def text_search_hint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(TEXT_SEARCH_HINT, reply_markup=MAIN_KEYBOARD)


MENU_BUTTONS = re.compile(r"^(🔍 Поиск по тексту|⚙️ Подбор по фильтрам|Отмена)$")


def build_text_search_handler(agent: MovieAgent) -> MessageHandler:
    async def handle_text_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return
        if MENU_BUTTONS.match(update.message.text):
            return

        user_text = update.message.text
        user_id = update.effective_user.id if update.effective_user else "unknown"
        logger.info("Text search from user_id=%s: %s", user_id, user_text[:120])

        await update.message.reply_text("Ищу в TMDB...")

        try:
            answer = await asyncio.to_thread(agent.ask, user_text)
            await update.message.reply_text(answer, reply_markup=MAIN_KEYBOARD)
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
