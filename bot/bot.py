import discord
from discord.ext import commands
from utils.config import DISCORD_TOKEN, PREFIX


class DiscordBot(commands.Bot):
  def __init__(self):
    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True
    super().__init__(command_prefix=PREFIX, intents=intents)

  async def setup_hook(self):
    await self.load_extension("bot.events")
    await self.load_extension("commands.general")
    await self.load_extension("commands.admin")

  def run(self):
    super().run(DISCORD_TOKEN)
