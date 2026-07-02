from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Any

import httpx

from app.config import KINOPOISK_API_KEY, KINOPOISK_BASE_URL
from app.content_filters import (
    EXCLUDED_COUNTRY_NAMES,
    EXCLUDED_GENRE_NAMES,
    contains_russian,
    is_allowed_movie,
)
from app.models import MovieItem, SearchFilters, WatchPlatform
from app.title_matching import title_matches

logger = logging.getLogger(__name__)

PRESET_RESULT_LIMIT = 20
PREMIERE_MONTHS = 6
NEW_MOVIES_MIN_RATING = 6.0
NEW_MOVIES_MAX_PAGES = 5

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
        if filters.topic_query:
            return await self.search_by_text(filters.topic_query, filters)
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
        similar_ids = await self._fetch_similar_movie_ids(reference.id)
        if not similar_ids:
            logger.info(
                "Similar search: no similarMovies for reference_id=%s title=%s",
                reference.id,
                reference.title,
            )
            return []

        fetch_limit = min(max(filters.count * 4, 20), 50)
        ids_to_fetch = [
            movie_id
            for movie_id in similar_ids[:fetch_limit]
            if movie_id != reference.id
        ]
        if not ids_to_fetch:
            return []

        params: list[tuple[str, str | int]] = [
            ("page", 1),
            ("limit", len(ids_to_fetch)),
            ("notNullField", "poster.url"),
            ("id", ",".join(str(movie_id) for movie_id in ids_to_fetch)),
        ]
        self._append_global_exclusions(params)

        movies = await self._fetch_movies(params)
        movies = self._apply_client_filters(movies, filters)
        movies_by_id = {movie.id: movie for movie in movies}
        ordered: list[MovieItem] = []
        for movie_id in ids_to_fetch:
            movie = movies_by_id.get(movie_id)
            if movie is not None:
                ordered.append(movie)
        logger.info(
            "Similar search reference_id=%s title=%s results=%d",
            reference.id,
            reference.title,
            len(ordered),
        )
        return ordered

    async def _fetch_similar_movie_ids(self, reference_id: int) -> list[int]:
        client = await self._get_client()
        response = await client.get(f"/movie/{reference_id}")
        response.raise_for_status()
        similar_raw = response.json().get("similarMovies") or []
        similar_ids: list[int] = []
        for item in similar_raw:
            if not isinstance(item, dict):
                continue
            raw_id = item.get("id")
            if raw_id is None:
                continue
            similar_ids.append(int(raw_id))
        return similar_ids

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

    async def search_new_movies(
        self, *, limit: int = PRESET_RESULT_LIMIT
    ) -> list[MovieItem]:
        selected: list[MovieItem] = []
        seen_ids: set[int] = set()

        for page in range(1, NEW_MOVIES_MAX_PAGES + 1):
            params = self._build_new_movies_params(page=page)
            movies = await self._fetch_movies(params)
            if not movies:
                break

            for movie in movies:
                if movie.id in seen_ids:
                    continue
                seen_ids.add(movie.id)
                if movie.is_series:
                    continue
                if not is_allowed_movie(movie, require_russian_title=True):
                    continue
                if is_ceremony_or_event(movie):
                    continue
                if not _has_new_movie_ratings(movie, min_rating=NEW_MOVIES_MIN_RATING):
                    continue
                selected.append(movie)
                if len(selected) >= limit:
                    return selected

        return selected

    def _build_new_movies_params(self, *, page: int) -> list[tuple[str, str | int]]:
        return self._build_preset_params(
            is_series=False,
            premiere_months=PREMIERE_MONTHS,
            sort_fields=(
                ("premiere.world", -1),
                ("rating.kp", -1),
                ("rating.tmdb", -1),
            ),
            limit=50,
            movies_only=True,
            min_kp_rating=NEW_MOVIES_MIN_RATING,
            page=page,
        )

    async def search_popular_series(
        self, *, limit: int = PRESET_RESULT_LIMIT
    ) -> list[MovieItem]:
        params = self._build_preset_params(
            is_series=True,
            premiere_months=PREMIERE_MONTHS,
            sort_fields=(("votes.kp", -1),),
            limit=min(max(limit * 3, 40), 50),
        )
        movies = await self._fetch_movies(params)
        return self._filter_preset_results(
            movies,
            limit=limit,
            is_series=True,
            require_russian_title=True,
        )

    async def fetch_by_params(
        self, params: list[tuple[str, str | int]]
    ) -> list[MovieItem]:
        return await self._fetch_movies(params)

    async def _fetch_movies(
        self, params: list[tuple[str, str | int]]
    ) -> list[MovieItem]:
        client = await self._get_client()
        response = await client.get("/movie", params=params)
        response.raise_for_status()
        payload = response.json()
        return [self._parse_item(item) for item in payload.get("docs", [])]

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
            ("notNullField", "poster.url"),
            ("sortField", "rating.kp"),
            ("sortType", -1),
        ]

        self._append_year_params(params, filters)
        if filters.country_name:
            params.append(("countries.name", filters.country_name))
        if filters.is_series is not None:
            params.append(("isSeries", str(filters.is_series).lower()))

        if filters.genre_names:
            for genre in filters.genre_names:
                params.append(("genres.name", f"+{genre}"))

        self._append_global_exclusions(params)

        if filters.company_query:
            network = COMPANY_NETWORKS.get(filters.company_query)
            if network:
                params.append(("networks.items.name", network))

        return params

    def _build_preset_params(
        self,
        *,
        is_series: bool,
        premiere_months: int,
        sort_fields: tuple[tuple[str, int], ...],
        limit: int,
        movies_only: bool = False,
        min_kp_rating: float | None = None,
        min_tmdb_rating: float | None = None,
        require_ratings: bool = False,
        page: int = 1,
    ) -> list[tuple[str, str | int]]:
        params: list[tuple[str, str | int]] = [
            ("page", page),
            ("limit", limit),
            ("isSeries", str(is_series).lower()),
            ("premiere.world", _premiere_range(premiere_months)),
            ("notNullField", "poster.url"),
            ("notNullField", "name"),
        ]
        if require_ratings:
            params.extend(
                [
                    ("notNullField", "rating.kp"),
                    ("notNullField", "rating.tmdb"),
                ]
            )
        if min_kp_rating is not None:
            params.append(("rating.kp", f"{min_kp_rating:g}-10"))
        if min_tmdb_rating is not None:
            params.append(("rating.tmdb", f"{min_tmdb_rating:g}-10"))
        if movies_only:
            params.extend(
                [
                    ("type", "movie"),
                    ("typeNumber", 1),
                ]
            )
        for sort_field, sort_type in sort_fields:
            params.append(("sortField", sort_field))
            params.append(("sortType", sort_type))
        self._append_global_exclusions(params)
        return params

    def _append_global_exclusions(self, params: list[tuple[str, str | int]]) -> None:
        for country in sorted(EXCLUDED_COUNTRY_NAMES):
            params.append(("countries.name", f"!{country}"))
        for genre in sorted(EXCLUDED_GENRE_NAMES):
            params.append(("genres.name", f"!{genre}"))

    def _append_year_params(
        self,
        params: list[tuple[str, str | int]],
        filters: SearchFilters,
    ) -> None:
        if filters.years:
            if len(filters.years) == 1:
                params.append(("year", filters.years[0]))
            else:
                params.append(("year", f"{min(filters.years)}-{max(filters.years)}"))
        elif filters.year is not None:
            params.append(("year", filters.year))

    def _apply_client_filters(
        self,
        movies: list[MovieItem],
        filters: SearchFilters,
        *,
        skip_company_text_check: bool = False,
    ) -> list[MovieItem]:
        result: list[MovieItem] = []
        for movie in movies:
            if filters.years:
                if movie.year not in filters.years:
                    continue
            elif filters.year is not None and movie.year != filters.year:
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
            if not is_allowed_movie(movie, require_russian_title=True):
                continue
            result.append(movie)
        return result

    def _filter_preset_results(
        self,
        movies: list[MovieItem],
        *,
        limit: int,
        is_series: bool,
        require_russian_title: bool = False,
    ) -> list[MovieItem]:
        selected: list[MovieItem] = []
        for movie in movies:
            if len(selected) >= limit:
                break
            if movie.is_series != is_series:
                continue
            if not is_allowed_movie(movie, require_russian_title=require_russian_title):
                continue
            selected.append(movie)
        return selected

    def _parse_item(self, item: dict[str, Any]) -> MovieItem:
        rating = item.get("rating") or {}
        raw_kp = rating.get("kp")
        kp_rating = float(raw_kp) if raw_kp not in (0, None) else None
        kp_display = kp_rating
        if kp_display in (0, None):
            kp_display = rating.get("imdb")
        tmdb_rating = rating.get("tmdb")
        if tmdb_rating in (0, None):
            tmdb_rating = None
        raw_imdb = rating.get("imdb")
        imdb_rating = float(raw_imdb) if raw_imdb not in (0, None) else None

        poster = item.get("poster") or {}
        poster_url = poster.get("url") or poster.get("previewUrl")

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
            title=_extract_russian_title(item),
            alternative_title=item.get("alternativeName") or None,
            year=item.get("year"),
            rating=float(kp_display) if kp_display not in (None, 0) else None,
            kp_rating=kp_rating,
            tmdb_rating=float(tmdb_rating) if tmdb_rating is not None else None,
            imdb_rating=imdb_rating,
            countries=countries,
            genres=genres,
            description=(
                item.get("description") or item.get("shortDescription") or ""
            ).strip(),
            is_series=is_series,
            poster_url=poster_url or None,
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


