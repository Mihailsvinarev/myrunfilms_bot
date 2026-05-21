# AI Movie Recommendation Bot

Telegram-бот для подбора фильмов и сериалов по запросу на естественном языке.

**Стек:** Telegram Bot API → TMDB Discover → Ollama (объяснение рекомендаций).

---

## Возможности

- Поиск фильмов и сериалов через TMDB Discover API
- Фильтры: жанр, страна, год
- Режим «фильмы режиссёра» (`with_crew`)
- LLM только объясняет уже найденные тайтлы (не придумывает названия)

---

## Архитектура

```
User → main.py (Telegram)
     → MovieAgent (app/agent.py)
         → TMDB Discover (app/tmdb_client.py)
         → Context builder (app/context_builder.py)
         → Ollama (app/llm_client.py)
     → Response
```

| Модуль | Назначение |
|--------|------------|
| `main.py` | Telegram handlers, polling |
| `app/agent.py` | Оркестрация запроса |
| `app/tmdb_client.py` | Discover API, парсинг intent |
| `app/context_builder.py` | Сбор контекста для LLM |
| `app/llm_client.py` | Вызов Ollama |
| `app/messages.py` | Сообщения пользователю |
| `app/logging_setup.py` | Логирование (UTF-8 на Windows) |

---

## Требования

- Python 3.11+
- [Ollama](https://ollama.com/) (локально, порт `11434`)
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
OLLAMA_MODEL=llama3.2
```

Запустите Ollama и скачайте модель:

```bash
ollama pull llama3.2
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
