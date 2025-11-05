import discord
from discord.ext import commands
from utils.logger import logger
from services.db_service import DBService
from services.llm_service import LLMService
from utils.llm_utils import to_base64_data_uri
from services.async_caller_service import to_thread
from services.image_processing_service import ImageProcessingService
from utils.config import CONTEXT_LIMIT
from utils.cache import server_cache
from utils.message_utils import (
  CHANNEL_NAME,
  should_ignore,
  prepare_prompt,
  log_message,
  get_reply_context,
  send_error_message,
  send_message,
  send_response,
)
from .image_handler import ImageHandlerCog


class MessageHandlerCog(commands.Cog):
  def __init__(self, bot: commands.Bot) -> None:
    self.bot = bot
    self.channel_name = CHANNEL_NAME
    self.db_service = DBService()
    self.llm_service = LLMService()
    self.image_handler = ImageHandlerCog(bot)
    self.context_reset_message = "Context reset! Starting a new conversation. 👋"

  @commands.Cog.listener()
  async def on_message(self, message: discord.Message) -> None:
    if message.author.bot:
      return

    self.bot.loop.create_task(self.handle_message(message))

  async def handle_message(self, message: discord.Message) -> None:
    log_message(message)
    reason = should_ignore(message, self.bot)
    if reason is True:
      return

    try:
      if reason in ["reply", "mentioned_reply_other"]:
        reply_context = get_reply_context(message)
        if reply_context:
          message.content = f"This is a reply to: {reply_context}\n\n{message.content}"

      server_id = (
        f"DM_{message.author.id}" if message.guild is None else str(message.guild.id)
      )
      server_lore = await self._get_server_lore(server_id, message.guild)
      prompt = prepare_prompt(message)

      if "reset" in prompt.lower():
        await self._reset_chat(message, server_id)
        return

      user_content = [{"type": "text", "text": prompt}]
      image_attachments = [
        att
        for att in message.attachments
        if att.content_type and att.content_type.startswith("image")
      ]
      has_imgs = bool(image_attachments)

      if has_imgs and not message.author.bot:
        await self.image_handler._queue_images_for_processing(
          message=message,
          image_attachments=image_attachments,
          user_caption=prompt if prompt else None,
        )

      if has_imgs:
        await send_message(
          message, f"-# Analyzing {len(image_attachments)} images ... 💭"
        )
        for att in image_attachments:
          img_bytes = await att.read()
          data_uri = to_base64_data_uri(img_bytes)
          user_content.append({"type": "image_url", "image_url": {"url": data_uri}})

      img_note = f"\n\n[Attached {len(image_attachments)} image(s)]" if has_imgs else ""
      await self._add_user_context(message, prompt + img_note, server_id)

      server_context = await to_thread(self.db_service.get_chat_history, server_id)
      messages = (
        [
          {
            "role": "system",
            "content": server_lore,
          }
        ]
        + server_context
        + [{"role": "user", "content": user_content}]
      )

      async with message.channel.typing():
        result = await to_thread(
          self.llm_service.chat_completions,
          messages=messages,
          enable_tools=not has_imgs,
        )
        if len(result) == 3:
          bot_response, usage, generated_images = result
        else:
          bot_response, usage = result
          generated_images = []

      bot_response, sticker_ids = await self.image_handler._replace_stickers(
        bot_response
      )
      stickers = await self.image_handler._fetch_stickers(sticker_ids)
      self.db_service.store_token_usage(
        {
          "message_id": str(message.id),
          "guild_id": str(message.guild.id)
          if message.guild
          else f"DM_{message.author.id}",
          "author_id": str(message.author.id),
          "input_tokens": usage.prompt_tokens,
          "output_tokens": usage.total_tokens,
        }
      )
      await send_response(message, bot_response, stickers, usage, generated_images)
      await self._add_assistant_context(bot_response, server_id)
      await self._trim_context(server_id)

    except Exception as e:
      logger.error(f"Error in on_message: {e}", exc_info=True)
      await send_error_message(message)

  async def _get_server_lore(self, server_id: str, guild: discord.Guild) -> str:
    """
    Get server lore (system prompt) with caching.

    Checks cache first, falls back to database if not found.
    """
    # Try cache first
    cached_lore = server_cache.get_lore(server_id)
    if cached_lore is not None:
      return cached_lore

    # Cache miss - fetch from database
    prompt = await to_thread(self.db_service.fetch_prompt, server_id)
    lore = (
      prompt.get("system_prompt", "You are a helpful assistant")
      if prompt
      else "You are a helpful assistant"
    )

    # Update cache
    server_cache.set_lore(server_id, lore)
    return lore

  async def _reset_chat(self, message: discord.Message, server_id: str) -> None:
    prompt = message.content.strip()
    if "reset" in prompt and "reset chat" not in prompt:
      await message.channel.send('-# Say "reset chat"')
      return

    await to_thread(self.db_service.delete_chat_history, server_id)
    # Optionally invalidate cache if the system prompt might change
    # server_cache.invalidate_lore(server_id)
    await message.channel.send(self.context_reset_message)

  async def _add_user_context(
    self, message: discord.Message, prompt: str, server_id: str
  ) -> None:
    server_context = await to_thread(self.db_service.get_chat_history, server_id)
    content = (
      f"{message.author.name} (aka {message.author.display_name}) said: {prompt}"
    )
    server_context.append({"role": "user", "content": content})
    await to_thread(self.db_service.update_chat_history, server_id, server_context)

  async def _add_assistant_context(self, response: str, server_id: str) -> None:
    server_context = await to_thread(self.db_service.get_chat_history, server_id)
    server_context.append({"role": "assistant", "content": response})
    await to_thread(self.db_service.update_chat_history, server_id, server_context)

  async def _trim_context(self, server_id: str) -> None:
    server_context = await to_thread(self.db_service.get_chat_history, server_id)
    if len(server_context) > CONTEXT_LIMIT:
      server_context = server_context[-CONTEXT_LIMIT:]
      await to_thread(self.db_service.update_chat_history, server_id, server_context)


async def setup(bot: commands.Bot) -> None:
  await bot.add_cog(MessageHandlerCog(bot))
