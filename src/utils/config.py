import os
import sys
import pytz
import datetime
import collections
from utils.logger import logger
from dotenv import load_dotenv

PREFIX = "!@"
load_dotenv()

### Timezone config: India Standard Time
ist = pytz.timezone("Asia/Kolkata")

### Environment Variables
ENVIRONMENT = os.getenv("ENVIRONMENT")
ADMIN_LIST = os.getenv("ADMIN_LIST")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TENOR_API_KEY = os.getenv("TENOR_API_KEY")
CONTEXT_LIMIT = os.getenv("CONTEXT_LIMIT", 15)
DB_SERVICE_BASE_URL = os.getenv("DB_SERVICE_BASE_URL", "localhost:8080")
TOMORROW_IO_API_KEY = os.getenv("TOMORROW_IO_API_KEY")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL")

MEILI_MASTER_KEY = os.getenv("MEILI_MASTER_KEY")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
VOYAGEAI_API_KEY = os.getenv("VOYAGEAI_API_KEY")

try:
  ADMIN_LIST = [int(item) for item in ADMIN_LIST.split(",")]
except ValueError:
  logger.error(f"ADMIN_LIST must contain only integers and comma. Got: {ADMIN_LIST}")
  sys.exit(1)

try:
  CONTEXT_LIMIT = int(CONTEXT_LIMIT)
except ValueError:
  logger.error(f"CONTEXT_LIMIT must be an integer. Got: {CONTEXT_LIMIT}")
  CONTEXT_LIMIT = 30

for var_name in [
  "ENVIRONMENT",
  "DISCORD_TOKEN",
  "TENOR_API_KEY",
  "DB_SERVICE_BASE_URL",
  "OPENROUTER_API_KEY",
  "OPENROUTER_MODEL",
  "TAVILY_API_KEY",
  "VOYAGEAI_API_KEY",
  "MEILI_MASTER_KEY"
]:
  if not globals()[var_name]:
    logger.error(f"{var_name} environment variable is not set.")
    sys.exit(1)


def get_time_based_greeting():
  now = datetime.datetime.now(ist)
  if 5 <= now.hour < 12:
    return "Good morning"
  elif 12 <= now.hour < 18:
    return "Good afternoon"
  elif 18 <= now.hour < 22:
    return "Good evening"
  else:
    return "Hello"


server_lore = collections.defaultdict(str)
server_contexts = collections.defaultdict(list)
