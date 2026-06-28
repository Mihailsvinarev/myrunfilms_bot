from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")


def format_kinopoisk_error(exc: httpx.HTTPStatusError) -> str:
    try:
        message = exc.response.json().get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
        if isinstance(message, list):
            parts = [str(item).strip() for item in message if str(item).strip()]
            if parts:
                return "; ".join(parts)
    except (ValueError, AttributeError, KeyError):
        pass
    return (
        f"Kinopoisk API вернул ошибку {exc.response.status_code}. " "Попробуйте позже."
    )


async def run_kinopoisk(
    operation: Callable[[], Awaitable[T]],
    *,
    log_context: str,
) -> tuple[T | None, str | None]:
    try:
        return await operation(), None
    except RuntimeError as exc:
        return None, str(exc)
    except httpx.HTTPStatusError as exc:
        logger.error(
            "%s Kinopoisk HTTP %s: %s",
            log_context,
            exc.response.status_code,
            exc.request.url,
        )
        return None, format_kinopoisk_error(exc)
    except httpx.HTTPError:
        logger.exception("%s Kinopoisk network error", log_context)
        return None, "Не удалось связаться с Kinopoisk API. Попробуйте позже."
    except Exception:
        logger.exception("%s Kinopoisk operation failed", log_context)
        return None, "Ошибка при обращении к Kinopoisk API. Попробуйте позже."
