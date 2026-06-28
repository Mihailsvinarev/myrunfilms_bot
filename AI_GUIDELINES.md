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

## Implementation conventions

- Async HTTP via `httpx.AsyncClient` in `app/kinopoisk_client.py`
- Parsing only in `app/query_parser.py`
- Models in `app/models.py` (Pydantic)
- No invented movie titles — only Kinopoisk API results
- Exclude genres: мультфильм, документальный, ток-шоу
- Russian-only descriptions in output
- Do not pad results below requested count

## Mandatory checks before commit

```bash
ruff check .
black --check .
pytest -q
```

If any check fails — fix before committing.

## Typical tasks

| Task | Files |
|------|--------|
| New filter | `query_parser.py`, `kinopoisk_client.py`, `keyboards.py`, tests |
| UI button | `bot_handlers.py`, `keyboards.py` |
| Response format | `response_formatter.py`, `content_filters.py` |
| API change | `kinopoisk_client.py`, `models.py`, tests |
