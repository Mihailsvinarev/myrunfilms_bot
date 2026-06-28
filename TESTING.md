# Testing

## Quick start

```bash
python -m pip install -r requirements-dev.txt
pytest
```

## What is covered

| Test file | Scope |
|-----------|--------|
| `tests/test_query_parser.py` | Парсинг текста запроса |
| `tests/test_kinopoisk_client.py` | HTTP-клиент (mock transport) |
| `tests/test_content_filters.py` | Жанры, лимит, русский текст |
| `tests/test_response_formatter.py` | Формат ответа, ссылки |
| `tests/test_agent.py` | Оркестрация агента |

Kinopoisk API **не вызывается** в unit-тестах — используется `httpx.MockTransport` и `AsyncMock`.

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
