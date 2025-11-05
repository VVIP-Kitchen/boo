from discord.ext import commands
from utils.logger import logger
from utils.message_utils import send_error_message


class ErrorHandlerCog(commands.Cog):
  def __init__(self, bot: commands.Bot):
    self.bot = bot

  @commands.Cog.listener()
  async def on_command_error(self, ctx, error):
    logger.error(f"Error in command {ctx.command}: {error}")
    await send_error_message(ctx.message)


async def setup(bot: commands.Bot) -> None:
  await bot.add_cog(ErrorHandlerCog(bot))
