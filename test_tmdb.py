from app.tmdb_client import (
    discover_movies,
    discover_tv,
    get_movie_details,
    parse_country_iso,
    parse_genres,
    parse_year,
    search_person,
)

import json


def pretty(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


print("\n=== DISCOVER MOVIE (RU, 2020, detective) ===")
movies = discover_movies(
    year=2020,
    country_iso="RU",
    genre_ids=parse_genres("российский детектив"),
)
pretty(movies[:2])


print("\n=== DISCOVER TV (RU, 2020, detective) ===")
shows = discover_tv(
    year=2020,
    country_iso="RU",
    genre_ids=parse_genres("российский детектив сериал"),
)
pretty(shows[:2])


print("\n=== MOVIE DETAILS ===")
if movies:
    details = get_movie_details(movies[0]["id"])
    pretty({"title": details.get("title"), "countries": details.get("production_countries")})


print("\n=== PARSE INTENT ===")
text = "российский сериал 2020 детектив"
print("year:", parse_year(text))
print("country:", parse_country_iso(text))
print("genres:", parse_genres(text))


print("\n=== SEARCH PERSON ===")
persons = search_person("Ridley Scott")
pretty(persons[:1])
