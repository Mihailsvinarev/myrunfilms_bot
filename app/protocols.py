from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.models import MovieItem, SearchFilters, SearchResult


class MovieRepository(Protocol):
    """Kinopoisk data access (search, fetch, enrich)."""

    async def search(self, filters: SearchFilters) -> list[MovieItem]: ...

    async def search_by_title(
        self, title: str, filters: SearchFilters
    ) -> list[MovieItem]: ...

    async def search_by_text(
        self, query: str, filters: SearchFilters
    ) -> list[MovieItem]: ...

    async def search_similar(
        self, reference_title: str, filters: SearchFilters
    ) -> list[MovieItem]: ...

    async def enrich_watchability(self, movies: list[MovieItem]) -> list[MovieItem]: ...

    async def fetch_by_params(
        self, params: list[tuple[str, str | int]]
    ) -> list[MovieItem]: ...

    async def close(self) -> None: ...


class NaturalLanguageQueryParser(Protocol):
    """Parses free-text user queries into SearchFilters (GigaChat + fallbacks)."""

    def is_available(self) -> bool: ...

    async def parse_query(self, text: str) -> Any: ...

    def to_search_filters(self, query: Any, user_text: str) -> SearchFilters: ...

    async def close(self) -> None: ...


@runtime_checkable
class MovieSearchService(Protocol):
    """Application service used by Telegram handlers."""

    async def ask(self, user_text: str) -> str: ...

    async def ask_movies(self, user_text: str) -> SearchResult: ...

    async def search(self, filters: SearchFilters) -> str: ...

    async def search_from_ui(self, data: dict) -> str: ...

    async def search_from_ui_movies(self, data: dict) -> SearchResult: ...

    async def fetch_collection(
        self, collection_id: str, genre_id: str
    ) -> SearchResult: ...

    async def close(self) -> None: ...
