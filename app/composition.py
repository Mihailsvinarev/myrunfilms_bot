from __future__ import annotations

from dataclasses import dataclass

from app.agent import MovieAgent
from app.gigachat_client import GigaChatClient
from app.kinopoisk_client import KinopoiskClient
from app.protocols import MovieSearchService


@dataclass(frozen=True, slots=True)
class AppServices:
    """Composition root: wired dependencies for the Telegram bot."""

    search_service: MovieSearchService


def build_app_services() -> AppServices:
    client = KinopoiskClient()
    ai_parser = GigaChatClient()
    agent = MovieAgent(client=client, ai_parser=ai_parser)
    return AppServices(search_service=agent)
