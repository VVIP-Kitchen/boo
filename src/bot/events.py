import pytz
import discord
import datetime
from pathlib import Path
from utils.logger import logger
from discord.ext import commands
from services.db_service import DBService
from services.github_service import GithubService
from services.workers_service import WorkersService
from utils.emoji_utils import replace_emojis, replace_stickers
from utils.config import CONTEXT_LIMIT, server_contexts, server_lore
from utils.message_utils import handle_user_mentions, is_direct_reply, text_to_file

ist = pytz.timezone("Asia/Kolkata")


class BotEvents(commands.Cog):
  """
  Cog for handling Discord bot events.
  """

  def __init__(self, bot: commands.Bot) -> None:
    """
    Initialize the BotEvents cog.

    Args:
      bot (commands.Bot): The Discord bot instance.
    """

    self.bot = bot
    self.channel_name = "chat"
    self.db_service = DBService()
    self.github_service = GithubService()
    self.workers_service = WorkersService()
    self.context_reset_message = "Context reset! Starting a new conversation. 👋"
    self.custom_emojis = {}
    self.error_message = "I'm sorry, I encountered an error while processing your message. Please try again later."

  @commands.Cog.listener()
  async def on_ready(self) -> None:
    """
    Event listener for when the bot is ready and connected.
    """

    logger.info(f"{self.bot.user} has connected to Discord!")
    self._load_custom_emojis()

  @commands.Cog.listener()
  async def on_message(self, message: discord.Message) -> None:
    """
    Event listener for incoming messages.

    Args:
      message (discord.Message): The incoming Discord message.
    """
    if self._should_ignore_message(message):
      return

    try:
      prompt = self._prepare_prompt(message)
      server_id = self._get_server_id(message)
      self._load_server_lore(server_id)

      if "reset chat" in prompt.lower():
        await self._reset_chat(message, server_id)
        return

      if message.guild is not None and not self._is_valid_channel(message):
        await self._send_channel_redirect(message)
        return

      analysis = await self._handle_image_input(message, prompt, server_id)
      full_prompt = f"{prompt}\n\nImage analysis: {analysis}" if analysis else prompt
      await self._process_message(message, full_prompt, server_id)
    except Exception as e:
      logger.error(f"Error processing message: {str(e)}")
      await self._send_error_message(message)

  def _load_custom_emojis(self) -> None:
    try:
      self.custom_emojis = {
        emoji.name: emoji for guild in self.bot.guilds for emoji in guild.emojis
      }
      logger.info(f"Loaded {len(self.custom_emojis)} custom emojis.")
    except Exception as e:
      logger.error(f"Error loading custom emojis: {str(e)}")

  def _is_bot_mentioned(self, message: discord.Message) -> bool:
    if message.guild is None:
      return True
    return is_direct_reply(message, self.bot) or self.bot.user in message.mentions

  def _should_ignore_message(self, message: discord.Message) -> bool:
    if message.author.bot:
      return True

    ### Always respond to DMs
    if message.guild is None:
      return False

    is_correct_channel = message.channel.name == self.channel_name
    is_mentioned = self.bot.user in message.mentions
    is_reply = is_direct_reply(message, self.bot)
    return not (is_correct_channel and (is_mentioned or is_reply))

  def _prepare_prompt(self, message: discord.Message) -> str:
    prompt = handle_user_mentions(message.content.strip(), message)
    for sticker in message.stickers:
      prompt += f"&{sticker.name};{sticker.id};{sticker.url}&"
    return prompt

  def _get_server_id(self, message: discord.Message) -> str:
    return f"DM_{message.author.id}" if message.guild is None else str(message.guild.id)

  def _load_server_lore(self, server_id: str) -> None:
    lore = self.db_service.fetch_prompt(server_id)
    server_lore[server_id] = (
      lore["system_prompt"] if lore is not None else "You are a helpful assistant"
    )

    ist = datetime.timezone(
      datetime.timedelta(hours=5, minutes=30)
    )  # Indian Standard Time
    now = datetime.datetime.now(ist)
    server_lore[server_id] += (
      f"\n\nCurrent Time: {now.strftime('%H:%M:%S')}\nToday is: {now.strftime('%A')}"
    )
    server_lore[server_id] += (
      f"You have the following emojis at your disposal, use them: {' '.join(list(self.custom_emojis.keys()))}"
    )

  async def _reset_chat(self, message: discord.Message, server_id: str) -> None:
    server_contexts[server_id] = []
    await message.channel.send(self.context_reset_message)

  def _is_valid_channel(self, message: discord.Message) -> bool:
    return message.channel.name == self.channel_name

  async def _send_channel_redirect(self, message: discord.Message) -> None:
    ctx = await self.bot.get_context(message)

    try:
      await ctx.send(
        "Ping me in <#1272840978277072918> to talk",
        ephemeral=True,
        reference=message,
      )
    except discord.errors.HTTPException:
      logger.info("Error occurred while sending message")

  async def _handle_image_input(
    self, message: discord.Message, prompt: str, server_id: str
  ) -> str:
    analysis = ""
    async with message.channel.typing():
      for attachment in message.attachments:
        if attachment.content_type.startswith("image"):
          image_url = attachment.url
          image_prompt = (
            f"Analyze this image. Additional context: {prompt}"
            if prompt
            else "Generate a caption for this image"
          )
          analysis = self.workers_service.analyze_image(image_url, image_prompt)
          break  ### Only analyze the first image
    return analysis

  async def _process_message(
    self, message: discord.Message, prompt: str, server_id: str
  ) -> None:
    self._add_user_context(message, prompt, server_id)
    messages = [
      {"role": "system", "content": server_lore[server_id]}
    ] + server_contexts[server_id]

    async with message.channel.typing():
      bot_response = self.workers_service.chat_completions(messages)
      bot_response_with_emojis = replace_emojis(bot_response, self.custom_emojis)
      bot_response_with_stickers, sticker_ids = replace_stickers(
        bot_response_with_emojis
      )
      sticker_list = await self._fetch_stickers(sticker_ids)

    await self._send_response(message, bot_response_with_stickers, sticker_list)
    self._add_assistant_context(bot_response, server_id)
    await self._check_context_limit(message, server_id)

  def _add_user_context(
    self, message: discord.Message, prompt: str, server_id: str
  ) -> None:
    content = (
      f"{message.author.name} (aka {message.author.display_name}) said: {prompt}"
    )
    server_contexts[server_id].append({"role": "user", "content": content})

  async def _fetch_stickers(self, sticker_ids: list) -> list:
    sticker_list = []
    for sticker_id in sticker_ids:
      try:
        sticker_list.append(await self.bot.fetch_sticker(int(sticker_id)))
      except discord.errors.NotFound:
        logger.info(f"Sticker with ID {sticker_id} not found")
    return sticker_list if sticker_list else None

  async def _send_response(
    self, message: discord.Message, response: str, stickers: list
  ) -> None:
    if len(response) > 1800:
      await message.channel.send(file=text_to_file(response))
    else:
      await message.channel.send(response, reference=message, stickers=stickers)

  def _add_assistant_context(self, response: str, server_id: str) -> None:
    server_contexts[server_id].append({"role": "assistant", "content": response})

  async def _check_context_limit(
    self, message: discord.Message, server_id: str
  ) -> None:
    if len(server_contexts[server_id]) >= CONTEXT_LIMIT:
      server_contexts[server_id] = []
      await message.channel.send(self.context_reset_message)

  async def _send_error_message(self, message: discord.Message) -> None:
    try:
      await message.channel.send(self.error_message, reference=message)
    except discord.errors.HTTPException:
      logger.error("Failed to send error message")


async def setup(bot: commands.Bot) -> None:
  """
  Setup function to add the BotEvents cog to the bot.

  Args:
    bot (commands.Bot): The Discord bot instance.
  """
  await bot.add_cog(BotEvents(bot))
