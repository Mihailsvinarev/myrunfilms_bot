import requests

from app.config import OLLAMA_MODEL, OLLAMA_URL
from app.prompts import SYSTEM_PROMPT
from app.vector_store import search_movies


class MovieAgent:

    def ask(self, user_text: str):

        # 1. semantic search
        results = search_movies(user_text)

        movies = results["documents"][0]

        context = "\n".join(movies)

        # 2. prompt for LLM
        prompt = f"""
Пользователь хочет: {user_text}

Вот похожие фильмы из базы:

{context}

Задача:
- выбери 3 лучших фильма
- объясни почему они подходят
- говори просто и дружелюбно
"""

        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 250,
            },
        }

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=120,
        )

        if response.status_code != 200:
            return f"Ollama error: {response.status_code}"

        return response.json()["message"]["content"]