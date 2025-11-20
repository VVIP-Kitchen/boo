import os
import sys
import pytz
from typing import List, Optional
from datetime import datetime
from dotenv import load_dotenv
from utils.logger import logger

# Load environment variables first
load_dotenv()

# Constants
PREFIX = "!@"
IST = pytz.timezone("Asia/Kolkata")

# Environment Variables
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "")
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
TENOR_API_KEY: str = os.getenv("TENOR_API_KEY", "")
TOMORROW_IO_API_KEY: Optional[str] = os.getenv("TOMORROW_IO_API_KEY")
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "")
MEILI_MASTER_KEY: str = os.getenv("MEILI_MASTER_KEY", "")
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
VOYAGEAI_API_KEY: str = os.getenv("VOYAGEAI_API_KEY", "")
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
DB_SERVICE_BASE_URL: str = os.getenv("DB_SERVICE_BASE_URL", "localhost:8080")
MANAGER_API_TOKEN: str = os.getenv("MANAGER_API_TOKEN", "")


def _parse_admin_list() -> List[int]:
  """Parse and validate ADMIN_LIST from environment."""
  admin_str = os.getenv("ADMIN_LIST", "")
  if not admin_str:
    logger.error("ADMIN_LIST environment variable is not set.")
    sys.exit(1)

  try:
    return [int(item.strip()) for item in admin_str.split(",") if item.strip()]
  except ValueError as e:
    logger.error(
      f"ADMIN_LIST must contain only integers separated by commas. "
      f"Got: {admin_str}. Error: {e}"
    )
    sys.exit(1)


def _parse_context_limit() -> int:
  """Parse and validate CONTEXT_LIMIT from environment."""
  limit_str = os.getenv("CONTEXT_LIMIT", "30")
  try:
    limit = int(limit_str)
    if limit <= 0:
      logger.warning(f"CONTEXT_LIMIT must be positive. Got: {limit}. Using default: 30")
      return 30
    return limit
  except ValueError:
    logger.warning(
      f"CONTEXT_LIMIT must be an integer. Got: {limit_str}. Using default: 30"
    )
    return 30


def _validate_required_env_vars() -> None:
  """Validate that all required environment variables are set."""
  required_vars = {
    "ENVIRONMENT": ENVIRONMENT,
    "DISCORD_TOKEN": DISCORD_TOKEN,
    "TENOR_API_KEY": TENOR_API_KEY,
    "DB_SERVICE_BASE_URL": DB_SERVICE_BASE_URL,
    "MANAGER_API_TOKEN": MANAGER_API_TOKEN,
    "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
    "OPENROUTER_MODEL": OPENROUTER_MODEL,
    "TAVILY_API_KEY": TAVILY_API_KEY,
    "VOYAGEAI_API_KEY": VOYAGEAI_API_KEY,
    "MEILI_MASTER_KEY": MEILI_MASTER_KEY,
    "GITHUB_TOKEN": GITHUB_TOKEN,
  }

  missing_vars = [name for name, value in required_vars.items() if not value]

  if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)


def get_time_based_greeting() -> str:
  """Get a greeting based on the current time in IST."""
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


# Initialize parsed values
ADMIN_LIST: List[int] = _parse_admin_list()
CONTEXT_LIMIT: int = _parse_context_limit()

# Validate all required environment variables
_validate_required_env_vars()

logger.info(f"Configuration loaded successfully for environment: {ENVIRONMENT}")
