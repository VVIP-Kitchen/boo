import datetime
import pytz
from discord.ext import commands
from bot.utils import get_time_based_greeting
from services.ai_service import get_ai_response
from config import CONTEXT_LIMIT

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


def setup(bot):
    @bot.event
    async def on_ready():
        print(f"{bot.user} has connected to Discord!")

    @bot.event
    async def on_message(message):
        if message.author.bot:
            return

        server_id = message.guild.id
        prompt = str(message.content).strip()

        if "cheen tapak dam dam".strip().lower() in prompt:
            await message.channel.send("https://tenor.com/sMEecgRE0sl.gif")
            return

        if prompt.lower().startswith("reset chat"):
            bot.server_contexts[server_id] = []
            await message.channel.send("Context reset! Starting a new conversation.")
            return

        if "<@" in prompt:
            mentions = message.mentions
            for mention in mentions:
                user_id = mention.id
                username = mention.name
                prompt = prompt.replace(f"<@{user_id}>", f"{username}")

        if not message.author.bot and len(prompt) != 0:
            if prompt.lower().startswith("remember that"):
                fact = prompt[len("remember that") :].strip()
                bot.user_memory[message.author.id]["fact"] = fact
                await message.channel.send(f"Got it! I'll remember that {fact}.")
                return

            if prompt.lower().startswith("what do you remember about me"):
                fact = bot.user_memory.get(message.author.id, {}).get(
                    "fact", "I don't remember anything specific about you yet."
                )
                await message.channel.send(f"Here's what I remember: {fact}")
                return

            bot.server_contexts[server_id].append(
                {
                    "role": "user",
                    "content": f"{message.author.name} (aka {message.author.display_name}) said: {prompt}",
                }
            )
            messages = [
                {"role": "system", "content": server_lore}
            ] + bot.server_contexts[server_id]

            bot_response = await get_ai_response(messages)
            bot.server_contexts[server_id].append(
                {"role": "assistant", "content": bot_response}
            )
            await message.channel.send(bot_response)

            if len(bot.server_contexts[server_id]) >= CONTEXT_LIMIT:
                bot.server_contexts[server_id] = []
                await message.channel.send(
                    "Context reset! Starting a new conversation."
                )

        await bot.process_commands(message)
