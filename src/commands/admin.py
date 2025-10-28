from discord.ext import commands


class AdminCommands(commands.Cog):
  """
  Cog for administrative commands.
  """

  def __init__(self, bot: commands.Bot) -> None:
    """
    Initialize the AdminCommands cog.

    Args:
      bot (commands.Bot): The Discord bot instance.
    """
    self.bot = bot

  @commands.command()
  async def sync(self, ctx: commands.Context) -> None:
    """
    Synchronize the command tree for slash commands.

    This command can only be used by users in the ADMIN_LIST.

    Args:
      ctx (commands.Context): The invocation context.
    """

    if not await self.bot.is_owner(ctx.author):
      await ctx.author.send("You do not have permission to use this command ❌")
      return
    await self.bot.tree.sync()
    await ctx.reply("Command Tree is synced, slash commands are updated ✔️")

  @commands.command()
  @commands.is_owner()
  async def reload(self, ctx: commands.Context, cog: str) -> None:
    """
    Reload a cog.

    Args:
      ctx (commands.Context): The invocation context.
      cog (str): The name of the cog to reload.
    """
    await self.bot.reload_extension(f"cogs.{cog}")
    await ctx.send(f"Cog {cog} reloaded")

async def setup(bot: commands.Bot) -> None:
  """
  Setup function to add the AdminCommands cog to the bot.

  Args:
    bot (commands.Bot): The Discord bot instance.
  """
  await bot.add_cog(AdminCommands(bot))
