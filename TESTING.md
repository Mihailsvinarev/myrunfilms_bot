# Testing

## Quick start

```bash
python -m pip install -r requirements-dev.txt
pytest
```

## What is covered

| Test file | Scope |
|-----------|--------|
| `tests/test_collections.py` | Подборки, callback_data, genre filter, пустая выдача |
| `tests/test_kinopoisk_errors.py` | Обработка ошибок Kinopoisk API |
| `tests/test_movie_browser.py` | Карточный браузер: индекс, caption, постер, границы |
| `tests/test_genres.py` | Конфигурация жанров (если добавлен) |
| `tests/test_query_parser.py` | Парсинг текста запроса |
| `tests/test_query_router.py` | GigaChat-first маршрутизация |
| `tests/test_kinopoisk_client.py` | HTTP-клиент (mock transport) |
| `tests/test_content_filters.py` | Жанры, страны, лимит |
| `tests/test_response_formatter.py` | Формат ответа, ссылки |
| `tests/test_agent.py` | Оркестрация агента |

Kinopoisk API **не вызывается** в unit-тестах — используется `httpx.MockTransport` и `AsyncMock`.

## Collections tests

```bash
pytest tests/test_collections.py -q
```

Проверяют:

- построение и разбор `callback_data`;
- что **Любой жанр** не добавляет `genres.name=+...` в API;
- client-side genre filter;
- отсутствие дополнения списка до 20;
- сообщение пустой выдачи.

## Movie browser tests

```bash
pytest tests/test_movie_browser.py -q
```

Проверяют:

- переход вперёд / назад и wrap-around;
- случайный индекс в пределах списка;
- сериализацию состояния в `user_data`;
- caption и отсутствие постера;
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

All three must pass.
