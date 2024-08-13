import discord
from discord.ext import commands
import collections

def create_bot():
    intents = discord.Intents.default()
    intents.members = True
    bot = commands.Bot(command_prefix="", intents=intents)
    bot.server_contexts = collections.defaultdict(list)
    bot.user_memory = collections.defaultdict(dict)
    return bot