from __future__ import annotations

PLATFORM_LABELS: dict[str, str] = {
    "иви": "IVI",
    "ivi": "IVI",
    "start": "START",
    "старт": "START",
    "wink": "WINK",
    "вink": "WINK",
    "kinopoisk hd": "KINOPOISK",
    "кинопоиск hd": "KINOPOISK",
    "кинопоиск": "KINOPOISK",
    "kinopoisk": "KINOPOISK",
    "kion": "KION",
    "кион": "KION",
    "okko": "OKKO",
    "окко": "OKKO",
    "premier": "PREMIER",
    "премьер": "PREMIER",
    "more.tv": "MORE.TV",
    "megogo": "MEGOGO",
    "мегого": "MEGOGO",
    "amediateka": "AMEDIATEKA",
    "амедиатека": "AMEDIATEKA",
    "netflix": "NETFLIX",
    "hbo max": "HBO MAX",
    "apple tv": "APPLE TV",
    "amazon": "AMAZON",
}


def platform_label(name: str) -> str:
    key = name.strip().lower()
    return PLATFORM_LABELS.get(key, name.strip())
