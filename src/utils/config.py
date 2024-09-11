import os
import sys
import pytz
import datetime
import collections
from utils.logger import logger

PREFIX = "!@"

### Timezone config: India Standard Time
ist = pytz.timezone("Asia/Kolkata")

### Environment Variables
ADMIN_LIST = os.getenv("ADMIN_LIST")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TENOR_API_KEY = os.getenv("TENOR_API_KEY")
CONTEXT_LIMIT = os.getenv("CONTEXT_LIMIT", 30)
DB_SERVICE_BASE_URL = os.getenv("DB_SERVICE_BASE_URL")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_WORKERS_AI_API_KEY = os.getenv("CLOUDFLARE_WORKERS_AI_API_KEY")
TOMORROW_IO_API_KEY = os.getenv("TOMORROW_IO_API_KEY")

GH_MODEL_NAME = os.getenv("GH_MODEL_NAME", "meta-llama-3.1-8b-instruct")
CF_WORKERS_MODEL_NAME = os.getenv(
  "CF_WORKERS_MODEL_NAME", "@cf/meta/llama-3.1-8b-instruct"
)
CF_WORKERS_IMAGE_MODEL_NAME = os.getenv(
  "CF_WORKERS_IMAGE_MODEL_NAME", "@cf/stabilityai/stable-diffusion-xl-base-1.0"
)
CF_WORKERS_IMAGE_DESCRIPTION_MODEL_NAME = os.getenv(
  "CF_WORKERS_IMAGE_DESCRIPTION_MODEL_NAME", "@cf/llava-hf/llava-1.5-7b-hf"
)

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
  "GITHUB_TOKEN",
  "DISCORD_TOKEN",
  "TENOR_API_KEY",
  "DB_SERVICE_BASE_URL",
  "CLOUDFLARE_ACCOUNT_ID",
  "CLOUDFLARE_WORKERS_AI_API_KEY",
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
user_memory = collections.defaultdict(dict)
