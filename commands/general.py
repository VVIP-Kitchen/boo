import io
from discord import File
from discord.ext import commands
from services.llm_service import LLMService


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
  async def imagine(self, ctx, *, prompt: str):
    if ctx.interaction:
      await ctx.defer()
    else:
      await ctx.typing()

    result = self.llm_service.generate_image(prompt)

    if isinstance(result, io.BytesIO):
      file = File(result, "output.png")
      await ctx.send(file=file)
    else:
      await ctx.send(result)


async def setup(bot):
  await bot.add_cog(GeneralCommands(bot))
