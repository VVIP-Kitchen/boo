import os
import sys
import pytz

from datetime import datetime
from dotenv import load_dotenv
from utils.logger import logger
from typing import List, Optional

load_dotenv()

PREFIX = "!@"
IST = pytz.timezone("Asia/Kolkata")

ADMIN_LIST: List[int] = []
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "")
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
TENOR_API_KEY: str = os.getenv("TENOR_API_KEY", "")
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "")
MEILI_MASTER_KEY: str = os.getenv("MEILI_MASTER_KEY", "")
VOYAGEAI_API_KEY: str = os.getenv("VOYAGEAI_API_KEY", "")
CONTEXT_LIMIT: int = int(os.getenv("CONTEXT_LIMIT", "30"))
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
TOMORROW_IO_API_KEY: Optional[str] = os.getenv("TOMORROW_IO_API_KEY")
DB_SERVICE_BASE_URL: str = os.getenv("DB_SERVICE_BASE_URL", "localhost:8080")


def _parse_admin_list() -> List[int]:
  admin_str = os.getenv("ADMIN_LIST", "")
  if not admin_str:
    logger.error("ADMIN_LIST environment variable is not set.")
    sys.exit(1)

  try:
    return [int(item.strip()) for item in admin_str.split(",") if item.strip()]
  except ValueError as ve:
    logger.error(f"ADMIN_LIST must contain integers separated by commas. Got: {admin_str}. Error: {ve}")
    sys.exit(1)

def _validate_required_env_vars() -> None:
  required_vars = {
    "ENVIRONMENT": ENVIRONMENT,
    "DISCORD_TOKEN": DISCORD_TOKEN,
    "TENOR_API_KEY": TENOR_API_KEY,
    "DB_SERVICE_BASE_URL": DB_SERVICE_BASE_URL,
    "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
    "OPENROUTER_MODEL": OPENROUTER_MODEL,
    "TAVILY_API_KEY": TAVILY_API_KEY,
    "VOYAGEAI_API_KEY": VOYAGEAI_API_KEY,
    "MEILI_MASTER_KEY": MEILI_MASTER_KEY,
  }

  missing_vars = [name for name, value in required_vars.items() if not value]
  if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

def get_time_based_greeting() -> str:
  now = datetime.now(IST)
  hour = now.hour

  if 5 <= hour < 12:
    return "Good morning"
  elif 12 <= hour < 18:
    return "Good afternoon"
  elif 18 <= hour < 22:
    return "Good evening"
  else:
    return "Hello"


ADMIN_LIST = _parse_admin_list()

_validate_required_env_vars()

logger.info(f"Configuration loaded successfully for environment: {ENVIRONMENT}")
