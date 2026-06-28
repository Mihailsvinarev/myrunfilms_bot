from unittest.mock import MagicMock

import httpx
import pytest

from app.kinopoisk_errors import format_kinopoisk_error, run_kinopoisk


def test_format_kinopoisk_error_uses_api_message():
    response = MagicMock()
    response.json.return_value = {"message": "суточный лимит"}
    exc = httpx.HTTPStatusError("Forbidden", request=MagicMock(), response=response)
    assert "суточный лимит" in format_kinopoisk_error(exc)


@pytest.mark.asyncio
async def test_run_kinopoisk_returns_result():
    async def ok():
        return ["movie"]

    result, error = await run_kinopoisk(ok, log_context="test")
    assert result == ["movie"]
    assert error is None


@pytest.mark.asyncio
async def test_run_kinopoisk_handles_runtime_error():
    async def fail():
        raise RuntimeError("missing key")

    result, error = await run_kinopoisk(fail, log_context="test")
    assert result is None
    assert error == "missing key"
