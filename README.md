# AI Movie Recommendation Bot

Telegram-бот для подбора фильмов и сериалов по запросу на естественном языке.

**Стек:** Telegram Bot API → TMDB Discover → форматированный ответ (без LLM).

---

## Возможности

- Поиск фильмов и сериалов через TMDB Discover API
- Фильтры: жанр, страна, год, количество («3 сериала»)
- Режим «фильмы режиссёра» (`with_crew`)
- Ответ собирается в коде из данных TMDB — названия не выдумываются

---

## Архитектура

```
User → main.py (Telegram)
     → MovieAgent (app/agent.py)
         → TMDB Discover (app/tmdb_client.py)
         → Cards + formatter (context_builder, response_formatter)
     → Response
```

| Модуль | Назначение |
|--------|------------|
| `main.py` | Telegram handlers, polling |
| `app/agent.py` | Оркестрация запроса |
| `app/tmdb_client.py` | Discover API, парсинг intent (`parse_count`, страна, год) |
| `app/context_builder.py` | Карточки тайтлов из TMDB |
| `app/response_formatter.py` | Текст ответа пользователю |
| `app/messages.py` | Сообщения «ничего не найдено» |
| `app/logging_setup.py` | Логирование (UTF-8 на Windows) |

---

## Требования

- Python 3.11+
- API-ключ [TMDB](https://www.themoviedb.org/settings/api)
- Telegram Bot Token ([@BotFather](https://t.me/BotFather))

---

## Установка

```bash
python -m pip install -r requirements.txt
```

Создайте `.env` в корне проекта:

```env
BOT_TOKEN=your_telegram_bot_token
TMDB_API_KEY=your_tmdb_api_key
```

Запуск бота:

```bash
python main.py
```

---

## Примеры запросов

- `российский сериал 2020 детектив`
- `фильм комедия 2015`
- `фильмы режиссёра Кристофера Нолана`

---

## Тесты

Проверка TMDB Discover (нужен `TMDB_API_KEY` в `.env`):

```bash
python test_tmdb.py
```

---

## Структура проекта

```
movie_ai_bot/
├── main.py
├── app/
│   ├── agent.py
│   ├── tmdb_client.py
│   ├── context_builder.py
│   ├── llm_client.py
│   ├── messages.py
│   ├── logging_setup.py
│   ├── config.py
│   └── prompts.py
├── test_tmdb.py
└── requirements.txt
```
