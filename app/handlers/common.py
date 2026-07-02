from __future__ import annotations

from app.keyboards import MAIN_KEYBOARD
from app.models import SearchResult
from app.movie_browser import MovieBrowser
from app.protocols import MovieSearchService
from app.telegram_utils import split_telegram_message

AGENT_KEY = "agent"


def get_agent(context) -> MovieSearchService:
    agent = context.application.bot_data.get(AGENT_KEY)
    if not isinstance(agent, MovieSearchService):
        raise RuntimeError(
            "MovieSearchService is not configured in application.bot_data"
        )
    return agent


async def present_search_results(
    message,
    context,
    result: SearchResult,
    *,
    source_id: str,
    genre_id: str,
    status_message=None,
) -> None:
    if result.error:
        await message.reply_text(result.error, reply_markup=MAIN_KEYBOARD)
        return

    await MovieBrowser.open_from_message(
        message,
        context,
        source_id=source_id,
        genre_id=genre_id,
        movies=result.movies,
        header=result.header,
        status_message=status_message,
    )


async def send_long_reply(message, text: str, *, reply_markup=MAIN_KEYBOARD) -> None:
    chunks = split_telegram_message(text)
    for index, chunk in enumerate(chunks):
        await message.reply_text(
            chunk,
            reply_markup=reply_markup if index == len(chunks) - 1 else None,
        )
