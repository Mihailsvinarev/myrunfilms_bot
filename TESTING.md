# Testing

## Quick start

```bash
python -m pip install -r requirements-dev.txt
pytest
```

## What is covered

| Test file | Scope |
|-----------|--------|
| `tests/test_agent.py` | Оркестрация поиска и подборок (`MovieAgent`) |
| `tests/test_collections.py` | Подборки, callback_data, genre filter, пустая выдача |
| `tests/test_composition.py` | Composition root и протокол `MovieSearchService` |
| `tests/test_content_filters.py` | Жанры, страны, лимит |
| `tests/test_gigachat_client.py` | Парсинг ответа GigaChat |
| `tests/test_intent_parser.py` | Intent из текста |
| `tests/test_kinopoisk_client.py` | HTTP-клиент (mock transport) |
| `tests/test_kinopoisk_errors.py` | Обработка ошибок Kinopoisk API |
| `tests/test_movie_browser.py` | Карточный браузер: state, wrap-around, caption, клавиатуры, постер |
| `tests/test_query_parser.py` | Парсинг текста запроса |
| `tests/test_query_router.py` | GigaChat-first маршрутизация |
| `tests/test_response_formatter.py` | Формат ответа, ссылки |
| `tests/test_ranker.py` | Ранжирование результатов |
| `tests/test_telegram_utils.py` | Разбиение длинных сообщений |

Kinopoisk API **не вызывается** в unit-тестах — используется `httpx.MockTransport` и `AsyncMock`.

**Не покрыто unit-тестами (осознанно):** async Telegram handlers в `app/handlers/` и интеграция `movie_browser` с Bot API — проверяются вручную smoke-тестом бота.

## Coverage

```bash
pytest --cov=app --cov-report=term-missing -q
```

**Baseline (последний прогон):**

| Область | Coverage |
|---------|----------|
| **Весь `app/`** | **~67%** |
| `query_parser.py` | ~95% |
| `telegram_cards.py` | ~95% |
| `query_router.py` | ~94% |
| `collections.py` | ~84% |
| `kinopoisk_client.py` | ~81% |
| `composition.py`, `protocols.py`, `config.py` | 100% |
| `app/handlers/` | ~0% (Telegram I/O) |
| `movie_browser.py` | ~33% (async UI) |

Перед commit не допускайте заметного падения общего coverage без обоснования.

HTML-отчёт (опционально):

```bash
pytest --cov=app --cov-report=html -q
# открыть htmlcov/index.html
```

## Collections tests

```bash
pytest tests/test_collections.py -q
```

Проверяют:

- построение и разбор `callback_data`;
- что **Любой жанр** не добавляет `genres.name=+...` in API;
- client-side genre filter;
- отсутствие дополнения списка до 20;
- сообщение пустой выдачи.

## Movie browser tests

```bash
pytest tests/test_movie_browser.py -q
```

Проверяют:

- wrap-around навигацию вперёд / назад;
- compact caption без описания и details caption с описанием ≤700 символов;
- переключение режимов compact ↔ details;
- случайный индекс в пределах списка;
- сериализацию состояния (`display_mode`, index) в `user_data`;
- отсутствие постера и layout inline-кнопок;
- скрытие кнопок «Случайный» / «Подборки» для текстового поиска;
- пустой список.

## Linting and formatting

```bash
ruff check .
black --check .
```

Auto-fix locally:

```bash
ruff check . --fix
black .
```

## CI

GitHub Actions workflow `.github/workflows/ci.yml`:

1. `ruff check .`
2. `black --check .`
3. `pytest -q`

Runs on push/PR to `main`.

## Before commit (required)

1. `ruff check .`
2. `black --check .`
3. `pytest -q`
4. `pytest --cov=app --cov-report=term-missing -q` (coverage не ниже baseline ~67%)
5. Code review diff (см. `AI_GUIDELINES.md`)

All steps must pass.
