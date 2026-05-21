import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

OLLAMA_URL = "http://localhost:11434/api/chat"

TMDB_API_KEY = os.getenv("TMDB_API_KEY")