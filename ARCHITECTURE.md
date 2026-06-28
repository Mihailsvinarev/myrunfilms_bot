# Architecture

## Overview

Telegram-бот для подбора фильмов и сериалов. Единственный источник данных — **Kinopoisk Dev API** (`https://api.poiskkino.dev/v1.4`).

```
User (Telegram)
    ↓
main.py                     — polling, DI через bot_data["agent"]
    ↓
app/handlers/               — Telegram UI (start, filters, collections, text)
app/movie_browser.py        — карточный просмотр подборок
    ↓
app/agent.py                — оркестрация (async), SearchResult
    ↓
app/collections.py          — подборки + параметры Kinopoisk
app/query_router.py         — GigaChat → query_parser (текстовый поиск)
app/query_parser.py         — intent из текста / UI-фильтров
    ↓
app/kinopoisk_client.py     — httpx.AsyncClient → Kinopoisk API
app/kinopoisk_errors.py     — единая обработка ошибок API
    ↓
app/content_filters.py      — жанры, страны, лимит без дополнения
    ↓
app/response_formatter.py   — текст ответа (текстовый поиск, /filters)
```

## Modules

| Module | Responsibility |
|--------|----------------|
| `app/models.py` | `MovieItem`, `SearchFilters`, `SearchResult` |
| `app/genres.py` | Единый реестр жанров (подборки, /filters, парсер) |
| `app/protocols.py` | `MovieRepository` Protocol |
| `app/collections.py` | Определения подборок, параметры API, фильтрация |
| `app/query_parser.py` | Парсинг текстового запроса и `/filters` |
| `app/query_router.py` | GigaChat-first маршрутизация текста |
| `app/gigachat_client.py` | AI-парсер естественного языка |
| `app/kinopoisk_client.py` | Async HTTP-клиент Kinopoisk |
| `app/kinopoisk_errors.py` | `format_kinopoisk_error`, `run_kinopoisk` |
| `app/content_filters.py` | Пост-фильтрация результатов |
| `app/agent.py` | Сценарии поиска и подборок |
| `app/handlers/` | Telegram handlers по сценариям |
| `app/keyboards.py` | Telegram-клавиатуры |
| `app/movie_browser.py` | Карточный UI подборок (навигация, editMessageMedia) |
| `app/messages.py` | Сообщения об ошибках / пустой выдаче |

## Collections flow

1. Reply-кнопка **🎬 Подборки**
2. Inline-меню подборок (`collection:{id}`)
3. Inline-меню жанров (`collection_genre:{id}:{genre_id}`)
4. `MovieAgent.fetch_collection()` → `SearchResult` → Kinopoisk `/movie`
5. `MovieBrowser.open()` — одна карточка, листание без повторных запросов

Навигация **без wrap-around**: на первом/последнем фильме кнопки ⬅/➡ неактивны (`browser:noop:*`).

Состояние: `context.user_data["movie_browser"]` — список, индекс, collection_id, genre_id.

## Data rules

- Подборки: рейтинг Kinopoisk **≥ 6.0**, только художественные фильмы/сериалы.
- Российские новинки: `premiere.russia`, зарубежные: `premiere.world`.
- Всегда исключаются жанры: **мультфильм**, **документальный**, **ток-шоу**, **концерт**, **музыка**, **аниме**.
- Исключаются страны: **Индия**, **Китай**.
- Если найдено меньше 20 — **не дополняем** случайными тайтлами.

## External dependencies

- `python-telegram-bot` — Telegram Bot API
- `httpx` — async HTTP
- `pydantic` — модели данных

## Configuration

Environment variables (`.env`):

```env
BOT_TOKEN=...
KINOPOISK_API_KEY=...
GIGACHAT_AUTH_KEY=...
GIGACHAT_VERIFY_SSL=false
```

## Docker

```bash
docker compose up --build
```

Uses `Dockerfile` + `docker-compose.yml` with `.env`.
