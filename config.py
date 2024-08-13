import os
import sys

CONTEXT_LIMIT = os.getenv("CONTEXT_LIMIT", 50)
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_WORKERS_AI_API_KEY = os.getenv("CLOUDFLARE_WORKERS_AI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

try:
    CONTEXT_LIMIT = int(CONTEXT_LIMIT)
except ValueError:
    print(f"Error: CONTEXT_LIMIT must be an integer. Got: {CONTEXT_LIMIT}")
    sys.exit(1)

for var_name in [
    "CLOUDFLARE_ACCOUNT_ID",
    "CLOUDFLARE_WORKERS_AI_API_KEY",
    "DISCORD_TOKEN",
]:
    if not globals()[var_name]:
        print(f"Error: {var_name} environment variable is not set.")
        sys.exit(1)