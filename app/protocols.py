from __future__ import annotations

from typing import Protocol

from app.models import MovieItem, SearchFilters


class MovieRepository(Protocol):
    async def search(self, filters: SearchFilters) -> list[MovieItem]: ...

    async def search_by_title(
        self, title: str, filters: SearchFilters
    ) -> list[MovieItem]: ...

    async def search_by_text(
        self, text: str, filters: SearchFilters
    ) -> list[MovieItem]: ...

    async def search_similar(
        self, reference_title: str, filters: SearchFilters
    ) -> list[MovieItem]: ...

    async def enrich_watchability(self, movies: list[MovieItem]) -> list[MovieItem]: ...

    async def fetch_by_params(
        self, params: list[tuple[str, str | int]]
    ) -> list[MovieItem]: ...

    async def close(self) -> None: ...
