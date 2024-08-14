import discord
from discord.ext import commands
from llm.api import call_model
from utils.utils import handle_user_mentions, replace_emojis
from utils.config import (
    CONTEXT_LIMIT,
    DISCORD_TOKEN,
    server_lore,
    server_contexts,
)

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!@", intents=intents)


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    bot.custom_emojis = {}
    for guild in bot.guilds:
        for emoji in guild.emojis:
            bot.custom_emojis[emoji.name] = emoji

    print(f"Loaded {len(bot.custom_emojis)} custom emojis.")


@bot.event
async def on_message(message):
    server_id = message.guild.id
    prompt = str(message.content).strip()

    if len(prompt) == 0 or message.author.bot:
        return

    if message.channel.name != "chat":
        await message.channel.send("Ping me in #chat to talk")
        return

    if "reset chat" in prompt.lower():
        server_contexts[server_id] = []
        await message.channel.send("Context reset! Starting a new conversation.")
        return

    prompt = handle_user_mentions(prompt, message)
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
    messages = [{"role": "system", "content": server_lore}] + server_contexts[server_id]

    bot_response = call_model(messages)
    bot_response_with_emojis = replace_emojis(bot_response, bot.custom_emojis)
    server_contexts[server_id].append({"role": "assistant", "content": bot_response})
    await message.channel.send(bot_response_with_emojis, reference=message)

    ### Reset context if it gets too large
    if len(server_contexts[server_id]) >= CONTEXT_LIMIT:
        server_contexts[server_id] = []
        await message.channel.send("Context reset! Starting a new conversation.")

    await bot.process_commands(message)


bot.run(DISCORD_TOKEN)
