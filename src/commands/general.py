import io
import random
import asyncio
import discord
import webrtcvad
import numpy as np
from datetime import datetime
from discord.ext import commands
from discord.ext import voice_recv
from collections import defaultdict
from scipy.signal import resample_poly
from utils.config import OPENROUTER_MODEL
from services.db_service import DBService
from services.asr_service import RemoteASR
from services.llm_service import LLMService
from discord.ext.voice_recv import AudioSink
from services.tenor_service import TenorService
from services.async_caller_service import to_thread
from services.weather_service import WeatherService
from utils.message_utils import get_channel_messages
from services.openrouter_service import OpenRouterService
from services.tool_calling_service import get_tavily_usage

WARMUP_BYTES_48K_STEREO = int(0.30 * 48000 * 2 * 2)  # ~300ms per speaker


class PcmFanoutSink(voice_recv.AudioSink):
  def __init__(self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue):
    super().__init__()
    self.loop = loop
    self.queue = queue

  def wants_opus(self) -> bool:
    return False  # we want decoded PCM

  def write(
    self, user: discord.abc.User | discord.Member | None, data: voice_recv.VoiceData
  ):
    # user can be None until SSRC is mapped; that's fine
    if not data.pcm:
      return
    pkt = getattr(data, "packet", None)  # raw RTP packet
    ts = getattr(pkt, "timestamp", None)
    self.loop.call_soon_threadsafe(
      self.queue.put_nowait,
      {"type": "pcm", "user": user, "pcm": data.pcm, "rtp_ts": ts},
    )

  @AudioSink.listener()
  def on_voice_member_speaking_state(
    self, member: discord.Member, ssrc: int, state: int
  ):
    if state == 0:  # state: 1 is start, 0 is stop
      self.loop.call_soon_threadsafe(
        self.queue.put_nowait, {"type": "flush", "user": member}
      )

  def cleanup(self):
    pass


