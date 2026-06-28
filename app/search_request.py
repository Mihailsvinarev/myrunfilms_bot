from dataclasses import dataclass, field


@dataclass
class SearchRequest:
    media_type: str = "movie"
    year: int | None = None
    country_iso: str | None = None
    genre_ids: list[int] | None = None
    count: int = 5
    exclude_animation: bool = False
    company_id: int | None = None
    company_query: str | None = None
    with_crew: int | None = None
    user_text: str | None = field(default=None, repr=False)
