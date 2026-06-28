# Architecture

## Overview

Telegram-бот для подбора фильмов и сериалов. Единственный источник данных — **Kinopoisk Dev API** (`https://api.kinopoisk.dev/v1.4`).

```
User (Telegram)
    ↓
main.py                     — polling, handlers, lifecycle
    ↓
app/bot_handlers.py         — меню, ConversationHandler, текстовый поиск
    ↓
app/agent.py                — оркестрация (async)
    ↓
app/query_parser.py         — intent из текста / UI-фильтров
    ↓
app/kinopoisk_client.py     — httpx.AsyncClient → Kinopoisk API
    ↓
app/content_filters.py      — жанры, русский язык, лимит без дополнения
    ↓
app/response_formatter.py   — текст ответа + ссылка на kinopoisk.ru
```

## Modules

| Module | Responsibility |
|--------|----------------|
| `app/models.py` | Pydantic-модели `MovieItem`, `SearchFilters` |
| `app/query_parser.py` | Парсинг запроса пользователя |
| `app/kinopoisk_client.py` | Async HTTP-клиент Kinopoisk |
| `app/content_filters.py` | Пост-фильтрация результатов |
| `app/agent.py` | Сценарий поиска |
| `app/keyboards.py` | Telegram-клавиатуры |
| `app/messages.py` | Сообщения об ошибках / пустой выдаче |

## Data rules

- Ответ только на **русском** (описание с кириллицей из Kinopoisk).
- Всегда исключаются жанры: **мультфильм**, **документальный**, **ток-шоу**.
- Если найдено меньше, чем запрошено — **не дополняем** нерелевантными тайтлами.
- Ссылка на карточку: `https://www.kinopoisk.ru/film/{id}/` или `/series/{id}/`.

## External dependencies

- `python-telegram-bot` — Telegram Bot API
- `httpx` — async HTTP
- `pydantic` — модели данных

## Configuration

Environment variables (`.env`):

```env
BOT_TOKEN=...
KINOPOISK_API_KEY=...
```

## Docker

```bash
docker compose up --build
```

Uses `Dockerfile` + `docker-compose.yml` with `.env`.
