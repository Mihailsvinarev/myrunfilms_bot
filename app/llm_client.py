import logging

import requests

from app.config import OLLAMA_MODEL, OLLAMA_URL
from app.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def explain_recommendations(prompt: str) -> str:
    logger.info("Calling Ollama model=%s", OLLAMA_MODEL)

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        },
        timeout=120,
    )

    if response.status_code != 200:
        logger.error("Ollama HTTP %s: %s", response.status_code, response.text[:200])
        return f"Ollama error: {response.status_code}"

    content = response.json()["message"]["content"]
    logger.info("Ollama response length=%d", len(content))
    return content
