# AI Guidelines (Cursor)

## Project context

Telegram Movie Bot. Data source: **Kinopoisk Dev API only**. Do not reintroduce TMDB or LLM-generated movie lists.

Read first:

- `ARCHITECTURE.md` — module layout
- `TESTING.md` — required checks
- `.cursor/rules/project.mdc` — project rules

## How to use Cursor

1. Open the repo root in Cursor.
2. Describe the task in chat (Agent mode).
3. Ask the agent to read relevant files before editing.
4. Review the diff before commit.
5. Run checks locally or rely on CI.

## Allowed automatic changes

The agent **may** change without asking:

- `app/` business logic
- `tests/`
- `main.py` wiring (handlers, logging)
- `requirements*.txt`, `pyproject.toml`, `Dockerfile`, `docker-compose.yml`
- Documentation: `README.md`, `ARCHITECTURE.md`, `TESTING.md`, this file

## Requires explicit user approval

- `.env`, secrets, API keys
- `venv/`, `chroma_db/`, `data/`
- Git push / force push
- Removing user-facing bot features without request
- Switching data source away from Kinopoisk

## High-risk zones

Changes here can break search quality, data integrity, or production secrets. Always require human review and full test run:

| Zone | Why risky |
|------|-----------|
| `app/kinopoisk_client.py` | HTTP params, pagination, field mapping — wrong query = wrong or empty results |
| `app/query_parser.py` | Intent parsing — affects every text search |
| `app/gigachat_client.py` | LLM routing — can misroute or drop filters |
| `app/content_filters.py` | Genre/country exclusions — business rules |
| `app/collections.py` | Curated lists and API params for collections |
| `app/composition.py` | DI wiring — wrong binding breaks entire app |
| `.env`, `app/config.py` | Secrets and runtime config |
| `main.py` handler order | Wrong order can swallow commands or callbacks |

Lower risk but still test after change: `telegram_cards.py`, `keyboards.py`, `response_formatter.py`.

## Implementation conventions

- Async HTTP via `httpx.AsyncClient` in `app/kinopoisk_client.py`
- Parsing only in `app/query_parser.py`
- Models in `app/models.py` (Pydantic)
- No invented movie titles — only Kinopoisk API results
- Exclude genres: мультфильм, документальный, ток-шоу
- Russian-only descriptions in output
- Do not pad results below requested count

## Mandatory checks after every AI change

Run in order; do not commit if any step fails.

### 1. Lint and format

```bash
ruff check .
black --check .
```

### 2. Tests

```bash
pytest -q
pytest --cov=app --cov-report=term-missing -q
```

Coverage must not drop significantly vs baseline in `TESTING.md`.

### 3. Build (install sanity)

```bash
python -m pip install -r requirements-dev.txt
python -c "from app.composition import build_app_services; build_app_services()"
```

For Docker path:

```bash
docker compose build
```

### 4. Code review (human)

Before commit, developer must:

- read the full `git diff`;
- verify no secrets, no invented movie data, no TMDB reintroduction;
- confirm handler/UI behaviour matches the task;
- smoke-test the bot locally if UI or handlers changed (`python main.py` + one text query and one collection).

### 5. CI

Push only after local steps pass; confirm GitHub Actions is green on the branch.

## Typical tasks

| Task | Files |
|------|--------|
| New filter | `query_parser.py`, `kinopoisk_client.py`, `keyboards.py`, tests |
| UI button | `bot_handlers.py`, `keyboards.py` |
| Response format | `response_formatter.py`, `content_filters.py` |
| API change | `kinopoisk_client.py`, `models.py`, tests |
