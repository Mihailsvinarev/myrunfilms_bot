from telegram import Update
from telegram.ext import ContextTypes

from app.keyboards import MAIN_KEYBOARD


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я подбираю фильмы и сериалы через Kinopoisk.\n\n"
        "🎬 Подборки — готовые списки с выбором жанра и листанием карточек.\n"
        "Текстовый запрос — просто напишите сообщение, например: "
        "«3 детективных сериала России 2021».\n\n"
        "Расширенный подбор: /filters\n"
        "Отмена подбора: /cancel",
        reply_markup=MAIN_KEYBOARD,
    )