class VoiceConsumer:
  """Consumes voice data, transcribes it, and generates LLM responses"""

  def __init__(
    self,
    queue: asyncio.Queue,
    asr_base_url: str,
    llm_service: LLMService,
    bot: commands.Bot,
    hmac_secret: str | None = None,
  ):
    self._conversation_history = defaultdict(list)
    self._transcript_buffer = defaultdict(list)  # user_id -> list of recent transcripts
    self._last_response_time = defaultdict(float)  # user_id -> timestamp of last LLM response
    self._buffer_max_size = 3  # Keep last 3 transcriptions
    self._response_cooldown = 5.0  # Minimum 5 seconds between LLM responses per user

    self.asr_client = RemoteASR(asr_base_url, hmac_secret=hmac_secret, timeout_s=10.0)
    self.llm_service = llm_service
    self.bot = bot
    self.queue = queue
    self.buffers = defaultdict(bytearray)  # uid -> PCM(48k stereo, s16le)
    self.vad = webrtcvad.Vad(2)
    self._fallback_ticks = defaultdict(
      int
    )  # uid -> accumulated bytes for coarse partials
    self._warmup = defaultdict(int)  # uid -> bytes left to drop
    self._conversation_history = defaultdict(list)  # user_id -> list of messages

  @staticmethod
  def stereo48k_to_mono16k(pcm48_stereo: bytes) -> bytes:
    """Convert 48kHz stereo PCM to 16kHz mono PCM"""
    s = np.frombuffer(pcm48_stereo, dtype=np.int16)
    if s.size == 0:
      return b""
    mono48 = s.reshape(-1, 2).mean(axis=1).astype(np.int16)
    mono16 = resample_poly(mono48, up=1, down=3).astype(np.int16)
    return mono16.tobytes()

  def vad_keep_voiced(self, mono16_bytes: bytes) -> bytes:
    """Filter out non-speech frames using VAD"""
    # 20ms @ 16k -> 640 bytes
    frames = [mono16_bytes[i : i + 640] for i in range(0, len(mono16_bytes), 640)]
    voiced = [f for f in frames if len(f) == 640 and self.vad.is_speech(f, 16000)]
    return b"".join(voiced)

  async def transcribe(self, mono16_bytes: bytes) -> str:
    """Send audio to remote ASR service for transcription"""
    if not mono16_bytes:
      return ""

    try:
      result = await self.asr_client.transcribe_pcm16(mono16_bytes, language="en")
      text = result.get("text", "").strip()

      # Log additional metadata from the response
      if text:
        duration = result.get("duration_s", 0)
        asr_ms = result.get("asr_ms", 0)
        model_info = result.get("model", {})
        print(
          f"[boo|ASR] Transcription took {asr_ms}ms for {duration:.2f}s audio using {model_info.get('name', 'unknown')} on {model_info.get('device', 'unknown')}"
        )

      return text
    except Exception as e:
      print(f"[boo|ASR] ERROR: Failed to transcribe audio: {e}")
      return ""

  async def generate_llm_response(
    self, user_text: str, user_id: int, user_name: str
  ) -> str:
    """Generate LLM response for the transcribed text"""
    try:
      # Build conversation context
      self._conversation_history[user_id].append({"role": "user", "content": user_text})

      # Keep only last 10 messages for context window management
      if len(self._conversation_history[user_id]) > 10:
        self._conversation_history[user_id] = self._conversation_history[user_id][-10:]

      # Create system message for voice chat context
      messages = [
        {
          "role": "system",
          "content": f"You are Boo, a friendly and helpful voice assistant in a Discord voice chat. Keep responses concise and conversational (1-3 sentences max). The user speaking is {user_name}.",
        }
      ]
      messages.extend(self._conversation_history[user_id])

      # Generate response using LLM service (synchronous, so use to_thread)
      response, usage = await to_thread(
        self.llm_service.chat_completions,
        messages=messages,
        temperature=0.7,
        max_tokens=150,
        enable_tools=False,  # Disable tools for faster voice responses
      )

      # Add assistant response to history
      self._conversation_history[user_id].append(
        {"role": "assistant", "content": response}
      )

      print(
        f"[boo|LLM] Generated response for {user_name} (tokens: {usage.total_tokens})"
      )
      return response

    except Exception as e:
      print(f"[boo|LLM] ERROR: Failed to generate response: {e}")
      return "Sorry, I couldn't process that right now."

  async def send_to_voice_text_channel(self, user: discord.Member, text: str):
    """Send LLM response to the voice channel's embedded text channel"""
    try:
      if not user.voice or not user.voice.channel:
        print(f"[boo|Discord] User {user.display_name} not in voice channel")
        return

      voice_channel = user.voice.channel

      # Check if it's a voice channel
      if not isinstance(voice_channel, discord.VoiceChannel):
        print(f"[boo|Discord] Not a voice channel")
        return

      # Check permissions
      permissions = voice_channel.permissions_for(user.guild.me)
      if not permissions.send_messages:
        print(f"[boo|Discord] No permission to send messages in this voice channel")
        return

      # Send to embedded text-in-voice channel
      await voice_channel.send(f"{user.mention} {text}")
      print(f"[boo|Discord] Sent response to '{voice_channel.name}' chat")

    except Exception as e:
      print(f"[boo|Discord] ERROR: {e}")

  async def run(self):
    """Main consumer loop processing audio chunks"""
    SECOND_48K_STEREO = 48000 * 2 * 2  # 192000 bytes ~= 1s

    while True:
      item = await self.queue.get()
      typ = item["type"]
      user = item["user"]
      uid = user.id if (user and hasattr(user, "id")) else 0

      if typ == "start":
        # (re)arm warm-up drop for this speaker
        self._warmup[uid] = WARMUP_BYTES_48K_STEREO

      elif typ == "pcm":
        b = item["pcm"]
        # drop warm-up bytes first
        drop = self._warmup.get(uid, 0)
        if drop:
          cut = min(drop, len(b))
          b = b[cut:]
          self._warmup[uid] = drop - cut
        if not b:
          continue  # still in warm-up—skip

        # buffer & maybe partial flush
        self.buffers[uid] += b
        self._fallback_ticks[uid] += len(b)
        if self._fallback_ticks[uid] >= 2 * SECOND_48K_STEREO:
          await self._flush_user(uid, user, partial=True)
          self._fallback_ticks[uid] = 0

      elif typ == "flush":
        await self._flush_user(uid, user, partial=False)
        self._fallback_ticks[uid] = 0

  async def _flush_user(self, uid: int, user, partial: bool = False) -> None:
    """Process buffered audio for a user, transcribe, and generate response"""
    buf = self.buffers[uid]
    if not buf:
      return

    data = bytes(buf)
    self.buffers[uid].clear()

    # Convert and filter audio
    mono16 = self.stereo48k_to_mono16k(data)
    voiced = self.vad_keep_voiced(mono16)
    chosen = voiced if len(voiced) >= int(16000 * 2 * 0.3) else mono16

    # Transcribe using remote ASR
    text = await self.transcribe(chosen)

    if text:
      name = getattr(user, "display_name", "unknown")
      tag = "(partial)" if partial else "(final)"
      print(f"[boo|ASR] {name} {tag}: {text}")

      # Only generate response for final (complete) utterances
      if isinstance(user, discord.Member):
        # Add to transcript buffer
        self._transcript_buffer[uid].append(text)

        # Keep only last N transcriptions
        if len(self._transcript_buffer[uid]) > self._buffer_max_size:
          self._transcript_buffer[uid] = self._transcript_buffer[uid][-self._buffer_max_size:]

        # Check if we should generate a response (cooldown-based)
        current_time = asyncio.get_event_loop().time()
        last_response = self._last_response_time.get(uid, 0)
        time_since_last = current_time - last_response

        # Generate response if:
        # 1. Enough time has passed since last response (cooldown)
        # 2. We have at least 2 transcriptions in buffer (some context)
        should_respond = (
          time_since_last >= self._response_cooldown and
          len(self._transcript_buffer[uid]) >= 2
        )

        if should_respond:
          # Combine buffered transcriptions into one context
          combined_text = " ".join(self._transcript_buffer[uid])

          # Generate LLM response
          response = await self.generate_llm_response(combined_text, uid, name)
          print(f"[boo|LLM] Response for {name}: {response}")

          # Send response to voice channel's text channel
          await self.send_to_voice_text_channel(user, response)

          # Update last response time and clear buffer
          self._last_response_time[uid] = current_time
          self._transcript_buffer[uid] = []

  async def close(self):
    """Clean up the ASR client"""
    await self.asr_client.close()


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

    if not hasattr(self.bot, "_voice_consumer_started"):
      self.bot._voice_consumer_started = True

      # Initialize the remote ASR consumer with LLM integration
      # Update the URL to match your Modal endpoint
      asr_url = "https://kashifulhaque--boo-whisper-api-fastapi-app.modal.run"
      consumer = VoiceConsumer(
        self.voice_queue,
        asr_base_url=asr_url,
        llm_service=self.llm_service,
        bot=self.bot,
        hmac_secret=None,  # Set your HMAC secret if configured on the server
      )

      # Store consumer reference for cleanup
      self.bot._voice_consumer = consumer
      self.bot.loop.create_task(consumer.run())

    self._listening_guild_ids.add(ctx.guild.id)
    await ctx.reply(
      "Joined **boo** and started capturing with remote ASR + LLM responses."
    )

  # ---- leave and stop capture ----
  @commands.hybrid_command(
    name="boo-leave", description="Leave 'boo' and stop capturing."
  )
  async def boo_leave(self, ctx: commands.Context):
    if ctx.guild and ctx.guild.voice_client:
      await ctx.guild.voice_client.disconnect(force=True)
      self._listening_guild_ids.discard(ctx.guild.id)

      # Clean up ASR client if it exists
      if hasattr(self.bot, "_voice_consumer"):
        try:
          await self.bot._voice_consumer.close()
        except Exception as e:
          print(f"[boo|ASR] Error closing ASR client: {e}")

      await ctx.reply("Left **boo**. Capture stopped.")
    else:
      await ctx.reply("I'm not in a voice channel.")

  # optional: lightweight consumer demonstrating how you'd read frames
  @commands.command(name="boo-debug-drain")
  async def boo_debug_drain(self, ctx: commands.Context, frames: int = 50):
    """Pull some frames from the queue just to prove it's flowing."""
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

  @commands.hybrid_command(
    name="get_model", description="Which is currently powering Boo?"
  )
  async def get_model(self, ctx: commands.Context) -> None:
    await ctx.send(f"**Powered by** [{OPENROUTER_MODEL}]()")

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


async def setup(bot: commands.Bot) -> None:
  """
  Setup function to add the GeneralCommands cog to the bot.

  Args:
      bot (commands.Bot): The Discord bot instance.
  """
  await bot.add_cog(GeneralCommands(bot))
