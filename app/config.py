import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "bot.db"


def get_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


BOT_TOKEN = get_env("BOT_TOKEN", "")
ADMIN_IDS_RAW = get_env("ADMIN_IDS", "")
ADMIN_IDS = []
if ADMIN_IDS_RAW:
    ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip()]

if not BOT_TOKEN:
    # useful for local development
    BOT_TOKEN = ""

# Defaults if no env is set.
if not ADMIN_IDS:
    ADMIN_IDS = [123456789]

# Additional config values from env.
STORAGE_CHANNEL_ID = get_env("STORAGE_CHANNEL_ID", "")
POSTING_CHANNEL_ID = get_env("POSTING_CHANNEL_ID", "")
REQUEST_LOG_CHAT_ID = get_env("REQUEST_LOG_CHAT_ID", "")
GENERAL_LOG_CHAT_ID = get_env("GENERAL_LOG_CHAT_ID", "")
