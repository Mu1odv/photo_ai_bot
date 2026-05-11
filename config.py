import os
from dotenv import load_dotenv

load_dotenv()

# Bot tokeni muhim, yo'q bo'lsa ilova ishga tushmaydi.
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN muhit o'zgaruvchisi o'rnatilmagan")

# Admin ID'lari (CSV formatini qo'llab-quvvatlaydi).
_admin_ids_env = os.getenv("ADMIN_IDS")
if _admin_ids_env:
    ADMIN_IDS = [int(val) for val in _admin_ids_env.split(",") if val.strip().isdigit()]
else:
    ADMIN_IDS = [1596222609]

# Ma'lumotlar bazasi yo'li.
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot_database.db")

# Xizmat narxlari.
PHOTO_COST = int(os.getenv("PHOTO_COST", "10"))
VIDEO_COST = int(os.getenv("VIDEO_COST", "20"))

# AI API kalitlari (masalan: Replicate, Stability AI, yoki o'zingizning server)
AI_API_KEY = os.getenv("AI_API_KEY")

def _is_truthy(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")

# Test rejimi: AI kalit yo'q bo'lsa avtomatik yoqiladi.
_test_mode_env = os.getenv("TEST_MODE")
if _test_mode_env is None:
    TEST_MODE = AI_API_KEY in (None, "", "your_key", "your_api_key_here")
else:
    TEST_MODE = _is_truthy(_test_mode_env)

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "0")) if os.getenv("DB_PORT") else None
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# Sinov rejimi sozlamalari
FREE_TRIES = int(os.getenv("FREE_TRIES", "2"))
PRICE_PER_IMAGE = int(os.getenv("PRICE_PER_IMAGE", "5000"))  # So'mda