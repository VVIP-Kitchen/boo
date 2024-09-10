import discord
from discord.ext import commands
from utils.config import DISCORD_TOKEN, PREFIX, ADMIN_LIST


class DiscordBot(commands.Bot):
  """
  Custom Discord bot class that extends commands.Bot.
  """

  def __init__(self) -> None:
    """
    Initialize the DiscordBot with custom intents and command prefix.
    """
    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True
    super().__init__(command_prefix=PREFIX, intents=intents, owner_ids=set(ADMIN_LIST))

  async def is_owner(self, user: discord.User):
    if user.id in self.owner_ids:
      return True

    ### Else fall back to the original
    return await super().is_owner(user)

  async def setup_hook(self) -> None:
    """
    Asynchronous setup hook to load initial extensions.
    """

    ### Load necessary extensions
    await self.load_extension("bot.events")
    await self.load_extension("commands.general")
    await self.load_extension("commands.admin")
    await self.load_extension("jishaku")

  def run(self) -> None:
    """
    Run the bot using the Discord token from configuration.
    """
    super().run(DISCORD_TOKEN)
