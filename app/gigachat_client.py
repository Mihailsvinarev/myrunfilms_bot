from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from app.config import (
    GIGACHAT_API_URL,
    GIGACHAT_AUTH_KEY,
    GIGACHAT_MODEL,
    GIGACHAT_OAUTH_URL,
    GIGACHAT_SCOPE,
    GIGACHAT_TIMEOUT,
    GIGACHAT_VERIFY_SSL,
)
from app.genres import KINOPOISK_SEARCH_GENRES
from app.models import SearchFilters
from app.query_parser import (
    COUNTRY_KEYWORDS,
    extract_reference_title,
    has_explicit_media_type,
    parse_company,
    parse_topic_query,
)

logger = logging.getLogger(__name__)

TOKEN_TTL_SECONDS = 30 * 60

ALLOWED_GENRES = list(KINOPOISK_SEARCH_GENRES)
ALLOWED_COUNTRIES = sorted(set(COUNTRY_KEYWORDS.values()))

MOOD_TO_GENRES: dict[str, list[str]] = {
    "маньяк": ["триллер", "криминал"],
    "убийц": ["триллер", "криминал"],
    "мрачн": ["триллер", "детектив"],
    "страшн": ["ужасы", "триллер"],
    "весел": ["комедия"],
    "смешн": ["комедия"],
    "романт": ["мелодрама"],
    "драм": ["драма"],
    "легк": ["комедия", "мелодрама"],
    "расследован": ["детектив"],
    "шпион": ["триллер", "боевик"],
    "войн": ["военный", "история"],
    "космос": ["фантастика"],
    "космонавт": ["фантастика"],
}

TOPIC_TO_GENRES: dict[str, list[str]] = {
    "теннис": ["спорт"],
    "tennis": ["спорт"],
    "футбол": ["спорт"],
    "football": ["спорт"],
    "soccer": ["спорт"],
    "хоккей": ["спорт"],
    "hockey": ["спорт"],
    "баскетбол": ["спорт"],
    "basketball": ["спорт"],
    "бокс": ["спорт"],
    "боксер": ["спорт"],
    "спорт": ["спорт"],
    "олимпиад": ["спорт"],
    "шахмат": ["драма", "биография"],
    "chess": ["драма", "биография"],
    "музык": ["музыкальный", "драма"],
    "готовк": ["комедия"],
    "кулинар": ["комедия"],
    "медицин": ["драма"],
    "врач": ["драма"],
    "больниц": ["драма"],
    "школ": ["драма", "комедия"],
    "университет": ["драма", "комедия"],
}

SYSTEM_PROMPT = """Ты парсер запросов к боту подбора фильмов и сериалов
через API Kinopoisk.
Извлеки параметры поиска из текста пользователя.
НЕ рекомендуй фильмы и НЕ придумывай названия.

Верни только JSON:
{
  "media_type": "movie" | "tv" | null,
  "genres": string[] | null,
  "country": string | null,
  "year": number | null,
  "year_from": number | null,
  "year_to": number | null,
  "director": string | null,
  "actor": string | null,
  "mood": string | null,
  "topic": string | null,
  "similar_title": string | null,
  "count": number
}

Поля и правила Kinopoisk:
- media_type=tv для сериалов, movie для фильмов, null если не указано явно.
- genres — только из списка Kinopoisk: __GENRES__
- country — только из списка: __COUNTRIES__
- topic — главное ключевое слово темы/сюжета (1–3 слова) для текстового поиска.
  Обязательно заполняй для конструкций «про X», «about X», «на тему X».
  topic — это НЕ название фильма. Не пиши в topic слова «сериал», «фильм», «про».
- similar_title — только для «как X», «похожие на X», «в стиле X»
  (конкретное название образца).
- mood — настроение или общая тема, если topic не выделить одним словом.
- count от 1 до 10.
- director и actor — имена, если явно указаны.
- year — один год; year_from/year_to — диапазон.

Сопоставление тем с жанрами Kinopoisk (используй genres вместе с topic):
- теннис, футбол, хоккей, бокс, баскетбол, спорт, олимпиада -> genres ["спорт"]
- маньяк, серийный убийца -> ["триллер", "криминал"]
- расследование, детектив, криминал -> ["детектив"] или ["криминал"]
- страшное, хоррор -> ["ужасы"]
- романтика, любовь -> ["мелодрама"]
- космос, будущее -> ["фантастика"]
- война, фронт -> ["военный"]
- историческая эпоха, биография известного человека -> ["история", "биография"]

Примеры:
- «Сериал про теннис» -> media_type=tv, genres=["спорт"], topic="теннис"
- «фильмы про футбол 2020» -> media_type=movie, year=2020,
  genres=["спорт"], topic="футбол"
- «мрачный детектив Россия» -> media_type=null,
  genres=["детектив","триллер"], country="Россия", mood="мрачное"
- «похожие на Интерстеллар» -> similar_title="Интерстеллар", genres=null, topic=null
- «сериал про врачей» -> media_type=tv, genres=["драма"], topic="врачи"
"""


