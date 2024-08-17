from services.llm_service import LLMService
from discord.ext import commands
from discord import File


class GeneralCommands(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.llm_service = LLMService()

  @commands.hybrid_command(name="greet", description="Greets the user")
  async def greet(self, ctx):
    await ctx.send(f"{ctx.author} How can I assist you today? 👀")

  @commands.hybrid_command(
    name="imagine", description="Generates an image from a prompt"
  )
  async def imagine(self, ctx, prompt):
    await ctx.send(file=File(self.llm_service.generate_image(prompt), "output.png"))


async def setup(bot):
  await bot.add_cog(GeneralCommands(bot))
