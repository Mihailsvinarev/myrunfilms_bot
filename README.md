# AI Movie Recommendation Bot

Telegram-бот для подбора фильмов и сериалов по запросу на естественном языке.

**Стек:** Telegram Bot API → Kinopoisk Dev API → форматированный ответ.

---

## Возможности

- **Подбор по фильтрам** (кнопки): жанр → год → страна → фильм/сериал → студия
- **Поиск по тексту**: жанр, страна, год, Netflix/Marvel/HBO
- Исключение мультфильмов, документального, реалити
- Только русские описания из Kinopoisk
- Прямые ссылки на kinopoisk.ru

---

## Быстрый старт

### Локально

```bash
python -m pip install -r requirements-dev.txt
cp .env.example .env   # заполните BOT_TOKEN и KINOPOISK_API_KEY
python main.py
```

### Docker

```bash
cp .env.example .env
docker compose up --build
```

---

## Документация

- [ARCHITECTURE.md](ARCHITECTURE.md) — архитектура
- [TESTING.md](TESTING.md) — тесты и CI
- [AI_GUIDELINES.md](AI_GUIDELINES.md) — правила для Cursor / AI

---

## Проверки перед commit

```bash
ruff check .
black --check .
pytest -q
```

---

## Примеры запросов

- `3 детективных сериала России 2021`
- `Сериалы Netflix 2025`
- `/filters` или кнопка «⚙️ Подбор по фильтрам»