class QueryFilters(BaseModel):
    media_type: Literal["movie", "tv"] | None = None
    genres: list[str] | None = None
    country: str | None = None
    year: int | None = None
    year_from: int | None = None
    year_to: int | None = None
    director: str | None = None
    actor: str | None = None
    mood: str | None = None
    topic: str | None = None
    similar_title: str | None = None
    count: int = Field(default=5, ge=1, le=10)


class _TokenCache:
    token: str | None = None
    expires_at: float = 0.0


class GigaChatClient:
    def __init__(
        self,
        auth_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        self.auth_key = auth_key or GIGACHAT_AUTH_KEY
        self._client = client
        self._owns_client = client is None
        self._token_cache = _TokenCache()

    def is_available(self) -> bool:
        return bool(self.auth_key)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=GIGACHAT_TIMEOUT,
                verify=GIGACHAT_VERIFY_SSL,
            )
        return self._client

    async def close(self) -> None:
        if self._client and self._owns_client:
            await self._client.aclose()
            self._client = None

    async def get_access_token(self) -> str:
        now = time.time()
        if self._token_cache.token and now < self._token_cache.expires_at:
            return self._token_cache.token

        if not self.auth_key:
            raise RuntimeError("GIGACHAT_AUTH_KEY is not set in .env")

        client = await self._get_client()
        response = await client.post(
            GIGACHAT_OAUTH_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "RqUID": str(uuid.uuid4()),
                "Authorization": f"Basic {self.auth_key}",
            },
            data={"scope": GIGACHAT_SCOPE},
        )
        if response.is_error:
            logger.error(
                "GigaChat OAuth HTTP %s: %s",
                response.status_code,
                response.text[:300],
            )
        response.raise_for_status()
        payload = response.json()
        access_token = payload["access_token"]
        expires_in = int(payload.get("expires_in", TOKEN_TTL_SECONDS))
        self._token_cache.token = access_token
        self._token_cache.expires_at = now + min(expires_in, TOKEN_TTL_SECONDS)
        return access_token

    async def parse_query(self, text: str) -> QueryFilters:
        access_token = await self.get_access_token()
        system_prompt = SYSTEM_PROMPT.replace(
            "__GENRES__", ", ".join(ALLOWED_GENRES)
        ).replace("__COUNTRIES__", ", ".join(ALLOWED_COUNTRIES))
        client = await self._get_client()
        response = await client.post(
            f"{GIGACHAT_API_URL.rstrip('/')}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            json={
                "model": GIGACHAT_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                "temperature": 0.1,
                "stream": False,
            },
        )
        if response.is_error:
            logger.error(
                "GigaChat chat HTTP %s: %s",
                response.status_code,
                response.text[:300],
            )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        payload = _extract_json(content)
        if "count" in payload:
            payload["count"] = min(max(int(payload["count"]), 1), 10)
        return QueryFilters.model_validate(payload)

    def to_search_filters(self, query: QueryFilters, user_text: str) -> SearchFilters:
        similar_title = self._resolve_similar_title(query, user_text)
        if similar_title:
            media_type = query.media_type or "movie"
            return SearchFilters(
                media_type=media_type,
                count=query.count,
                user_text=user_text,
                query_mode="similar",
                title_query=similar_title,
                restrict_media_type=has_explicit_media_type(user_text),
            )

        topic_query = self._resolve_topic(query, user_text)
        genre_names = self._normalize_genres(query.genres)
        genre_names = self._apply_mood(query.mood, genre_names)
        genre_names = self._apply_topic(topic_query, query.mood, genre_names)
        country_name = self._normalize_country(query.country)
        year = self._resolve_year(query)
        company_query = parse_company(user_text)

        effective_text = user_text
        if query.director:
            effective_text = f"режиссер {query.director} {user_text}".strip()
        elif query.actor:
            effective_text = f"{query.actor} {user_text}".strip()

        media_type = query.media_type or "movie"
        restrict_media_type = query.media_type is not None or has_explicit_media_type(
            user_text
        )

        return SearchFilters(
            media_type=media_type,
            year=year,
            country_name=country_name,
            genre_names=genre_names,
            topic_query=topic_query,
            count=query.count,
            company_query=company_query,
            user_text=effective_text,
            query_mode="filter",
            restrict_media_type=restrict_media_type,
        )

    def _normalize_genres(self, genres: list[str] | None) -> list[str] | None:
        if not genres:
            return None
        allowed = {genre.lower(): genre for genre in ALLOWED_GENRES}
        normalized: list[str] = []
        for genre in genres:
            canonical = allowed.get(genre.strip().lower())
            if canonical and canonical not in normalized:
                normalized.append(canonical)
        return normalized or None

    def _normalize_country(self, country: str | None) -> str | None:
        if not country:
            return None
        if country in ALLOWED_COUNTRIES:
            return country
        lowered = country.strip().lower()
        for keyword, name in COUNTRY_KEYWORDS.items():
            if keyword in lowered or lowered in name.lower():
                return name
        return None

    def _resolve_year(self, query: QueryFilters) -> int | None:
        if query.year is not None:
            return query.year
        if query.year_from is not None and query.year_to is not None:
            if query.year_from == query.year_to:
                return query.year_from
        if query.year_from is not None:
            return query.year_from
        return query.year_to

    def _resolve_topic(self, query: QueryFilters, user_text: str) -> str | None:
        if query.topic and query.topic.strip():
            return self._clean_topic(query.topic)
        parsed = parse_topic_query(user_text)
        if parsed:
            return self._clean_topic(parsed)
        return None

    def _clean_topic(self, topic: str) -> str:
        cleaned = topic.strip().lower()
        for word in ("сериал", "фильм", "кино", "про", "about"):
            cleaned = re.sub(rf"\b{re.escape(word)}\b", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,!?;:")
        return cleaned

    def _apply_mood(
        self, mood: str | None, genre_names: list[str] | None
    ) -> list[str] | None:
        if not mood:
            return genre_names
        lowered = mood.lower()
        mood_genres: list[str] = []
        for hint, names in MOOD_TO_GENRES.items():
            if hint in lowered:
                for name in names:
                    if name not in mood_genres:
                        mood_genres.append(name)
        if not mood_genres:
            return genre_names
        if not genre_names:
            return mood_genres[:2]
        merged = list(genre_names)
        for genre in mood_genres:
            if genre not in merged:
                merged.append(genre)
        return merged[:3]

    def _apply_topic(
        self,
        topic_query: str | None,
        mood: str | None,
        genre_names: list[str] | None,
    ) -> list[str] | None:
        hints = " ".join(part for part in (topic_query, mood) if part).lower()
        if not hints:
            return genre_names

        topic_genres: list[str] = []
        for hint, names in TOPIC_TO_GENRES.items():
            if hint in hints:
                for name in names:
                    if name not in topic_genres:
                        topic_genres.append(name)
        if not topic_genres:
            return genre_names
        if not genre_names:
            return topic_genres[:2]
        merged = list(genre_names)
        for genre in topic_genres:
            if genre not in merged:
                merged.append(genre)
        return merged[:3]

    def _resolve_similar_title(self, query: QueryFilters, user_text: str) -> str | None:
        if query.similar_title and query.similar_title.strip():
            return query.similar_title.strip()
        return extract_reference_title(user_text)


def _extract_json(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    fenced = re.search(
        r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE
    )
    if fenced:
        cleaned = fenced.group(1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError("GigaChat returned invalid JSON") from exc


def parse_query_payload(payload: dict[str, Any]) -> QueryFilters:
    if "count" in payload:
        payload = {**payload, "count": min(max(int(payload["count"]), 1), 10)}
    return QueryFilters.model_validate(payload)


def query_filters_to_search_filters(
    query: QueryFilters, user_text: str
) -> SearchFilters:
    client = GigaChatClient(auth_key="test")
    return client.to_search_filters(query, user_text)
