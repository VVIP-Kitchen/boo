import os
import sys
import pytz
import discord
import requests
import datetime
import collections
from discord.ext import commands

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


intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="", intents=intents)
server_contexts = collections.defaultdict(list)


def get_time_based_greeting():
    ist = pytz.timezone('Asia/Kolkata')
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

user_memory = collections.defaultdict(dict)  # To store facts about users


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")


@bot.event
async def on_message(message):
    global server_lore

    if message.author.bot:
        return

    server_id = message.guild.id
    prompt = str(message.content).strip()

    if "cheen tapak dam dam".strip().lower() in prompt:
        await message.channel.send("https://tenor.com/sMEecgRE0sl.gif")
        return
    
    if prompt.lower().startswith("reset chat"):
        server_contexts[server_id] = []
        await message.channel.send("Context reset! Starting a new conversation.")
        return

    ### Handle user mentions
    if "<@" in prompt:
        mentions = message.mentions
        for mention in mentions:
            user_id = mention.id
            username = mention.name
            prompt = prompt.replace(f"<@{user_id}>", f"@{username}")

    if not message.author.bot and len(prompt) != 0:
        ### Check if the user wants to share some information
        if prompt.lower().startswith("remember that"):
            fact = prompt[len("remember that") :].strip()
            user_memory[message.author.id]["fact"] = fact
            await message.channel.send(f"Got it! I'll remember that {fact}.")
            return

        ### Check if the user wants to recall something
        if prompt.lower().startswith("what do you remember about me"):
            fact = user_memory.get(message.author.id, {}).get(
                "fact", "I don't remember anything specific about you yet."
            )
            await message.channel.send(f"Here's what I remember: {fact}")
            return

        ### Build the context for the conversation
        server_contexts[server_id].append(
            {
                "role": "user",
                "content": message.author.name
                + " (aka "
                + message.author.display_name
                + ")"
                + " said: "
                + prompt,
            }
        )
        messages = [{"role": "system", "content": server_lore}] + server_contexts[
            server_id
        ]

        try:
            response = requests.post(
                f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/meta/llama-3-8b-instruct-awq",
                headers={"Authorization": f"Bearer {CLOUDFLARE_WORKERS_AI_API_KEY}"},
                json={"messages": messages},
            )
            response.raise_for_status()
            result = response.json()
            bot_response = str(result["result"]["response"])
        except requests.RequestException as e:
            print(f"API request failed: {e}")
            bot_response = (
                "Sorry, I'm having trouble thinking right now. Can you try again later?"
            )
        except KeyError:
            print("Unexpected API response format")
            bot_response = "I'm a bit confused. Can you rephrase that?"

        ### Add the bot's response to the conversation context
        server_contexts[server_id].append(
            {"role": "assistant", "content": bot_response}
        )
        await message.channel.send(bot_response)

        # Reset context if it gets too large
        if len(server_contexts[server_id]) >= CONTEXT_LIMIT:
            server_contexts[server_id] = []
            await message.channel.send("Context reset! Starting a new conversation.")

    await bot.process_commands(message)


@bot.command(name="hello")
async def greet(ctx):
    greeting = get_time_based_greeting()
    await ctx.send(f"{greeting}, {ctx.author.name}! How can I assist you today?")


bot.run(DISCORD_TOKEN)
