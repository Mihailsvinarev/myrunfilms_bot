from __future__ import annotations

import re

from app.genres import PARSER_GENRE_KEYWORDS
from app.models import QueryMode, SearchFilters

GENRE_KEYWORDS = PARSER_GENRE_KEYWORDS

COUNTRY_KEYWORDS: dict[str, str] = {
    "росси": "Россия",
    "russia": "Россия",
    "сша": "США",
    "америк": "США",
    "usa": "США",
    "британ": "Великобритания",
    "англи": "Великобритания",
    "uk": "Великобритания",
    "франц": "Франция",
    "герман": "Германия",
    "итал": "Италия",
    "испан": "Испания",
    "япон": "Япония",
    "коре": "Южная Корея",
    "китай": "Китай",
    "инд": "Индия",
}

COUNTRY_ISO_TO_NAME: dict[str, str] = {
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

COMPANY_KEYWORDS: dict[str, str] = {
    "netflix": "Netflix",
    "marvel": "Marvel",
    "hbo": "HBO",
    "disney": "Disney",
    "warner": "Warner",
    "amazon": "Amazon",
    "apple tv": "Apple TV",
}

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


def parse_media_type(text: str) -> str:
    return "tv" if "сериал" in text.lower() else "movie"


def parse_year(text: str) -> int | None:
    match = re.search(r"20\d{2}", text)
    return int(match.group()) if match else None


def parse_count(text: str, *, default: int = 5, maximum: int = 10) -> int:
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


def parse_country_name(text: str) -> str | None:
    lowered = text.lower()
    for keyword, name in COUNTRY_KEYWORDS.items():
        if keyword in lowered:
            return name
    return None


def country_name_from_iso(iso: str | None) -> str | None:
    if not iso:
        return None
    return COUNTRY_ISO_TO_NAME.get(iso)


def parse_genre_names(text: str) -> list[str] | None:
    lowered = text.lower()
    genres: list[str] = []
    for keyword, names in GENRE_KEYWORDS.items():
        if keyword in lowered:
            genres.extend(names)
    if not genres:
        return None
    return list(dict.fromkeys(genres))


def parse_company(text: str) -> str | None:
    lowered = text.lower()
    for keyword, query in COMPANY_KEYWORDS.items():
        if keyword in lowered:
            return query
    return None


def is_director_request(text: str) -> bool:
    lowered = text.lower()
    return "режиссер" in lowered or "режиссёр" in lowered


COMPLEXITY_MARKERS = (
    "но не ",
    "кроме ",
    "без ",
    "except ",
    "не хочу",
    "не надо",
    "что-нибудь",
    "что нибудь",
    "что-то",
    "типа ",
    "вроде ",
    "настроен",
    "атмосфер",
)

VAGUE_THEME_HINTS: tuple[tuple[str, list[str]], ...] = (
    ("расследован", ["детектив"]),
    ("детектив", ["детектив"]),
    ("криминал", ["криминал"]),
    ("маньяк", ["триллер", "криминал"]),
    ("серийн", ["триллер", "криминал"]),
    ("убийц", ["триллер", "криминал"]),
    ("мрачн", ["триллер"]),
    ("ужас", ["ужасы"]),
    ("романт", ["мелодрама"]),
    ("комед", ["комедия"]),
    ("фантаст", ["фантастика"]),
    ("боевик", ["боевик"]),
    ("приключен", ["приключения"]),
    ("теннис", ["спорт"]),
    ("футбол", ["спорт"]),
    ("хоккей", ["спорт"]),
    ("баскетбол", ["спорт"]),
    ("бокс", ["спорт"]),
    ("спорт", ["спорт"]),
)

TOPIC_PATTERNS = (
    re.compile(r"\bпро\s+([a-zA-Zа-яА-ЯёЁ0-9\-]{2,40})", re.IGNORECASE),
    re.compile(r"\babout\s+([a-zA-Z0-9\- ]{2,40})", re.IGNORECASE),
)


def parse_topic_query(text: str) -> str | None:
    for pattern in TOPIC_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        topic = clean_title_text(match.group(1))
        if topic and len(topic) >= 2:
            return topic
    return None


def _genres_from_theme_hints(text: str) -> list[str]:
    lowered = text.lower()
    genres: list[str] = []
    for hint, names in VAGUE_THEME_HINTS:
        if hint in lowered:
            for name in names:
                if name not in genres:
                    genres.append(name)
    return genres


def is_vague_query(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in COMPLEXITY_MARKERS) or "про " in lowered


def parse_vague_query(text: str) -> SearchFilters | None:
    if not is_vague_query(text):
        return None

    topic = parse_topic_query(text)
    genres = _genres_from_theme_hints(text)
    if not genres and not topic:
        return None

    return SearchFilters(
        media_type=parse_media_type(text),
        year=parse_year(text),
        country_name=parse_country_name(text),
        genre_names=genres[:2] or None,
        topic_query=topic,
        count=parse_count(text),
        company_query=parse_company(text),
        user_text=text,
        query_mode="filter",
        restrict_media_type=has_explicit_media_type(text),
    )


SIMILAR_PATTERNS = (
    re.compile(r"(?:похож(?:ие|их|ую|ий|ее|ею)?)\s+(?:на\s+)?(.+)", re.IGNORECASE),
    re.compile(r"в\s+стиле\s+(.+)", re.IGNORECASE),
    re.compile(
        r"(?:фильм(?:ы|ов)?|сериал(?:ы|ов)?|картин(?:ы|у)?)?\s*(?:как|как\s+у)\s+(.+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"посоветуй(?:те)?\s+(?:фильм|сериал|кино|что-нибудь|что-то)?\s*(?:как|похож(?:ий|ие|ую|ая)?\s+на)\s+(.+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"рекомендуй(?:те)?\s+(?:фильм|сериал|кино)?\s*(?:как|похож(?:ий|ие|ую|ая)?\s+на)\s+(.+)",
        re.IGNORECASE,
    ),
    re.compile(r"similar\s+to\s+(.+)", re.IGNORECASE),
    re.compile(r"like\s+(.+)", re.IGNORECASE),
)

TITLE_NOISE_WORDS = (
    "фильм",
    "фильмы",
    "фильма",
    "фильмов",
    "сериал",
    "сериалы",
    "сериала",
    "сериалов",
    "кино",
    "картина",
    "подбери",
    "найди",
    "покажи",
    "дай",
    "дайте",
    "похожие",
    "похожих",
    "похожая",
    "похожий",
    "пожалуйста",
)


def extract_reference_title(text: str) -> str | None:
    for pattern in SIMILAR_PATTERNS:
        match = pattern.search(text)
        if match:
            cleaned = clean_title_text(match.group(1))
            if cleaned:
                return cleaned
    return None


def clean_title_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"20\d{2}", " ", cleaned)
    cleaned = re.sub(
        r"(?<![0-9])([1-9]|10)(?!\d)\s*\S*\s*(?:фильм|сериал|вариант|шт|штук)",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    for word in TITLE_NOISE_WORDS:
        cleaned = re.sub(rf"\b{re.escape(word)}\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" .,!?;:")


def has_explicit_media_type(text: str) -> bool:
    lowered = text.lower()
    return "сериал" in lowered or bool(re.search(r"\bфильм", lowered))


def has_filter_signals(text: str) -> bool:
    if parse_country_name(text) or parse_genre_names(text) or parse_company(text):
        return True

    lowered = text.lower()
    without_years = re.sub(r"20\d{2}", " ", lowered)

    if any(re.search(pattern, without_years) for pattern in COUNT_PATTERNS):
        return True

    for word in COUNT_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", without_years):
            return True

    year = parse_year(text)
    has_type = has_explicit_media_type(text)
    has_genre = bool(parse_genre_names(text))
    has_country = bool(parse_country_name(text))
    has_company = bool(parse_company(text))

    if has_type and (year or has_genre or has_country or has_company):
        return True
    if year and (has_genre or has_country or has_company or has_type):
        return True
    if has_company and (year or has_type):
        return True
    return False


def parse_query_mode(text: str) -> QueryMode:
    if extract_reference_title(text):
        return "similar"
    if parse_topic_query(text) or parse_vague_query(text):
        return "filter"
    if has_filter_signals(text):
        return "filter"
    cleaned = clean_title_text(text)
    if cleaned and len(cleaned) >= 2:
        return "title"
    return "filter"


def parse_title_query(text: str, mode: QueryMode) -> str | None:
    if mode == "similar":
        return extract_reference_title(text)
    if mode == "title":
        cleaned = clean_title_text(text)
        return cleaned or None
    return None


def parse_search_filters(text: str) -> SearchFilters:
    query_mode = parse_query_mode(text)
    explicit_type = has_explicit_media_type(text)
    topic = parse_topic_query(text)
    genre_names = parse_genre_names(text) or _genres_from_theme_hints(text) or None
    return SearchFilters(
        media_type=parse_media_type(text),
        year=parse_year(text),
        country_name=parse_country_name(text),
        genre_names=genre_names[:2] if genre_names else None,
        topic_query=topic,
        count=parse_count(text),
        company_query=parse_company(text),
        user_text=text,
        query_mode=query_mode,
        title_query=parse_title_query(text, query_mode),
        restrict_media_type=explicit_type or query_mode == "filter",
    )


def filters_from_ui(data: dict) -> SearchFilters:
    genre_names = data.get("genre_names")
    if not genre_names and data.get("genre_name"):
        genre_names = [data["genre_name"]]

    country_name = data.get("country_name")
    if not country_name:
        country_name = country_name_from_iso(data.get("country_iso"))

    return SearchFilters(
        media_type=data.get("media_type", "movie"),
        year=data.get("year"),
        years=data.get("years") or None,
        country_name=country_name,
        genre_names=genre_names,
        count=data.get("count", 5),
        company_query=data.get("company_query"),
    )
