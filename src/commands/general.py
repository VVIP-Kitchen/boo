import random
import discord

from datetime import datetime
from discord.ext import commands
from services.db_service import DBService
from services.llm_service import LLMService
from services.tenor_service import TenorService
from services.async_caller_service import to_thread
from services.weather_service import WeatherService
from utils.message_utils import get_channel_messages
from services.openrouter_service import OpenRouterService
from services.tool_calling_service import get_tavily_usage


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
  
  @commands.hybrid_command(name="tavily", description="Tavily stats")
  async def get_tavily_status(self, ctx: commands.Context) -> None:
    if ctx.interaction:
      await ctx.defer()
    else:
      await ctx.typing()
    
    try:
      result = get_tavily_usage()
      
      # Create embed
      embed = discord.Embed(
        title="🔍 Tavily API Usage Statistics",
        color=0x00ff88,  # Green color
        timestamp=discord.utils.utcnow()
      )
      
      # Helper function to safely calculate percentage
      def safe_percentage(usage, limit):
        if limit is None or limit == 0:
          return 0.0
        return (usage / limit) * 100
      
      # Helper function to format usage display
      def format_usage(usage, limit):
        if limit is None:
          return f"**{usage:,}** / **Unlimited**"
        return f"**{usage:,}** / **{limit:,}**"
      
      # Key usage field
      key_usage = result.get("key", {}).get("usage", 0)
      key_limit = result.get("key", {}).get("limit")
      key_percentage = safe_percentage(key_usage, key_limit)
      
      embed.add_field(
        name="🔑 Key Usage",
        value=f"{format_usage(key_usage, key_limit)} requests\n"
              f"**{key_percentage:.1f}%** used" if key_limit else "**Unlimited**",
        inline=True
      )
      
      # Account plan info
      account_data = result.get("account", {})
      current_plan = account_data.get("current_plan", "Unknown")
      plan_usage = account_data.get("plan_usage", 0)
      plan_limit = account_data.get("plan_limit")
      plan_percentage = safe_percentage(plan_usage, plan_limit)
      
      embed.add_field(
        name="📋 Plan Usage",
        value=f"**Plan:** {current_plan}\n"
              f"{format_usage(plan_usage, plan_limit)} requests\n"
              f"**{plan_percentage:.1f}%** used" if plan_limit else "**Unlimited**",
        inline=True
      )
      
      # Pay-as-you-go usage
      paygo_usage = account_data.get("paygo_usage", 0)
      paygo_limit = account_data.get("paygo_limit")
      paygo_percentage = safe_percentage(paygo_usage, paygo_limit)
      
      embed.add_field(
        name="💳 Pay-as-you-go",
        value=f"{format_usage(paygo_usage, paygo_limit)} requests\n"
              f"**{paygo_percentage:.1f}%** used" if paygo_limit else "**Unlimited**",
        inline=True
      )
      
      # Add usage bars for visual representation
      def create_progress_bar(percentage, length=10):
        if percentage == 0:
          return "`░░░░░░░░░░` 0.0%"
        filled = int(percentage / 100 * length)
        bar = "█" * filled + "░" * (length - filled)
        return f"`{bar}` {percentage:.1f}%"
      
      # Only add progress bars if we have valid limits
      progress_fields = []
      if key_limit is not None:
        progress_fields.append(f"**Key:** {create_progress_bar(key_percentage)}")
      if plan_limit is not None:
        progress_fields.append(f"**Plan:** {create_progress_bar(plan_percentage)}")
      if paygo_limit is not None:
        progress_fields.append(f"**PayGo:** {create_progress_bar(paygo_percentage)}")
      
      if progress_fields:
        embed.add_field(
          name="📊 Usage Overview",
          value="\n".join(progress_fields),
          inline=False
        )
      
      # Set footer
      embed.set_footer(text="Tavily API Statistics")
      
      # Send the embed
      if ctx.interaction:
        await ctx.followup.send(embed=embed)
      else:
        await ctx.send(embed=embed)

    except Exception as e:
      # Error handling
      error_embed = discord.Embed(
        title="❌ Error",
        description="Failed to fetch Tavily usage statistics:\n",
        color=0xff0000
      )
      
      if ctx.interaction:
        await ctx.followup.send(embed=error_embed)
      else:
        await ctx.send(embed=error_embed)

  @commands.hybrid_command(name="token_stats", description="Show LLM token usage stats for this server (and/or specific user)")
  async def get_token_stats(
    self,
    ctx: commands.Context,
    user: discord.Member = None,
    period: str = "daily"
  ) -> None:
    await ctx.defer()
    guild = ctx.guild
    if not guild:
      embed = discord.Embed(
        title="❌ Error",
        description="This command can only be used in a server",
        color=0xFF0000,
      )
      return await ctx.send(embed=embed)
    
    target_user = user or ctx.author
    valid_periods = ["daily", "weekly", "monthly", "yearly"]
    if period.lower() not in valid_periods:
      embed = discord.Embed(
        title="❌ Invalid Period",
        description=f"Period must be one of: {', '.join(valid_periods)}",
        color=0xFF0000,
      )
      return await ctx.send(embed=embed)
    
    try:
      stats = self.db_service.get_token_stats(
        guild_id=str(guild.id),
        author_id=str(target_user.id),
        period=period.lower()
      )

      if not stats:
        embed = discord.Embed(
          title="📊 Token Usage Statistics",
          description=f"No token usage data found for {target_user.display_name} in the {period} period.",
          color=0x7615D1,
          timestamp=datetime.now(),
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)
        return await ctx.send(embed=embed)
      
      total_input = sum(usage.get('input_tokens', 0) for usage in stats)
      total_output = sum(usage.get('output_tokens', 0) for usage in stats)
      total_tokens = total_input + total_output
      total_messages = len(stats)

      avg_input = total_input / total_messages if total_messages > 0 else 0
      avg_output = total_output / total_messages if total_messages > 0 else 0
      avg_total = total_tokens / total_messages if total_messages > 0 else 0

      embed = discord.Embed(
        title="📊 Token Usage Statistics",
        description=f"Token usage for **{target_user.display_name}** ({period} period)",
        color=0x7615D1,
        timestamp=datetime.now(),
      )
      embed.set_thumbnail(url=target_user.display_avatar.url)

      embed.add_field(
        name="📥 Input Tokens",
        value=f"**Total:** {total_input:,}\n**Average:** {avg_input:.1f} per message",
        inline=True,
      )

      embed.add_field(
        name="📤 Output Tokens",
        value=f"**Total:** {total_output:,}\n**Average:** {avg_output:.1f} per message",
        inline=True,
      )

      embed.add_field(
        name="🔢 Combined",
        value=f"**Total:** {total_tokens:,}\n**Average:** {avg_total:.1f} per message",
        inline=True,
      )
      
      embed.add_field(
        name="💬 Messages",
        value=f"{total_messages:,}",
        inline=True,
      )
      
      embed.add_field(
        name="📅 Period",
        value=period.capitalize(),
        inline=True,
      )

      if total_input > 0:
        efficiency_ratio = total_output / total_input
        embed.add_field(
          name="⚡ Output/Input Ratio",
          value=f"{efficiency_ratio:.2f}",
          inline=True,
        )

      if stats:
        most_recent = max(stats, key=lambda x: x.get('timestamp', ''))
        if most_recent.get('timestamp'):
          # Parse timestamp and format it nicely
          try:
            from dateutil import parser
            timestamp_dt = parser.parse(most_recent['timestamp'])
            embed.add_field(
              name="🕒 Last Activity",
              value=f"<t:{int(timestamp_dt.timestamp())}:R>",
              inline=False,
            )
          except Exception as _e:
            pass
      
      embed.set_footer(
        text=f"Requested by {ctx.author.display_name}",
        icon_url=ctx.author.display_avatar.url
      )
        
      await ctx.send(embed=embed)
    except Exception as e:
      embed = discord.Embed(
        title="❌ Error",
        description=f"Failed to fetch token statistics: {str(e)}",
        color=0xFF0000,
      )
      await ctx.send(embed=embed)

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
