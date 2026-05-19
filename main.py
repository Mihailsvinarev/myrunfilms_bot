from telegram.ext import ApplicationBuilder, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes

from dotenv import load_dotenv
import os

from app.agent import MovieAgent

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

agent = MovieAgent()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_text = update.message.text

    await update.message.reply_text("🎬 Думаю над фильмами...")

    answer = agent.ask(user_text)

    await update.message.reply_text(answer)


app = (
    ApplicationBuilder()
    .token(TOKEN)
    .read_timeout(120)
    .write_timeout(120)
    .connect_timeout(120)
    .pool_timeout(120)
    .build()
)

app.add_handler(MessageHandler(filters.TEXT, handle_message))

print("Movie AI Bot started...")

app.run_polling()