import io
import random
import asyncio
import discord

from datetime import datetime
from discord.ext import commands
from discord.ext import voice_recv
from discord.ext.voice_recv import AudioSink
from utils.config import OPENROUTER_MODEL
from services.db_service import DBService
from services.llm_service import LLMService
from services.tenor_service import TenorService
from services.async_caller_service import to_thread
from services.weather_service import WeatherService
from utils.message_utils import get_channel_messages
from services.voyageai_service import VoyageAiService
from services.openrouter_service import OpenRouterService
from services.tool_calling_service import get_tavily_usage
from services.meilisearch_service import MeilisearchService
from utils.logger import logger


class PcmFanoutSink(voice_recv.AudioSink):
  def __init__(self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue):
    super().__init__()
    self.loop = loop
    self.queue = queue
    self._frame_counter = 0

  def wants_opus(self) -> bool:
    return False  # we want decoded PCM

  def write(
    self, user: discord.abc.User | discord.Member | None, data: voice_recv.VoiceData
  ):
    # user can be None until SSRC is mapped; that's fine
    if not data.pcm:
      return

    self._frame_counter += 1
    if self._frame_counter % 50 == 0:  # ~1s of audio (20ms/frame => 50 frames)
      print(f"[voice] ~{self._frame_counter / 50:.1f}s captured")

    pkt = getattr(data, "packet", None)  # raw RTP packet
    ts = getattr(pkt, "timestamp", None)
    seq = getattr(pkt, "sequence", None)
    # hand off safely to the asyncio loop
    self.loop.call_soon_threadsafe(self.queue.put_nowait, (user, data.pcm, ts, seq))

  @AudioSink.listener()
  def on_voice_member_speaking_state(
    self, member: discord.Member, ssrc: int, state: int
  ):
    print(
      f"[voice] speaking_state: {member} ({ssrc}) -> {state}"
    )  # state '1' is speaking

  def cleanup(self):
    pass


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
    self.voyage_service = VoyageAiService()
    self.meili_service = MeilisearchService()
    self.openrouter_service = OpenRouterService()

    # a simple queue you can consume elsewhere (e.g., a task that streams to your voice LLM)
    self.voice_queue: asyncio.Queue[
      tuple[discord.Member | None, bytes, int | None, int | None]
    ] = asyncio.Queue()
    self._listening_guild_ids: set[int] = set()

  def _on_pcm(self, user, pcm_bytes: bytes, ts: float):
    try:
      self.voice_queue.put_nowait((user, pcm_bytes, ts))
    except asyncio.QueueFull:
      pass

  @commands.hybrid_command(
    name="boo-join",
    description="Join the voice channel named 'boo' and start capturing.",
  )
  async def boo_join(self, ctx: commands.Context):
    await ctx.defer(ephemeral=True)

    if not ctx.guild:
      return await ctx.reply("Use this in a server.")

    # find a voice or stage channel named 'boo'
    def _is_boo(c: discord.abc.GuildChannel):
      return (
        isinstance(c, (discord.VoiceChannel, discord.StageChannel))
        and c.name.lower() == "boo"
      )

    channel = discord.utils.find(_is_boo, ctx.guild.channels)
    if channel is None:
      return await ctx.reply(
        "Couldn't find a voice/stage channel named **boo** in this server."
      )

    # already connected?
    if ctx.guild.voice_client and ctx.guild.voice_client.is_connected():
      if ctx.guild.voice_client.channel.id == channel.id:
        return await ctx.reply("I'm already in **boo** and listening.")
      # move if in another VC
      await ctx.guild.voice_client.move_to(channel)
    else:
      # IMPORTANT: use the receive-capable client
      vc = await channel.connect(cls=voice_recv.VoiceRecvClient)  # <- key line
      # start listening with our sink
      sink = PcmFanoutSink(self.bot.loop, self.voice_queue)
      vc.listen(sink)  # start receiving into sink

    self._listening_guild_ids.add(ctx.guild.id)
    await ctx.reply("Joined **boo** and started capturing.")

  # ---- leave and stop capture ----
  @commands.hybrid_command(
    name="boo-leave", description="Leave 'boo' and stop capturing."
  )
  async def boo_leave(self, ctx: commands.Context):
    if ctx.guild and ctx.guild.voice_client:
      await ctx.guild.voice_client.disconnect(force=True)
      self._listening_guild_ids.discard(ctx.guild.id)
      await ctx.reply("Left **boo**. Capture stopped.")
    else:
      await ctx.reply("I'm not in a voice channel.")

  # optional: lightweight consumer demonstrating how you'd read frames
  @commands.command(name="boo-debug-drain")
  async def boo_debug_drain(self, ctx: commands.Context, frames: int = 50):
    """Pull some frames from the queue just to prove it’s flowing."""
    grabbed = 0
    while grabbed < frames:
      try:
        user, pcm, ts = await asyncio.wait_for(self.voice_queue.get(), timeout=5)
        grabbed += 1
      except asyncio.TimeoutError:
        break
    await ctx.reply(f"Drained {grabbed} frames from the capture queue.")

  @commands.hybrid_command(name="bonk", description="Bonks a user")
  async def bonk(self, ctx: commands.Context, member: discord.Member) -> None:
    async with ctx.typing():
      bonk_gif = random.choice(self.tenor_service.search())
      await ctx.send(
        content=f"<@{ctx.author.id}> has bonked <@{member.id}> {bonk_gif['url']}"
      )

  @commands.cooldown(10, 60)
  @commands.hybrid_command(name="skibidi", description="You are my skibidi")
  async def skibidi(self, ctx: commands.Context) -> None:
    """
    Post O Skibidi RE

    Args:
      ctx (commands.Context): The invocation context.
    """
    await ctx.send("SKIBIDI 😍\nhttps://youtu.be/smQ57m7mjSU")

  @commands.hybrid_command(
    name="get_model", description="Which is currently powering Boo?"
  )
  async def get_model(self, ctx: commands.Context) -> None:
    await ctx.send(
      f"**Powered by** [{OPENROUTER_MODEL}](<https://openrouter.ai/{OPENROUTER_MODEL}>)"
    )

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

      # Create simple embed
      embed = discord.Embed(
        title="Tavily API Usage", color=0x2B2D31, timestamp=discord.utils.utcnow()
      )

      # Key usage
      key_data = result.get("key", {})
      key_usage = key_data.get("usage", 0)
      embed.add_field(name="Search queries", value=f"{key_usage} searches", inline=True)

      # Account info
      account = result.get("account", {})
      plan = account.get("current_plan", "Unknown")
      embed.add_field(name="Plan", value=f"{plan}", inline=True)

      plan_usage = account.get("plan_usage", 0)
      plan_limit = account.get("plan_limit", "N/A")
      embed.add_field(
        name="Total usage", value=f"{plan_usage} / {plan_limit}", inline=True
      )

      # Send response
      await ctx.send(embed=embed)

    except Exception as e:
      error_embed = discord.Embed(
        title="Error",
        description=f"Failed to get Tavily stats: {str(e)}",
        color=0xFF0000,
      )
      await ctx.send(embed=error_embed)

  @commands.hybrid_command(
    name="token_stats",
    description="Show LLM token usage stats for this server (and/or specific user)",
  )
  async def get_token_stats(
    self, ctx: commands.Context, user: discord.Member = None, period: str = "daily"
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
        guild_id=str(guild.id), author_id=str(target_user.id), period=period.lower()
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

      total_input = sum(usage.get("input_tokens", 0) for usage in stats)
      total_output = sum(usage.get("output_tokens", 0) for usage in stats)
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
        most_recent = max(stats, key=lambda x: x.get("timestamp", ""))
        if most_recent.get("timestamp"):
          # Parse timestamp and format it nicely
          try:
            from dateutil import parser

            timestamp_dt = parser.parse(most_recent["timestamp"])
            embed.add_field(
              name="🕒 Last Activity",
              value=f"<t:{int(timestamp_dt.timestamp())}:R>",
              inline=False,
            )
          except Exception as _e:
            pass

      embed.set_footer(
        text=f"Requested by {ctx.author.display_name}",
        icon_url=ctx.author.display_avatar.url,
      )

      await ctx.send(embed=embed)
    except Exception as e:
      embed = discord.Embed(
        title="❌ Error",
        description=f"Failed to fetch token statistics: {str(e)}",
        color=0xFF0000,
      )
      await ctx.send(embed=embed)

  @commands.hybrid_command(
    name="summary", description="Generate a summary of recent messages in this channel"
  )
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
      summary, _usage = await to_thread(
        self.llm_service.chat_completions,
        prompt=summary_prompt,
        temperature=0.35,
        max_tokens=512,
      )

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

  @commands.hybrid_command(
    name="get_prompt", description="Get the current system prompt for this server"
  )
  async def get_system_prompt(self, ctx):
    """Fetch the current system prompt for this server"""
    await ctx.defer()  # Defer the response to prevent timeout

    guild = ctx.guild
    if not guild:
      return await ctx.send("❌ This command can only be used in a server, no DMs")

    try:
      result = self.db_service.fetch_prompt(str(guild.id))
      system_prompt = result.get("system_prompt") if result else "No system prompt set"
      file_content = system_prompt.encode("utf-8")
      filename = f"system_prompt_{guild.id}.md"
      file = discord.File(fp=io.BytesIO(file_content), filename=filename)

      await ctx.send(
        content=f"📄 Here's the system prompt for **{guild.name}**:", file=file
      )
    except Exception as e:
      await ctx.send(f"❌ Failed to fetch system prompt: {e}")

  @commands.hybrid_command(
    name="update_prompt",
    description="Update the system prompt for this server from a file",
  )
  async def update_system_prompt(self, ctx, file: discord.Attachment):
    """
    Update the system prompt for this guild from an uploaded file

    Args:
      file: A text file containing the new system prompt
    """
    await ctx.defer()
    guild = ctx.guild
    if not guild:
      return await ctx.send("❌ This command can only be used in a server, no DMs")

    # --- permission gate: manage_guild OR role "boo manager"
    def has_boo_manager_role(member: discord.Member) -> bool:
      # case-insensitive match on role name; consider using role ID for robustness
      return any(r.name.lower() == "boo manager" for r in member.roles)

    is_manager = ctx.author.guild_permissions.manage_guild or has_boo_manager_role(
      ctx.author
    )
    if not is_manager:
      return await ctx.send(
        "❌ You need **Manage Server** or the **boo manager** role to update the system prompt."
      )
    # --- end gate

    try:
      if not file.filename.endswith((".txt", ".md")):
        return await ctx.send("❌ Please upload a text file (.txt or .md)")

      if file.size > 1024 * 1024:
        return await ctx.send("❌ File size must be less than 1MB")

      file_content = await file.read()
      try:
        system_prompt = file_content.decode("utf-8").strip()
      except UnicodeDecodeError:
        return await ctx.send("❌ File must be valid UTF-8 text")

      if not system_prompt:
        return await ctx.send("❌ File appears to be empty")

      if len(system_prompt) > 50000:
        return await ctx.send("❌ System prompt is too long (max 50,000 characters)")

      success = self.db_service.update_prompt(str(guild.id), system_prompt)

      if success:
        await ctx.send(f"✅ System prompt updated successfully for **{guild.name}**!")
      else:
        await ctx.send("❌ Failed to update system prompt. Please try again later.")

    except Exception as e:
      await ctx.send(f"❌ An error occurred while processing the file: {str(e)}")

  @commands.hybrid_command(
    name="add_prompt", description="Add a system prompt for this server from a file"
  )
  async def add_system_prompt(self, ctx, file: discord.Attachment):
    """
    Add a system prompt for this guild from an uploaded file

    Args:
      file: A text file containing the new system prompt
    """
    await ctx.defer()
    guild = ctx.guild
    if not guild:
      return await ctx.send("❌ This command can only be used in a server, no DMs")

    # --- permission gate: manage_guild OR role "boo manager"
    def has_boo_manager_role(member: discord.Member) -> bool:
      # case-insensitive name match; replace with role ID check for more robustness
      return any(r.name.lower() == "boo manager" for r in member.roles)

    is_manager = ctx.author.guild_permissions.manage_guild or has_boo_manager_role(
      ctx.author
    )
    if not is_manager:
      return await ctx.send(
        "❌ You need **Manage Server** or the **boo manager** role to add a system prompt."
      )
    # --- end gate

    try:
      if not file.filename.endswith((".txt", ".md")):
        return await ctx.send("❌ Please upload a text file (.txt or .md)")

      if file.size > 1024 * 1024:  # 1MB limit
        return await ctx.send("❌ File size must be less than 1MB")

      file_content = await file.read()
      try:
        system_prompt = file_content.decode("utf-8").strip()
      except UnicodeDecodeError:
        return await ctx.send("❌ File must be valid UTF-8 text")

      if not system_prompt:
        return await ctx.send("❌ File appears to be empty")

      if len(system_prompt) > 50000:
        return await ctx.send("❌ System prompt is too long (max 50,000 characters)")

      success = self.db_service.add_prompt(str(guild.id), system_prompt)

      if success:
        await ctx.send(f"✅ System prompt added successfully for **{guild.name}**!")
      else:
        await ctx.send(
          "❌ Failed to add system prompt, might not exist. Try '/add_prompt'"
        )

    except Exception as e:
      await ctx.send(f"❌ An error occurred while processing the file: {str(e)}")

  ### Search commands
  @commands.hybrid_command(
    name="search_by_text", description="Search for images by text query"
  )
  async def search_by_text(self, ctx: commands.Context, query: str, limit: int = 5):
    """
    Search for images using a text query.

    Args:
        query: Text to search for
        limit: Maximum number of results (default: 5, max: 10)
    """
    await ctx.defer()

    if not ctx.guild:
      return await ctx.send("❌ This command can only be used in a server")

    try:
      # Validate limit
      limit = max(1, min(limit, 10))

      # Generate embedding for the query
      query_embedding = await to_thread(
        self.voyage_service.generate_text_embeddings, query
      )

      # Search in Meilisearch
      results = await to_thread(
        self.meili_service.search_by_text,
        query=query,
        query_embedding=query_embedding,
        server_id=str(ctx.guild.id),
        limit=limit,
        semantic_ratio=0.55,  # Balance between semantic and keyword search
      )

      hits = results.get("hits", [])

      if not hits:
        embed = discord.Embed(
          title="🔍 No Results Found",
          description=f"No images found matching: **{query}**",
          color=0xFF6B6B,
        )
        return await ctx.send(embed=embed)

      # Create embed with results
      embed = discord.Embed(
        title=f"🔍 Image Search Results for: `{query}`",
        description=f"Found {len(hits)} result(s) in this server",
        color=0x7615D1,
        timestamp=datetime.now(),
      )

      for idx, hit in enumerate(hits, 1):
        score = hit.get("_rankingScore", 0)
        vlm_caption = hit.get("vlm_caption", "No caption")
        user_caption = hit.get("user_caption", "")
        author_name = hit.get("author_name", "Unknown")
        message_url = hit.get("message_url", "")

        # Truncate captions if too long
        vlm_caption_short = (
          (vlm_caption[:50] + "...") if len(vlm_caption) > 50 else vlm_caption
        )

        field_value = f"**Description:** `{vlm_caption_short}`\n"
        if user_caption:
          field_value += f"**User Caption:** `{user_caption[:50]}`\n"
        field_value += f"**Posted by:** {author_name}\n"
        field_value += f"-# Score: {score:.3f}\n"
        if message_url:
          field_value += f"[Jump to message]({message_url})"

        embed.add_field(name=f"#{idx}", value=field_value, inline=False)

      embed.set_footer(text=f"Requested by {ctx.author.display_name}")
      await ctx.send(embed=embed)

    except Exception as e:
      embed = discord.Embed(
        title="❌ Search Error",
        description=f"An error occurred while searching: {str(e)}",
        color=0xFF0000,
      )
      await ctx.send(embed=embed)

  @commands.hybrid_command(
    name="search_by_image",
    description="Search for similar images using an uploaded image",
  )
  async def search_by_image(self, ctx: commands.Context, limit: int = 5):
    """
    Search for visually similar images.
    Attach an image when using this command.

    Args:
        limit: Maximum number of results (default: 5, max: 10)
    """
    await ctx.defer()

    if not ctx.guild:
      return await ctx.send("❌ This command can only be used in a server")

    # Check for image attachment
    if ctx.message.attachments:
      attachments = ctx.message.attachments
    elif ctx.interaction and ctx.interaction.message.attachments:
      attachments = ctx.interaction.message.attachments
    else:
      embed = discord.Embed(
        title="❌ No Image Provided",
        description="Please attach an image when using this command!",
        color=0xFF6B6B,
      )
      return await ctx.send(embed=embed)

    # Get the first image attachment
    image_attachments = [
      att
      for att in attachments
      if att.content_type and att.content_type.startswith("image")
    ]

    if not image_attachments:
      embed = discord.Embed(
        title="❌ No Image Found",
        description="Please attach an image file (PNG, JPG, etc.)",
        color=0xFF6B6B,
      )
      return await ctx.send(embed=embed)

    try:
      # Read image bytes
      image_attachment = image_attachments[0]
      image_bytes = await image_attachment.read()

      # Validate limit
      limit = max(1, min(limit, 10))

      # Generate embedding for the image
      image_embedding = await to_thread(
        self.voyage_service.generate_image_embeddings, image_bytes
      )

      # Search in Meilisearch
      results = await to_thread(
        self.meili_service.search_by_image,
        image_embedding=image_embedding,
        server_id=str(ctx.guild.id),
        limit=limit,
        semantic_ratio=0.95,  # High semantic ratio for visual similarity
      )

      hits = results.get("hits", [])

      if not hits:
        embed = discord.Embed(
          title="🔍 No Similar Images Found",
          description="No visually similar images found in this server",
          color=0xFF6B6B,
        )
        return await ctx.send(embed=embed)

      # Create embed with results
      embed = discord.Embed(
        title="🖼️ Visually Similar Images",
        description=f"Found {len(hits)} similar image(s) in this server",
        color=0x7615D1,
        timestamp=datetime.now(),
      )

      for idx, hit in enumerate(hits, 1):
        score = hit.get("_rankingScore", 0)
        vlm_caption = hit.get("vlm_caption", "No caption")
        author_name = hit.get("author_name", "Unknown")
        message_url = hit.get("message_url", "")
        attachment_url = hit.get("attachment_url", "")

        # Truncate caption
        vlm_caption_short = (
          (vlm_caption[:100] + "...") if len(vlm_caption) > 100 else vlm_caption
        )

        field_value = f"**Similarity:** {score:.3f}\n"
        field_value += f"**Description:** {vlm_caption_short}\n"
        field_value += f"**Posted by:** {author_name}\n"
        if message_url:
          field_value += f"[Jump to message]({message_url})"

        embed.add_field(name=f"#{idx}", value=field_value, inline=False)

      # Set thumbnail to first result if available
      if hits and hits[0].get("attachment_url"):
        embed.set_thumbnail(url=hits[0]["attachment_url"])

      embed.set_footer(text=f"Requested by {ctx.author.display_name}")
      await ctx.send(embed=embed)

    except Exception as e:
      embed = discord.Embed(
        title="❌ Search Error",
        description=f"An error occurred while searching: {str(e)}",
        color=0xFF0000,
      )
      await ctx.send(embed=embed)

  @commands.hybrid_command(
    name="image_stats", description="Show statistics about stored images"
  )
  async def image_stats(self, ctx: commands.Context):
    """Show statistics about the image database."""
    await ctx.defer()

    if not ctx.guild:
      return await ctx.send("❌ This command can only be used in a server")

    try:
      stats = await to_thread(self.meili_service.get_stats)

      embed = discord.Embed(
        title="📊 Image Database Statistics",
        color=0x7615D1,
        timestamp=datetime.now(),
      )

      # Check if there's an error
      if "error" in stats:
        embed.add_field(name="⚠️ Error", value=f"``````", inline=False)

      embed.add_field(
        name="📸 Total Images",
        value=f"{stats.get('total_documents', 0):,}",
        inline=True,
      )

      embed.add_field(
        name="🔄 Indexing Status",
        value="In Progress" if stats.get("is_indexing") else "Up to Date",
        inline=True,
      )

      # Show method used if available
      if "method" in stats:
        embed.add_field(name="📋 Method", value=stats["method"], inline=True)

      embed.set_footer(text=f"Server: {ctx.guild.name}")
      await ctx.send(embed=embed)

    except Exception as e:
      logger.error(f"Error in image_stats command: {e}")
      embed = discord.Embed(
        title="❌ Error",
        description=f"Failed to get statistics: {str(e)}",
        color=0xFF0000,
      )
      await ctx.send(embed=embed)

  @commands.hybrid_command(
    name="queue_status", description="Show background image processing queue status"
  )
  @commands.has_permissions(administrator=True)
  async def queue_status(self, ctx: commands.Context):
    """Show status of the background task queue."""
    try:
      # Initialize task queue service
      from services.task_queue_service import TaskQueueService

      task_queue = TaskQueueService()

      info = task_queue.get_queue_info()

      if "error" in info:
        return await ctx.send(f"❌ Queue error: {info['error']}")

      embed = discord.Embed(
        title="📊 Task Queue Status",
        color=0x7615D1,
        timestamp=datetime.now(),
      )

      embed.add_field(name="⏳ Pending", value=str(info.get("count", 0)), inline=True)
      embed.add_field(
        name="▶️ Running", value=str(info.get("started_count", 0)), inline=True
      )
      embed.add_field(
        name="✅ Completed", value=str(info.get("finished_count", 0)), inline=True
      )
      embed.add_field(
        name="❌ Failed", value=str(info.get("failed_count", 0)), inline=True
      )

      await ctx.send(embed=embed)

    except Exception as e:
      await ctx.send(f"❌ Error: {str(e)}")

  @commands.command()
  async def research(self, ctx: commands.Context, *, query: str) -> None:
    """
    Perform research on a given topic.
    """
    await ctx.send(f"🔬 Researching: {query}...")
    try:
      # Check for attachments
      if ctx.message.attachments:
        attachment_url = ctx.message.attachments[0].url
        query += f"\n\nFile: {attachment_url}"

      response, _, _ = await to_thread(
        self.llm_service.chat_completions, prompt=query, enable_tools=True
      )
      await ctx.send(response)
    except Exception as e:
      logger.error(f"Error in research command: {e}")
      await ctx.send("An error occurred while researching.")


async def setup(bot: commands.Bot) -> None:
  """
  Setup function to add the GeneralCommands cog to the bot.

  Args:
    bot (commands.Bot): The Discord bot instance.
  """

  await bot.add_cog(GeneralCommands(bot))
