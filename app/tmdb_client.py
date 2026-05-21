import re
import requests

from app.config import TMDB_API_KEY

BASE_URL = "https://api.themoviedb.org/3"
LANG = "ru-RU"

GENRE_KEYWORDS: dict[str, list[int]] = {
    "детектив": [80, 9648],
    "криминал": [80],
    "триллер": [53],
    "ужас": [27],
    "хоррор": [27],
    "комед": [35],
    "драм": [18],
    "фантаст": [878],
    "боевик": [28],
    "мелодрам": [10749],
    "романт": [10749],
    "аним": [16],
    "документал": [99],
    "истор": [36],
    "приключ": [12],
    "семейн": [10751],
    "военн": [10752],
    "вестерн": [37],
}

COUNTRY_KEYWORDS: dict[str, str] = {
    # stems cover Russian cases: Россия, России, российский, ...
    "росси": "RU",
    "russia": "RU",
    "сша": "US",
    "америк": "US",
    "usa": "US",
    "британ": "GB",
    "англи": "GB",
    "uk": "GB",
    "франц": "FR",
    "герман": "DE",
    "итал": "IT",
    "испан": "ES",
    "япон": "JP",
    "коре": "KR",
    "китай": "CN",
    "инд": "IN",
}

COUNTRY_NAMES: dict[str, str] = {
    "RU": "Россия",
    "US": "США",
    "GB": "Великобритания",
    "FR": "Франция",
    "DE": "Германия",
    "IT": "Италия",
    "ES": "Испания",
    "JP": "Япония",
    "KR": "Южная Корея",
    "CN": "Китай",
    "IN": "Индия",
}


def _get(url, params=None):
    if params is None:
        params = {}

    params["api_key"] = TMDB_API_KEY
    params["language"] = LANG

    r = requests.get(url, params=params, timeout=30)

    if r.status_code != 200:
        return {}

    return r.json()


def _genre_param(genre_ids: list[int] | None) -> str | None:
    if not genre_ids:
        return None
    unique = list(dict.fromkeys(genre_ids))
    return "|".join(str(g) for g in unique)


def _discover_params(
    *,
    year: int | None = None,
    country_iso: str | None = None,
    genre_ids: list[int] | None = None,
    with_crew: int | None = None,
    year_key: str,
) -> dict:
    params: dict = {
        "sort_by": "vote_average.desc",
        "vote_count.gte": 50,
        "include_adult": "false",
    }

    if year is not None:
        params[year_key] = year
    if country_iso:
        params["with_origin_country"] = country_iso
    if genre_param := _genre_param(genre_ids):
        params["with_genres"] = genre_param
    if with_crew is not None:
        params["with_crew"] = with_crew

    return params


def discover_movies(
    *,
    year: int | None = None,
    country_iso: str | None = None,
    genre_ids: list[int] | None = None,
    with_crew: int | None = None,
) -> list[dict]:
    url = f"{BASE_URL}/discover/movie"
    params = _discover_params(
        year=year,
        country_iso=country_iso,
        genre_ids=genre_ids,
        with_crew=with_crew,
        year_key="primary_release_year",
    )
    results = _get(url, params).get("results", [])
    return _filter_by_origin_country(results, country_iso)


def discover_tv(
    *,
    year: int | None = None,
    country_iso: str | None = None,
    genre_ids: list[int] | None = None,
    with_crew: int | None = None,
) -> list[dict]:
    url = f"{BASE_URL}/discover/tv"
    params = _discover_params(
        year=year,
        country_iso=country_iso,
        genre_ids=genre_ids,
        with_crew=with_crew,
        year_key="first_air_date_year",
    )
    results = _get(url, params).get("results", [])
    return _filter_by_origin_country(results, country_iso)


def _filter_by_origin_country(
    items: list[dict],
    country_iso: str | None,
) -> list[dict]:
    if not country_iso:
        return items

    filtered = [
        item
        for item in items
        if country_iso in (item.get("origin_country") or [])
    ]
    return filtered


