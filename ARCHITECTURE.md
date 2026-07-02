# Architecture

## Overview

Telegram-бот для подбора фильмов и сериалов. Единственный источник данных — **Kinopoisk Dev API** (`https://api.poiskkino.dev/v1.4`).

```
User (Telegram)
    ↓
main.py                     — polling, composition root (build_app_services)
    ↓
app/composition.py          — wiring: KinopoiskClient + GigaChatClient → MovieAgent
    ↓
app/handlers/               — Telegram UI (зависят от MovieSearchService Protocol)
app/telegram_cards.py       — caption и inline-клавиатуры карточек (без Telegram API)
app/movie_browser.py        — карточный просмотр подборок (send/edit, навигация)
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
| `app/protocols.py` | Контракты: `MovieRepository`, `NaturalLanguageQueryParser`, `MovieSearchService` |
| `app/composition.py` | Composition root — единственное место создания конкретных реализаций |
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
| `app/telegram_cards.py` | Компактные caption и клавиатуры карточек (compact / details) |
| `app/movie_browser.py` | Карточный UI подборок (send_photo, editMessageMedia, state) |
| `app/messages.py` | Сообщения об ошибках / пустой выдаче |

## SOLID

| Принцип | Как применён |
|---------|----------------|
| **S** — Single Responsibility | `agent` — оркестрация; `kinopoisk_client` — HTTP; `query_parser` — intent; `telegram_cards` — caption; `movie_browser` — Telegram I/O |
| **O** — Open/Closed | Новые подборки — через `COLLECTIONS` в `collections.py`; новые жанры — через `genres.py` |
| **L** — Liskov Substitution | `KinopoiskClient` и `AsyncMock` взаимозаменяемы как `MovieRepository`; `MovieAgent` — как `MovieSearchService` |
| **I** — Interface Segregation | Handlers видят только `MovieSearchService`; collections — только `MovieRepository`; router — только `NaturalLanguageQueryParser` |
| **D** — Dependency Inversion | `main.py` → `build_app_services()`; `MovieAgent` не создаёт клиентов сам; handlers не импортируют `KinopoiskClient` |

**DI:** `app.bot_data[AGENT_KEY]` хранит `MovieSearchService`. Тесты подставляют моки через конструктор `MovieAgent`.

**Ошибки Kinopoisk:** единый wrapper `run_kinopoisk()` для поиска и подборок.

## Collections flow

1. Reply-кнопка **🎬 Подборки**
2. Inline-меню подборок (`collection:{id}`)
3. Inline-меню жанров (`collection_genre:{id}:{genre_id}`)
4. `MovieAgent.fetch_collection()` → `SearchResult` → Kinopoisk `/movie`
5. `MovieBrowser.open()` — одна компактная карточка, листание без повторных запросов

**Compact mode:** постер + номер + метаданные без описания. Кнопки: навигация, «ℹ Подробнее», Кинопоиск, случайный, подборки.

**Details mode:** то же сообщение редактируется — добавляется описание (≤700 символов) и ссылка. Кнопки: «Назад к карточке», «Следующий», Кинопоиск, подборки.

Навигация **с wrap-around**: с последнего фильма «Следующий» → первый, с первого «Предыдущий» → последний.

Состояние: `context.user_data["movie_browser"]` — список, индекс, `display_mode` (`compact` / `details`), collection_id, genre_id.

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
