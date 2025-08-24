import random
import discord
import datetime
from discord.ext import commands
from services.db_service import DBService
from services.llm_service import LLMService
from services.async_caller_service import to_thread
from utils.config import CONTEXT_LIMIT, server_contexts, server_lore
from utils.emoji_utils import replace_emojis, replace_stickers
from utils.logger import logger
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


class BotEvents(commands.Cog):
  def __init__(self, bot: commands.Bot) -> None:
    self.bot = bot
    self.custom_emojis = {}
    self.db_service = DBService()
    self.channel_name = CHANNEL_NAME
    self.llm_service = LLMService()
    self.context_reset_message = "Context reset! Starting a new conversation. 👋"

  @commands.Cog.listener()
  async def on_ready(self) -> None:
    logger.info(f"{self.bot.user} has connected to Discord!")
    self.custom_emojis = {
      emoji.name: emoji for guild in self.bot.guilds for emoji in guild.emojis
    }

  @commands.Cog.listener()
  async def on_message(self, message: discord.Message) -> None:
    log_message(message)

    await self._guys_check(message)
    reason = should_ignore(message, self.bot)
    if reason is True:
      return

    try:
      if reason in ["reply", "mentioned_reply_other"]:
        reply_context = get_reply_context(message)
        if reply_context:
          message.content = f"This is a reply to: {reply_context}\n\n{message.content}"

      prompt = prepare_prompt(message)
      server_id = (
        f"DM_{message.author.id}" if message.guild is None else str(message.guild.id)
      )
      self._load_server_lore(server_id, message.guild)

      if "reset" in prompt.lower():
        await self._reset_chat(message, server_id)
        return

      image_attachments = [
        att for att in message.attachments
        if att.content_type and att.content_type.startswith("image")
      ]
      has_imgs = bool(image_attachments)

      user_content = [{"type": "text", "text": prompt}]
      if has_imgs:
        await send_message(message, f"-# Analyzing {len(image_attachments)} images ... 💭")
        for att in image_attachments:
          img_bytes = await att.read()
          data_uri = self.llm_service._to_base64_data_uri(img_bytes)
          user_content.append({"type": "image_url", "image_url": {"url": data_uri}})

      img_note = f"\n\n[Attached {len(image_attachments)} image(s)]" if has_imgs else ""
      self._add_user_context(message, prompt + img_note, server_id)

      messages = (
        [{"role": "system", "content": server_lore.get(server_id, "No server lore found!")}]
        + server_contexts[server_id]
        + [{"role": "user", "content": user_content}]
      )

      async with message.channel.typing():
        bot_response, usage = await to_thread(
          self.llm_service.chat_completions,
          messages=messages,
          enable_tools=not has_imgs
        )
        bot_response = replace_emojis(bot_response, self.custom_emojis)
        bot_response, sticker_ids = replace_stickers(bot_response)
        stickers = await self._fetch_stickers(sticker_ids)

      self.db_service.store_token_usage({
        "message_id": str(message.id),
        "guild_id": str(message.guild.id) if message.guild else f"DM_{message.author.id}",
        "author_id": str(message.author.id),
        "input_tokens": usage.prompt_tokens,
        "output_tokens": usage.total_tokens,
      })

      await send_response(message, bot_response, stickers)
      self._add_assistant_context(bot_response, server_id)
      await self._trim_context(server_id)
    except Exception as e:
      logger.error(f"Error in on_message: {e}")
      await send_error_message(message)

  def _load_server_lore(self, server_id: str, guild: discord.Guild) -> None:
    prompt = self.db_service.fetch_prompt(server_id)
    lore = prompt.get("system_prompt") if prompt else "You are a helpful assistant"

    now = datetime.datetime.now(
      datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    )
    lore += f"\n\nCurrent Time: {now.strftime('%H:%M:%S')} | Day: {now.strftime('%A')}"
    lore += f"\nAvailable emojis: {' '.join(list(self.custom_emojis.keys()))}"

    if guild and guild.chunked:
      online = [
        f"{m}, aka {m.display_name}"
        for m in guild.members
        if not m.bot and m.status != discord.Status.offline
      ]
      lore += f"\n\nOnline members: {', '.join(online) if online else 'None'}"

    server_lore[server_id] = lore

  ### User has to say 'reset chat' in order to reset context
  async def _reset_chat(self, message: discord.Message, server_id: str) -> None:
    prompt = message.content.strip()
    if "reset" in prompt and "reset chat" not in prompt:
      await message.channel.send('-# Say "reset chat"')
      return
    server_contexts[server_id] = []
    await message.channel.send(self.context_reset_message)

  async def _guys_check(self, message: discord.Message) -> None:
    msg = message.content.strip().lower()
    if "guys" in msg and not message.author.bot and random.random() < 0.03:
      await message.channel.send(
        ">>> Hi! `'Guys'` is a gendered pronoun. We recommend alternatives like `'folks'`, `'all'`, `'everyone'`, `'y'all'`, `'team'`, `'crew'` etc. We appreciate your help in building an inclusive workplace at VVIP."
      )
      return

  async def _chat(self, message: discord.Message, prompt: str, server_id: str) -> None:
    self._add_user_context(message, prompt, server_id)

    messages = [
      {"role": "system", "content": server_lore.get(server_id, "No server lore found!")}
    ] + server_contexts[server_id]

    async with message.channel.typing():
      bot_response, usage = await to_thread(
        self.llm_service.chat_completions, messages=messages
      )
      bot_response = replace_emojis(bot_response, self.custom_emojis)
      bot_response, sticker_ids = replace_stickers(bot_response)
      stickers = await self._fetch_stickers(sticker_ids)

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

    await send_response(message, bot_response, stickers)
    self._add_assistant_context(bot_response, server_id)
    await self._trim_context(server_id)

  def _add_user_context(
    self, message: discord.Message, prompt: str, server_id: str
  ) -> None:
    content = (
      f"{message.author.name} (aka {message.author.display_name}) said: {prompt}"
    )
    server_contexts[server_id].append({"role": "user", "content": content})

  def _add_assistant_context(self, response: str, server_id: str) -> None:
    server_contexts[server_id].append({"role": "assistant", "content": response})

  async def _trim_context(self, server_id: str) -> None:
    if len(server_contexts[server_id]) > CONTEXT_LIMIT:
      server_contexts[server_id] = server_contexts[server_id][-CONTEXT_LIMIT:]

  async def _fetch_stickers(self, sticker_ids: list) -> list:
    stickers = []
    for sid in sticker_ids:
      try:
        stickers.append(await self.bot.fetch_sticker(int(sid)))
      except discord.errors.NotFound:
        logger.info(f"Sticker not found: {sid}")
    return stickers


async def setup(bot: commands.Bot) -> None:
  await bot.add_cog(BotEvents(bot))
