import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "7397653738").split(",")))

# Anthropic (Claude)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# OpenAI (Rasm)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Database
DB_PATH = os.getenv("DB_PATH", "data/bot.db")

# Default settings
DEFAULT_DAILY_LIMIT = int(os.getenv("DEFAULT_DAILY_LIMIT", "10"))
DEFAULT_PREMIUM_PRICE = int(os.getenv("DEFAULT_PREMIUM_PRICE", "19900"))
DEFAULT_STARS_PRICE = int(os.getenv("DEFAULT_STARS_PRICE", "100"))
PREMIUM_DAYS = int(os.getenv("PREMIUM_DAYS", "30"))

# Claude model
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
