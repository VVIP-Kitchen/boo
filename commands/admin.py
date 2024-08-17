from discord.ext import commands
from utils.config import ADMIN_LIST


class AdminCommands(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.command()
  async def sync(self, ctx):
    if ctx.author.id not in ADMIN_LIST:
      await ctx.author.send("You do not have permission to use this command ❌")
      return
    await self.bot.tree.sync()
    await ctx.reply("Command Tree is synced, slash commands are updated ✔️")


async def setup(bot):
  await bot.add_cog(AdminCommands(bot))
