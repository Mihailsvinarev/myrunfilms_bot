from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

QueryMode = Literal["filter", "title", "similar"]


class WatchPlatform(BaseModel):
    name: str
    url: str


class MovieItem(BaseModel):
    id: int
    title: str
    alternative_title: str | None = None
    year: int | None = None
    rating: float | None = None
    countries: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    description: str = ""
    is_series: bool = False
    watch_platforms: list[WatchPlatform] = Field(default_factory=list)

    @property
    def kinopoisk_url(self) -> str:
        kind = "series" if self.is_series else "film"
        return f"https://www.kinopoisk.ru/{kind}/{self.id}/"

    @property
    def countries_label(self) -> str:
        return ", ".join(self.countries) if self.countries else "—"

    @property
    def genres_label(self) -> str:
        return ", ".join(self.genres) if self.genres else "—"

    @property
    def rating_label(self) -> str:
        if self.rating is None:
            return "—"
        return f"{self.rating:.1f}"


class SearchFilters(BaseModel):
    media_type: Literal["movie", "tv"] = "movie"
    year: int | None = None
    country_name: str | None = None
    genre_names: list[str] | None = None
    count: int = Field(default=5, ge=1, le=10)
    company_query: str | None = None
    user_text: str | None = None
    query_mode: QueryMode = "filter"
    title_query: str | None = None
    restrict_media_type: bool = True

    @property
    def is_series(self) -> bool | None:
        if not self.restrict_media_type:
            return None
        if self.media_type == "tv":
            return True
        if self.media_type == "movie":
            return False
        return None
