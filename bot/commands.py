from discord.ext import commands
from bot.utils import get_time_based_greeting

def setup(bot):
    @bot.command(name="hello")
    async def greet(ctx):
        greeting = get_time_based_greeting()
        await ctx.send(f"{greeting}, {ctx.author.name}! How can I assist you today?")