def discover(
    media_type: str,
    *,
    year: int | None = None,
    country_iso: str | None = None,
    genre_ids: list[int] | None = None,
    with_crew: int | None = None,
) -> list[dict]:
    if media_type == "tv":
        return discover_tv(
            year=year,
            country_iso=country_iso,
            genre_ids=genre_ids,
            with_crew=with_crew,
        )
    return discover_movies(
        year=year,
        country_iso=country_iso,
        genre_ids=genre_ids,
        with_crew=with_crew,
    )


def parse_media_type(text: str) -> str:
    text = text.lower()
    if "сериал" in text:
        return "tv"
    return "movie"


def parse_year(text: str) -> int | None:
    match = re.search(r"20\d{2}", text)
    return int(match.group()) if match else None


COUNT_WORDS: dict[str, int] = {
    "один": 1,
    "одна": 1,
    "одно": 1,
    "два": 2,
    "две": 2,
    "двух": 2,
    "три": 3,
    "трёх": 3,
    "трех": 3,
    "четыре": 4,
    "четырёх": 4,
    "четырех": 4,
    "пять": 5,
    "пяти": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
}

COUNT_PATTERNS = (
    r"(?<![0-9])([1-9]|10)(?!\d)\s*\S*\s*(?:фильм|сериал|вариант|детектив)",
    r"(?:дай|дайте|подбери|нужно|хочу|посоветуй|покажи)\s*([1-9]|10)",
    r"(?<![0-9])([1-9]|10)(?!\d)\s*(?:шт|штук)",
    r"(?<![0-9])([1-9]|10)(?!\d)\s+(?:лучш|топ)",
)


def parse_count(text: str, *, default: int = 5, maximum: int = 10) -> int:
    """Extract requested number of titles; ignores years like 2021."""
    lowered = text.lower()
    without_years = re.sub(r"20\d{2}", " ", lowered)

    for pattern in COUNT_PATTERNS:
        match = re.search(pattern, without_years)
        if match:
            return min(maximum, max(1, int(match.group(1))))

    for word, count in COUNT_WORDS.items():
        if re.search(rf"\b{re.escape(word)}\b", without_years):
            return min(maximum, max(1, count))

    return min(maximum, max(1, default))


def parse_country_iso(text: str) -> str | None:
    lowered = text.lower()
    for keyword, iso in COUNTRY_KEYWORDS.items():
        if keyword in lowered:
            return iso
    return None


def parse_genres(text: str) -> list[int] | None:
    lowered = text.lower()
    genre_ids: list[int] = []

    for keyword, ids in GENRE_KEYWORDS.items():
        if keyword in lowered:
            genre_ids.extend(ids)

    if not genre_ids:
        return None

    return list(dict.fromkeys(genre_ids))


def country_label(iso: str | None) -> str | None:
    if not iso:
        return None
    return COUNTRY_NAMES.get(iso, iso)


def format_countries(details: dict, media_type: str) -> str:
    if media_type == "tv":
        codes = details.get("origin_country") or []
        if codes:
            return ", ".join(COUNTRY_NAMES.get(code, code) for code in codes)
        return "—"

    countries = details.get("production_countries") or []
    if countries:
        return ", ".join(c["name"] for c in countries)
    return "—"


# ---------------- DETAILS ----------------
def get_movie_details(movie_id: int):
    url = f"{BASE_URL}/movie/{movie_id}"
    return _get(url, {"append_to_response": "credits"})


def get_tv_details(tv_id: int):
    url = f"{BASE_URL}/tv/{tv_id}"
    return _get(url, {"append_to_response": "credits"})


def get_details(media_type: str, item_id: int) -> dict:
    if media_type == "tv":
        return get_tv_details(item_id)
    return get_movie_details(item_id)


# ---------------- PERSON (director mode) ----------------
def search_person(query: str):
    url = f"{BASE_URL}/search/person"
    return _get(url, {"query": query}).get("results", [])


def is_director_request(text: str) -> bool:
    lowered = text.lower()
    return "режиссер" in lowered or "режиссёр" in lowered
