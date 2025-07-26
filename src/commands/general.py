import random
import discord

from datetime import datetime
from discord.ext import commands
from services.db_service import DBService
from services.llm_service import LLMService
from services.tenor_service import TenorService
from services.async_caller_service import to_thread
from services.weather_service import WeatherService
from services.openrouter_service import OpenRouterService
from utils.message_utils import get_channel_messages


def split_text(text, max_length=4096):
  return [text[i : i + max_length] for i in range(0, len(text), max_length)]


class GeneralCommands(commands.Cog):
  """
  Cog for general-purpose commands.
  """

  def __init__(self, bot: commands.Bot) -> None:
    """
    Initialize the GeneralCommands cog.

    Args:
      bot (commands.Bot): The Discord bot instance.
    """

    self.bot = bot
    self.db_service = DBService()
    self.llm_service = LLMService()
    self.tenor_service = TenorService()
    self.weather_service = WeatherService()
    self.openrouter_service = OpenRouterService()

  async def _defer_response(self, ctx: commands.Context) -> None:
    if ctx.interaction:
      await ctx.defer()
    else:
      await ctx.typing()

  def _get_bot_avatar(self, ctx: commands.Context):
    return (
      ctx.bot.user.avatar.url
      if ctx.bot.user.avatar
      else ctx.bot.user.default_avatar.url
    )

  @commands.hybrid_command(name="ping", description="Pings the bot")
  async def respond_with_ping(self, ctx):
    ping = self.bot.latency * 1000
    embed = discord.Embed(title="Pong", description=f"Pong response: {ping:.2f}ms", color=0x7615D1)
    await ctx.send(embed=embed)

  @commands.hybrid_command(name="bonk", description="Bonks a user")
  async def bonk(self, ctx: commands.Context, member: discord.Member) -> None:
    async with ctx.typing():
      bonk_gif = random.choice(self.tenor_service.search())
      await ctx.send(content=f"<@{ctx.author.id}> has bonked <@{member.id}> {bonk_gif['url']}")

  @commands.cooldown(10, 60)
  @commands.hybrid_command(name="skibidi", description="You are my skibidi")
  async def skibidi(self, ctx: commands.Context) -> None:
    """
    Post O Skibidi RE

    Args:
      ctx (commands.Context): The invocation context.
    """
    await ctx.send("SKIBIDI 😍\nhttps://youtu.be/smQ57m7mjSU")

  @commands.hybrid_command(name="weather", description="Get the weather")
  async def weather(self, ctx: commands.Context, location: str) -> None:
    """
    Get the weather for a location.

    Args:
      ctx (commands.Context): The invocation context.
      location (str): The location for which to get the weather.
    """
    location = location.strip()
    if ctx.interaction:
      await ctx.defer()
    else:
      await ctx.typing()

    result = self.weather_service.weather_info(location)
    await ctx.send(result)
  
  @commands.hybrid_command(name="openrouter", description="OpenRouter stats")
  async def get_openrouter_status(self, ctx: commands.Context) -> None:
    if ctx.interaction:
      await ctx.defer()
    else:
      await ctx.typing()
    
    result = self.openrouter_service.get_status()
    await ctx.send(result)
    

  @commands.hybrid_command(name="summary", description="Generate a summary of recent messages in this channel")
  async def generate_summary(self, ctx):
    """
    Generate a summary of recent messages from Redis for the current channel
    """

    await ctx.defer()  # Defer to avoid timeout

    try:
      # Get channel messages from Redis
      channel_messages = get_channel_messages(ctx.channel.id)

      if not channel_messages:
        embed = discord.Embed(
          title="No Messages Found",
          description="No recent messages found for this channel (within the last 15 minutes).",
          color=0xFF6B6B,
        )
        await ctx.send(embed=embed)
        return

      # Format messages for AI summary
      formatted_messages = []
      for msg in channel_messages:
        formatted_messages.append(f"**{msg['author_name']}:** {msg['content']}")

      messages_text = "\n".join(formatted_messages)

      # Create prompt for summary
      summary_prompt = f"Generate a snarky summary for the following Discord channel conversation: {messages_text}"

      # Generate summary using the AI function
      summary, _usage = await to_thread(self.llm_service.chat_completions, prompt=summary_prompt, temperature=0.35, max_tokens=512)


      # Create embed with summary
      embed = discord.Embed(
        title=f"📝 Channel Summary - #{ctx.channel.name}",
        description=summary,
        color=0x7615D1,
        timestamp=datetime.now(),
      )

      embed.add_field(
        name="📊 Messages Analyzed",
        value=f"{len(channel_messages)} messages from the last 15 minutes",
        inline=True,
      )

      if channel_messages:
        embed.add_field(
          name="⏰ Time Range",
          value=f"From {channel_messages[-1]['timestamp'][:19].replace('T', ' ')} to {channel_messages[0]['timestamp'][:19].replace('T', ' ')}",
          inline=False,
        )

      embed.set_footer(text="Summary generated by AI")

      await ctx.send(embed=embed)

    except Exception as e:
      embed = discord.Embed(
        title="❌ Error",
        description=f"Failed to generate summary: {str(e)}",
        color=0xFF0000,
      )
      await ctx.send(embed=embed)

  @commands.hybrid_command(name="get_prompt", description="Get the current system prompt for this server")
  async def get_system_prompt(self, ctx):
    """
    Fetch and display the current system prompt for this guild
    """
    await ctx.defer()  # Defer the response to prevent timeout

    guild = ctx.guild
    if not guild:
      return await ctx.send(
        embed=discord.Embed(
          title="❌ Error",
          description="This command can only be used in a server, no DMs",
          color=0xFF0000,
        )
      )

    try:
      result = self.db_service.fetch_prompt(str(guild.id))
      desc = result.get("system_prompt") if result else "No system prompt set"
      chunks = split_text(desc)
      for i, chunk in enumerate(chunks):
        embed = discord.Embed(
          title=f"System Prompt (Part {i + 1}/{len(chunks)})", description=chunk
        )
        await ctx.send(embed=embed)
    except Exception as e:
      await ctx.send(
        embed=discord.Embed(
          title="❌ Error",
          description=f"Failed to fetch system prompt: {e}",
          color=0xFF0000,
        )
      )


async def setup(bot: commands.Bot) -> None:
  """
  Setup function to add the GeneralCommands cog to the bot.

  Args:
    bot (commands.Bot): The Discord bot instance.
  """

  await bot.add_cog(GeneralCommands(bot))
