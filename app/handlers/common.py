from __future__ import annotations

from app.agent import MovieAgent
from app.keyboards import MAIN_KEYBOARD
from app.telegram_utils import split_telegram_message

AGENT_KEY = "agent"


def get_agent(context) -> MovieAgent:
    agent = context.application.bot_data.get(AGENT_KEY)
    if not isinstance(agent, MovieAgent):
        raise RuntimeError("MovieAgent is not configured in application.bot_data")
    return agent


async def send_long_reply(message, text: str, *, reply_markup=MAIN_KEYBOARD) -> None:
    chunks = split_telegram_message(text)
    for index, chunk in enumerate(chunks):
        await message.reply_text(
            chunk,
            reply_markup=reply_markup if index == len(chunks) - 1 else None,
        )