def _premiere_range(months: int) -> str:
    today = date.today()
    start = today - timedelta(days=months * 30)
    return f"{start.strftime('%d.%m.%Y')}-{today.strftime('%d.%m.%Y')}"


def _extract_russian_title(item: dict[str, Any]) -> str:
    for entry in item.get("names") or []:
        if not isinstance(entry, dict):
            continue
        name = (entry.get("name") or "").strip()
        if not name:
            continue
        language = (entry.get("language") or "").upper()
        entry_type = (entry.get("type") or "").lower()
        if language == "RU" or "russian title" in entry_type:
            return name

    for candidate in (item.get("name"), item.get("alternativeName")):
        text = (candidate or "").strip()
        if text and contains_russian(text):
            return text

    return (item.get("name") or item.get("alternativeName") or "Без названия").strip()


def _has_new_movie_ratings(movie: MovieItem, *, min_rating: float) -> bool:
    if movie.kp_rating is None or movie.kp_rating < min_rating:
        return False
    if movie.tmdb_rating is not None and movie.tmdb_rating >= min_rating:
        return True
    if movie.imdb_rating is not None and movie.imdb_rating >= min_rating:
        return True
    return False


def is_ceremony_or_event(movie: MovieItem) -> bool:
    lowered = movie.title.lower()
    if "церемони" in lowered and any(
        word in lowered for word in ("оскар", "премии", "emmy", "grammy")
    ):
        return True
    return False
