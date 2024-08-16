import discord

from discord.ext import commands

from llm.api import call_model
from utils.utils import handle_user_mentions, replace_emojis
from utils.config import (
    CONTEXT_LIMIT,
    DISCORD_TOKEN,
    ADMIN_LIST,
    server_lore,
    server_contexts,
)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
prefix = "!@"
bot = commands.Bot(command_prefix=prefix, intents=intents)


@bot.event
async def on_ready():
    print(f"[INFO] {bot.user} has connected to Discord!")

    bot.custom_emojis = {}
    for guild in bot.guilds:
        for emoji in guild.emojis:
            bot.custom_emojis[emoji.name] = emoji

    print(f"[INFO] Loaded {len(bot.custom_emojis)} custom emojis.")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    prompt = str(message.content).strip()
    if len(prompt) == 0:
        return

    if message.content.startswith(prefix):
        await bot.process_commands(message)
        return

    if message.guild is None:
        server_id = f"DM_{message.author.id}"  ### This is a DM
    else:
        server_id = message.guild.id
        is_direct_reply = (
            message.reference
            and message.reference.resolved
            and message.reference.resolved.author == bot.user
        )
        is_mention = bot.user in message.mentions
        if not (is_direct_reply or is_mention) or message.channel.name != "chat":
            return

    if "reset chat" in prompt.lower():
        server_contexts[server_id] = []
        await message.channel.send("Context reset! 🥸 Starting a new conversation. 👋")
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

    ### Start the typing indicator
    async with message.channel.typing():
        bot_response = call_model(messages)
        bot_response_with_emojis = replace_emojis(bot_response, bot.custom_emojis)
        server_contexts[server_id].append({"role": "assistant", "content": bot_response})

    await message.channel.send(bot_response_with_emojis, reference=message)

    ### Reset context if it gets too large
    if len(server_contexts[server_id]) >= CONTEXT_LIMIT:
        server_contexts[server_id] = []
        await message.channel.send("Context reset! Starting a new conversation.")


@bot.hybrid_command(name="greet", description="Greets the user")
async def greet(ctx):
    await ctx.send(f"{ctx.author} How can I assist you today? 👀")


bot.command()
async def sync(message):
    if message.author.id not in ADMIN_LIST:
        message.author.send("You do not have permission to use this command ❌")
        return
    await bot.tree.sync()
    await message.reply("Command Tree is synced, slash commands are updated ✔️")


bot.run(DISCORD_TOKEN)
