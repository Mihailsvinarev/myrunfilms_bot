import requests

from app.config import OLLAMA_MODEL, OLLAMA_URL
from app.prompts import SYSTEM_PROMPT

from app.tmdb_client import (
    discover,
    get_details,
    search_person,
    parse_media_type,
    parse_year,
    parse_country_iso,
    parse_genres,
    country_label,
    format_countries,
    is_director_request,
)


class MovieAgent:

    def _no_results_message(
        self,
        media_type: str,
        year: int | None,
        country_iso: str | None,
        genre_ids: list[int] | None,
    ) -> str:
        kind = "сериалов" if media_type == "tv" else "фильмов"
        parts = [f"Не нашёл подходящих {kind} в TMDB"]

        if year:
            parts.append(f"за {year} год")
        if country_iso:
            parts.append(f"из {country_label(country_iso)}")
        if genre_ids:
            parts.append("с указанным жанром")

        parts.append("Попробуйте изменить год, страну или жанр.")
        return " ".join(parts) + " 🤷"

    def _build_context(self, items: list[dict], media_type: str) -> str:
        context = ""

        for item in items[:5]:
            item_id = item.get("id")
            if not item_id:
                continue

            details = get_details(media_type, item_id)

            title = details.get("title") or details.get("name") or item.get("title") or item.get("name")
            overview = details.get("overview") or item.get("overview")
            rating = details.get("vote_average") or item.get("vote_average")
            release = (
                details.get("release_date")
                or details.get("first_air_date")
                or item.get("release_date")
                or item.get("first_air_date")
            )
            genres = ", ".join(g["name"] for g in details.get("genres", []))
            countries = format_countries(details, media_type)

            cast = ", ".join(
                a["name"] for a in details.get("credits", {}).get("cast", [])[:5]
            )

            director = "—"
            for crew_member in details.get("credits", {}).get("crew", []):
                if crew_member.get("job") == "Director":
                    director = crew_member.get("name", "—")
                    break

            context += f"""
Название: {title}
Режиссер: {director}
Страна: {countries}
Жанры: {genres}
Актеры: {cast}
Рейтинг: {rating}
Дата: {release}
Описание: {overview}
---
"""

        return context

    def ask(self, user_text: str):
        media_type = parse_media_type(user_text)
        year = parse_year(user_text)
        country_iso = parse_country_iso(user_text)
        genre_ids = parse_genres(user_text)
        country = country_label(country_iso)

        with_crew = None
        if is_director_request(user_text):
            persons = search_person(user_text)
            if not persons:
                return "Не удалось найти режиссёра в TMDB. Уточните имя и попробуйте снова."
            with_crew = persons[0]["id"]

        items = discover(
            media_type,
            year=year,
            country_iso=country_iso,
            genre_ids=genre_ids,
            with_crew=with_crew,
        )

        if not items:
            return self._no_results_message(media_type, year, country_iso, genre_ids)

        context = self._build_context(items, media_type)

        if not context.strip():
            return self._no_results_message(media_type, year, country_iso, genre_ids)

        prompt = f"""
Пользователь запросил:
{user_text}

Тип: {media_type}
Год: {year or "не указан"}
Страна: {country or "не указана"}

Вот результаты TMDB (уже отфильтрованы):

{context}

Задача:
- выбери лучшие варианты из списка выше
- кратко объясни, почему они подходят
- не добавляй фильмы и сериалы, которых нет в списке
- отвечай на русском
"""

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            },
            timeout=120,
        )

        if response.status_code != 200:
            return f"Ollama error: {response.status_code}"

        return response.json()["message"]["content"]
