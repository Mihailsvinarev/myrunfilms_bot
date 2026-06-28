import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
KINOPOISK_API_KEY = os.getenv("KINOPOISK_API_KEY")

KINOPOISK_BASE_URL = "https://api.poiskkino.dev/v1.4"

GIGACHAT_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY")
GIGACHAT_OAUTH_URL = os.getenv(
    "GIGACHAT_OAUTH_URL",
    "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
)
GIGACHAT_API_URL = os.getenv(
    "GIGACHAT_API_URL",
    "https://gigachat.devices.sberbank.ru/api/v1",
)
GIGACHAT_MODEL = os.getenv("GIGACHAT_MODEL", "GigaChat")
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
GIGACHAT_TIMEOUT = float(os.getenv("GIGACHAT_TIMEOUT", "30"))
GIGACHAT_VERIFY_SSL = os.getenv("GIGACHAT_VERIFY_SSL", "true").lower() == "true"
