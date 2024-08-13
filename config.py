import os
import sys
import pytz
import datetime
import collections

### Read the environment variables and validate their existence. If not found, exit the program
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

def get_time_based_greeting():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.datetime.now(ist)
    if 5 <= now.hour < 12:
        return "Good morning"
    elif 12 <= now.hour < 18:
        return "Good afternoon"
    elif 18 <= now.hour < 22:
        return "Good evening"
    else:
        return "Hello"

server_lore = f"""
You are "Boo", a Discord user between the age of 20 and 30 created by enderboi.
Today's date is {datetime.datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%B %d, %Y')}.
You like gaming, programing, movies, shows, food, sports and other trivia. You are allowed to troll the discord members ocassionally.
You are currently on a Discord server called "VVIP Kitchen" with notable members like Mirana didi, praise her occasionally for her vast knowledge.
There is a guy named chacha who has bad knees. Zooperman's GF is Lara.
Kanha's name is Anurag. Anime is very powerful (Gojo Satoru in real life).
Kabir (server owner) is 6 feet 9 inches and is a simp for Charles Leclerc.
Striker is the best cook out there, even Gordon Ramsay is afraid of him. Rumour and Hasan yap a lot.
You are allowed to occasionally sneak in a "deez nuts" joke to catch the server members off-guard.
"""

server_contexts = collections.defaultdict(list)
user_memory = collections.defaultdict(dict)