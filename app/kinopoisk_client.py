from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.config import KINOPOISK_API_KEY, KINOPOISK_BASE_URL
from app.models import MovieItem, SearchFilters, WatchPlatform
from app.title_matching import title_matches

logger = logging.getLogger(__name__)

ALWAYS_EXCLUDED_GENRES = ("мультфильм", "документальный", "ток-шоу")

# Студии/платформы, для которых в API есть фильтр networks.items.name
COMPANY_NETWORKS: dict[str, str] = {
    "Netflix": "Netflix",
    "HBO": "HBO",
}


class KinopoiskClient:
    def __init__(
        self, api_key: str | None = None, client: httpx.AsyncClient | None = None
    ):
        self.api_key = api_key or KINOPOISK_API_KEY
        self._client = client
        self._owns_client = client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=KINOPOISK_BASE_URL,
                headers={"X-API-KEY": self.api_key or ""},
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client and self._owns_client:
            await self._client.aclose()
            self._client = None

    async def search(self, filters: SearchFilters) -> list[MovieItem]:
        if not self.api_key:
            raise RuntimeError("KINOPOISK_API_KEY is not set in .env")

        fetch_limit = min(max(filters.count * 4, 20), 50)
        if filters.company_query and filters.company_query in COMPANY_NETWORKS:
            movies = await self._search_by_filters(filters, limit=fetch_limit)
            return self._apply_client_filters(
                movies, filters, skip_company_text_check=True
            )
        if filters.company_query:
            movies = await self._search_by_query(filters, limit=fetch_limit)
            return self._apply_client_filters(
                movies, filters, skip_company_text_check=True
            )

        movies = await self._search_by_filters(filters, limit=fetch_limit)
        return self._apply_client_filters(movies, filters)

    async def enrich_watchability(self, movies: list[MovieItem]) -> list[MovieItem]:
        if not movies:
            return movies

        client = await self._get_client()

        async def fetch_platforms(movie: MovieItem) -> MovieItem:
            try:
                response = await client.get(f"/movie/{movie.id}")
                response.raise_for_status()
                platforms = self._parse_watchability(response.json())
            except httpx.HTTPError:
                logger.warning("Failed to fetch watchability for movie %s", movie.id)
                return movie
            if not platforms:
                return movie
            return movie.model_copy(update={"watch_platforms": platforms})

        return list(await asyncio.gather(*(fetch_platforms(movie) for movie in movies)))

    async def search_by_title(
        self, title: str, filters: SearchFilters
    ) -> list[MovieItem]:
        client = await self._get_client()
        response = await client.get(
            "/movie/search",
            params={"query": title, "page": 1, "limit": 50},
        )
        response.raise_for_status()
        movies = [self._parse_item(item) for item in response.json().get("docs", [])]
        matched = [
            movie
            for movie in movies
            if title_matches(title, movie.title, movie.alternative_title)
        ]
        return self._apply_client_filters(matched, filters)

    async def search_similar(
        self, reference_title: str, filters: SearchFilters
    ) -> list[MovieItem]:
        reference_filters = filters.model_copy(
            update={
                "count": 1,
                "restrict_media_type": False,
                "query_mode": "title",
            }
        )
        references = await self.search_by_title(reference_title, reference_filters)
        if not references:
            return []

        reference = references[0]
        client = await self._get_client()
        response = await client.get(f"/movie/{reference.id}")
        response.raise_for_status()
        detail = response.json()
        genres = [
            genre.get("name", "")
            for genre in detail.get("genres") or []
            if genre.get("name")
        ]
        if not genres:
            return []

        genre_filters = filters.model_copy(
            update={
                "genre_names": genres[:3],
                "query_mode": "filter",
            }
        )
        fetch_limit = min(max(filters.count * 4, 20), 50)
        movies = await self._search_by_filters(genre_filters, limit=fetch_limit)
        movies = self._apply_client_filters(movies, filters)
        return [movie for movie in movies if movie.id != reference.id]

    async def search_by_text(
        self, query: str, filters: SearchFilters
    ) -> list[MovieItem]:
        client = await self._get_client()
        response = await client.get(
            "/movie/search",
            params={
                "query": query,
                "page": 1,
                "limit": min(max(filters.count * 4, 20), 50),
            },
        )
        response.raise_for_status()
        payload = response.json()
        movies = [self._parse_item(item) for item in payload.get("docs", [])]
        return self._apply_client_filters(movies, filters)

    async def _search_by_filters(
        self, filters: SearchFilters, *, limit: int
    ) -> list[MovieItem]:
        params = self._build_list_params(filters, limit=limit)
        client = await self._get_client()
        response = await client.get("/movie", params=params)
        response.raise_for_status()
        payload = response.json()
        return [self._parse_item(item) for item in payload.get("docs", [])]

    async def _search_by_query(
        self, filters: SearchFilters, *, limit: int
    ) -> list[MovieItem]:
        client = await self._get_client()
        response = await client.get(
            "/movie/search",
            params={"query": filters.company_query, "page": 1, "limit": limit},
        )
        response.raise_for_status()
        payload = response.json()
        movies = [self._parse_item(item) for item in payload.get("docs", [])]
        return movies

    def _build_list_params(
        self, filters: SearchFilters, *, limit: int
    ) -> list[tuple[str, str | int]]:
        params: list[tuple[str, str | int]] = [
            ("page", 1),
            ("limit", limit),
            ("sortField", "rating.kp"),
            ("sortType", -1),
        ]

        if filters.year is not None:
            params.append(("year", filters.year))
        if filters.country_name:
            params.append(("countries.name", filters.country_name))
        if filters.is_series is not None:
            params.append(("isSeries", str(filters.is_series).lower()))

        if filters.genre_names:
            for genre in filters.genre_names:
                params.append(("genres.name", f"+{genre}"))

        for genre in ALWAYS_EXCLUDED_GENRES:
            params.append(("genres.name", f"!{genre}"))

        if filters.company_query:
            network = COMPANY_NETWORKS.get(filters.company_query)
            if network:
                params.append(("networks.items.name", network))

        return params

    def _apply_client_filters(
        self,
        movies: list[MovieItem],
        filters: SearchFilters,
        *,
        skip_company_text_check: bool = False,
    ) -> list[MovieItem]:
        result: list[MovieItem] = []
        for movie in movies:
            if filters.year is not None and movie.year != filters.year:
                continue
            if filters.is_series is not None and movie.is_series != filters.is_series:
                continue
            if filters.country_name and filters.country_name not in movie.countries:
                continue
            if filters.genre_names and not any(
                genre.lower() in {g.lower() for g in movie.genres}
                for genre in filters.genre_names
            ):
                continue
            if filters.company_query and not skip_company_text_check:
                company = filters.company_query.lower()
                haystack = f"{movie.title} {movie.description}".lower()
                if company not in haystack:
                    continue
            result.append(movie)
        return result

    def _parse_item(self, item: dict[str, Any]) -> MovieItem:
        rating = item.get("rating") or {}
        kp_rating = rating.get("kp")
        if kp_rating in (0, None):
            kp_rating = rating.get("imdb")

        genres = [
            genre.get("name", "")
            for genre in item.get("genres") or []
            if genre.get("name")
        ]
        countries = [
            country.get("name", "")
            for country in item.get("countries") or []
            if country.get("name")
        ]

        item_type = (item.get("type") or "").lower()
        is_series = bool(item.get("isSeries")) or item_type in {
            "tv-series",
            "mini-series",
            "animated-series",
        }

        return MovieItem(
            id=int(item["id"]),
            title=item.get("name") or item.get("alternativeName") or "Без названия",
            alternative_title=item.get("alternativeName") or None,
            year=item.get("year"),
            rating=float(kp_rating) if kp_rating not in (None, 0) else None,
            countries=countries,
            genres=genres,
            description=(
                item.get("description") or item.get("shortDescription") or ""
            ).strip(),
            is_series=is_series,
        )

    def _parse_watchability(self, item: dict[str, Any]) -> list[WatchPlatform]:
        watchability = item.get("watchability") or {}
        platforms: list[WatchPlatform] = []
        seen_urls: set[str] = set()

        for entry in watchability.get("items") or []:
            name = (entry.get("name") or "").strip()
            url = (entry.get("url") or "").strip()
            if not name or not url or url in seen_urls:
                continue
            seen_urls.add(url)
            platforms.append(WatchPlatform(name=name, url=url))

        return platforms
