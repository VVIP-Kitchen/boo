from discord.ext import commands


class GeneralCommands(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.hybrid_command(name="greet", description="Greets the user")
  async def greet(self, ctx):
    await ctx.send(f"{ctx.author} How can I assist you today? 👀")


async def setup(bot):
  await bot.add_cog(GeneralCommands(bot))
