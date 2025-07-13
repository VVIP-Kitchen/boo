import discord
import datetime
from utils.logger import logger
from discord.ext import commands
from services.db_service import DBService
from services.workers_service import WorkersService
from utils.emoji_utils import replace_emojis, replace_stickers
from utils.config import CONTEXT_LIMIT, server_contexts, server_lore
from utils.message_utils import (
  CHANNEL_NAME,
  should_ignore,
  text_to_file,
  prepare_prompt,
  log_message
)

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
    self.custom_emojis = {}
    self.db_service = DBService()
    self.channel_name = CHANNEL_NAME
    self.workers_service = WorkersService()
    self.context_reset_message = "Context reset! Starting a new conversation. 👋"
    self.error_message = "I'm sorry, I encountered an error while processing your message. Please try again later."

  @commands.Cog.listener()
  async def on_ready(self) -> None:
    """
    Event listener for when the bot is ready and connected.
    """
    logger.info(f"{self.bot.user} has connected to Discord!")
    self._load_custom_emojis()

  ### Load emojis
  def _load_custom_emojis(self) -> None:
    try:
      self.custom_emojis = {
        emoji.name: emoji for guild in self.bot.guilds for emoji in guild.emojis
      }
      logger.info(f"Loaded {len(self.custom_emojis)} custom emojis.")
    except Exception as e:
      logger.error(f"Error loading custom emojis: {str(e)}")

  @commands.Cog.listener()
  async def on_message(self, message: discord.Message) -> None:
    """
    Event listener for incoming messages.

    Args:
      message (discord.Message): The incoming Discord message.
    """
    log_message(message)

    await self._guys_check(message)
    if should_ignore(message, self.bot):
      return

    try:
      prompt = prepare_prompt(message)
      server_id = f"DM_{message.author.id}" if message.guild is None else str(message.guild.id)
      self._load_server_lore(server_id, message.guild)

      if "reset" in prompt.lower():
        await self._reset_chat(message, server_id)
        return

      analysis = await self._handle_image_input(message, prompt, server_id)
      full_prompt = f"{prompt}\n\nImage analysis: {analysis}" if analysis else prompt
      await self._process_message(message, full_prompt, server_id)
    except Exception as e:
      logger.error(f"Error processing message: {str(e)}")
      await self._send_error_message(message)

  def _load_server_lore(self, server_id: str, guild: discord.Guild) -> None:
    ### Get system prompt
    lore = self.db_service.fetch_prompt(server_id)
    server_lore[server_id] = lore.get("system_prompt") if lore else "You are a helpful assistant"

    ### Get current date and time
    ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))  # Indian Standard Time
    now = datetime.datetime.now(ist)
    server_lore[server_id] += f"\n\nCurrent Time: {now.strftime('%H:%M:%S')}\nToday is: {now.strftime('%A')}"
    
    ### Get all emojis
    server_lore[server_id] += f"You have the following emojis at your disposal, use them: {' '.join(list(self.custom_emojis.keys()))}"

    ### Get online members
    if guild is not None and guild.chunked: # Ensure members are available
      online_members = [
        f"{member}, aka {member.display_name}" for member in guild.members
        if not member.bot and member.status != discord.Status.offline
      ]

      if online_members:
        member_list = ", ".join(online_members)
        server_lore[server_id] += f"\n\nCurrently online members: {member_list}"
      else:
        server_lore[server_id] += "\n\nNo members are currently online"

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
    if "guys" in msg:
      await message.channel.send("Hi! 'Guys' is a gendered pronoun. We recommend alternatives like 'folks', 'all', 'everyone', 'y\'all', 'team', 'crew' etc. We appreciate your help in building an inclusive workplace at VVIP.")
      return

  async def _handle_image_input(self, message: discord.Message, prompt: str, server_id: str) -> str:
    analysis = ""
    async with message.channel.typing():
      ### Return if there are no attachments or the file attachments are not image
      if len(message.attachments) == 0 or not message.attachments[0].content_type.startswith("image"):
        return analysis

      await self._send_message(message, '-# Thinking 🤔')
      for idx, attachment in enumerate(message.attachments):
        if attachment.content_type.startswith("image"):
          image_url = attachment.url
          image_prompt = f"Analyze this image {idx + 1}. Additional context: {prompt}" if prompt else "Caption this image {idx + 1}"
          result = self.workers_service.chat_completions(image=image_url, prompt=image_prompt)
          
          if len(analysis) == 0:
            analysis = result
          else:
            analysis += "\n" + result
          
          await self._send_message(message, f"-# Analyzed {idx + 1}/{len(message.attachments)} images!")
    return analysis

  async def _process_message(self, message: discord.Message, prompt: str, server_id: str) -> None:
    self._add_user_context(message, prompt, server_id)
    
    messages = [
      {
        "role": "system",
        "content": server_lore[server_id]
      }
    ] + server_contexts[server_id]

    async with message.channel.typing():
      bot_response = self.workers_service.chat_completions(messages=messages)
      bot_response_with_emojis = replace_emojis(bot_response, self.custom_emojis)
      bot_response_with_stickers, sticker_ids = replace_stickers(bot_response_with_emojis)
      sticker_list = await self._fetch_stickers(sticker_ids)

    await self._send_response(message, bot_response_with_stickers, sticker_list)
    self._add_assistant_context(bot_response, server_id)
    await self._check_context_limit(server_id)

  def _add_user_context(self, message: discord.Message, prompt: str, server_id: str) -> None:
    content = f"{message.author.name} (aka {message.author.display_name}) said: {prompt}"
    server_contexts[server_id].append({"role": "user", "content": content})

  async def _fetch_stickers(self, sticker_ids: list) -> list:
    sticker_list = []
    for sticker_id in sticker_ids:
      try:
        sticker_list.append(await self.bot.fetch_sticker(int(sticker_id)))
      except discord.errors.NotFound:
        logger.info(f"Sticker with ID {sticker_id} not found")
    return sticker_list if sticker_list else None

  async def _send_response(self, message: discord.Message, response: str, stickers: list) -> None:
    if len(response) > 1800:
      await message.channel.send(file=text_to_file(response))
    else:
      await message.channel.send(response, reference=message, stickers=stickers)
  
  async def _send_message(self, message: discord.Message, response: str, mention_author: bool = False) -> None:
    if len(response) > 1800:
      await message.channel.send(file=text_to_file(response), mention_author=mention_author)
    else:
      await message.channel.send(response, mention_author=mention_author)

  def _add_assistant_context(self, response: str, server_id: str) -> None:
    server_contexts[server_id].append({"role": "assistant", "content": response})

  async def _check_context_limit(self, server_id: str) -> None:
    if len(server_contexts[server_id]) > CONTEXT_LIMIT:
      excess = len(server_contexts[server_id]) - CONTEXT_LIMIT
      server_contexts[server_id] = server_contexts[server_id][excess:]

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
