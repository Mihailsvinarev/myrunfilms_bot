from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from telegram import Update

from dotenv import load_dotenv
import os
import asyncio

from app.agent import MovieAgent

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

agent = MovieAgent()


# ---------------- HANDLER ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message or not update.message.text:
        return

    user_text = update.message.text

    await update.message.reply_text("🎬 Думаю над фильмами...")

    try:
        # 🔥 ВАЖНО: перенос блокирующего кода в thread
        answer = await asyncio.to_thread(agent.ask, user_text)

        await update.message.reply_text(answer)

    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}")


# ---------------- APP ----------------
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

print("🎬 Movie AI Bot started...")

app.run_polling()
