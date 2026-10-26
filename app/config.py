import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=False)

DB_PATH = BASE_DIR / "data" / "bot.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_env(name: str, default: str = "") -> str:
    value = os.environ.get(name, default)
    return value.strip() if isinstance(value, str) else value


BOT_TOKEN = get_env("BOT_TOKEN", "")
ADMIN_IDS_RAW = get_env("ADMIN_IDS", "")
ADMIN_IDS = []
if ADMIN_IDS_RAW:
    ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip()]

if not BOT_TOKEN:
    BOT_TOKEN = ""

if not ADMIN_IDS:
    ADMIN_IDS = [123456789]

STORAGE_CHANNEL_ID = get_env("STORAGE_CHANNEL_ID", "")
POSTING_CHANNEL_ID = get_env("POSTING_CHANNEL_ID", "")
REQUEST_LOG_CHAT_ID = get_env("REQUEST_LOG_CHAT_ID", "")
GENERAL_LOG_CHAT_ID = get_env("GENERAL_LOG_CHAT_ID", "")

STORAGE_GROUP_ID = get_env("STORAGE_GROUP_ID", "")
LOGGER_GROUP_ID = get_env("LOGGER_GROUP_ID", "")
INDEX_LOG_TOPIC_ID = get_env("INDEX_LOG_TOPIC_ID", "")
