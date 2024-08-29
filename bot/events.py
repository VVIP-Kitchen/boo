import re
import pytz
import discord
import datetime
from utils.logger import logger
from discord.ext import commands
from services.llm_service import LLMService
from utils.emoji_utils import replace_emojis, replace_stickers
from utils.config import CONTEXT_LIMIT, server_contexts, server_lore, PREFIX
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
    self.llm_service = LLMService()
    self.context_reset_message = "Context reset! Starting a new conversation. 👋"

  @commands.Cog.listener()
  async def on_ready(self) -> None:
    """
    Event listener for when the bot is ready and connected.
    """
    logger.info(f"{self.bot.user} has connected to Discord!")
    self.custom_emojis = {
      emoji.name: emoji for guild in self.bot.guilds for emoji in guild.emojis
    }
    logger.info(f"Loaded {len(self.custom_emojis)} custom emojis.")

  @commands.Cog.listener()
  async def on_message(self, message: discord.Message) -> None:
    """
    Event listener for incoming messages.

    Args:
      message (discord.Message): The incoming Discord message.
    """

    ### Don't process the message if it's authored by a bot or is empty
    prompt = message.content.strip()

    if message.author.bot or len(prompt) == 0:
      if message.guild is not None:
        is_reply = is_direct_reply(message, self.bot)
        is_mention = self.bot.user in message.mentions

        if not (is_reply or is_mention):
          return

        if message.channel.name != self.channel_name:
          ctx = await self.bot.get_context(message)
          await ctx.send(
            "Ping me in <#1272840978277072918> to talk",
            ephemeral=True,
            reference=message,
          )
          return
      if not message.author.bot and message.stickers:
        try:
          await message.channel.send(stickers=message.stickers, reference=message)
        except:
          logger.info(f"Error occured while sending message")
          return
      return

    for sticker in message.stickers:
      prompt = prompt + f"&{sticker.name};{sticker.id};{sticker.url}&"

    ### Either get the server ID or get the author ID (in case of a DM)
    server_id = f"DM_{message.author.id}" if message.guild is None else message.guild.id

    server_lore[server_id] = ""
    server_lore_file = f"data/prompts/{server_id}.txt"
    try:
      with open(server_lore_file, "r") as file:
        server_lore[server_id] = file.read()
    except:
      with open("data/prompts/default_prompt.txt", "r") as file:
        server_lore[server_id] = file.read()

    now = datetime.datetime.now(ist)
    current_time = now.strftime("%H:%M:%S")
    current_day = now.strftime("%A")
    server_lore[server_id] += (
      f"\n\nCurrent Time: {current_time}\nToday is: {current_day}"
    )

    if "reset chat" in prompt.lower():
      server_contexts[server_id] = []
      await message.channel.send(self.context_reset_message)
      return

    if message.guild is not None:
      is_reply = is_direct_reply(message, self.bot)
      is_mention = self.bot.user in message.mentions

      if not (is_reply or is_mention):
        return

      if message.channel.name != self.channel_name:
        ctx = await self.bot.get_context(message)
        try:
          await ctx.send(
            "Ping me in <#1272840978277072918> to talk",
            ephemeral=True,
            reference=message,
          )
        except:
          logger.info(f"Error occured while sending message")
          return
        return

    ### Build the context
    prompt = handle_user_mentions(prompt, message)
    server_contexts[server_id].append(
      {
        "role": "user",
        "content": f"{message.author.name} (aka {message.author.display_name}) said: {prompt}",
      }
    )
    messages = [
      {"role": "system", "content": server_lore[server_id]}
    ] + server_contexts[server_id]

    ### While the typing ... indicator is showing up, process the user input and generate a response
    async with message.channel.typing():
      bot_response = self.llm_service.call_model(messages)
      bot_response_with_emojis = replace_emojis(bot_response, self.custom_emojis)
      bot_response_with_stickers, test_list = replace_stickers(bot_response_with_emojis)
      sticker_list = []
      for sticker in test_list:
        try:
          sticker_list.append(await self.bot.fetch_sticker(int(sticker)))
        except:
          logger.info(f"Error occured while fetching sticker")
          return
      if not sticker_list:
        sticker_list = None
      server_contexts[server_id].append({"role": "assistant", "content": bot_response})
    if len(bot_response_with_stickers) > 1800:
      await message.channel.send(file=text_to_file(bot_response_with_stickers))
    else:
      if message is not None:
        await message.channel.send(
          bot_response_with_stickers, reference=message, stickers=sticker_list
        )
      else:
        await message.channel.send(bot_response_with_stickers, stickers=sticker_list)

    ### Reset the context if the conversation gets too long
    if len(server_contexts[server_id]) >= CONTEXT_LIMIT:
      server_contexts[server_id] = []
      await message.channel.send(self.context_reset_message)

  #@commands.Cog.listener()
  async def on_raw_message_delete(self, payload):
    # PREPROCESSING TO CHECK IF THE DELETED MESSAGE IS SAME AS THE ONE SENT BY NQN
    test_id = payload.channel_id
    test_content = payload.cached_message.content
    channel = self.bot.get_channel(test_id)
    ctx = await self.bot.get_context(payload.cached_message)

    def match_object(matchobj):
      return re.search(r"\:.*\:", matchobj.group(0)).group(0)

    messages = [
      message async for message in channel.history(limit=5) if message.author.bot
    ]
    message = messages[-1]
    message.content = re.sub(
      r"<[A-Za-z_0-9]*\:[A-Za-z_0-9]*\:[0-9]*>", match_object, message.content
    )
    if not message.content == test_content:
      return

    pmsg = payload.cached_message
    prompt = payload.cached_message.content.strip()

    if pmsg.author.bot or len(prompt) == 0:
      if message.guild is not None:
        is_reply = is_direct_reply(message, self.bot)
        is_mention = self.bot.user in message.mentions

        if not (is_reply or is_mention):
          return

        if message.channel.name != self.channel_name:
          ctx = await self.bot.get_context(message)
          await ctx.send(
            "Ping me in <#1272840978277072918> to talk",
            ephemeral=True,
            reference=message,
          )
          return
      if not message.author.bot and message.stickers:
        try:
          await message.channel.send(stickers=message.stickers, reference=message)
        except:
          logger.info(f"Error occured while sending message")
      return

    for sticker in message.stickers:
      prompt = prompt + f"&{sticker.name};{sticker.id};{sticker.url}&"

    if message.content.startswith(PREFIX):
      ctx = await bot.get_context(pmsg)
      for check_command in self.bot.commands:
        test_text = ctx.message.content.split()
        if check_command.name in test_text[0]:
          ctx.command = check_command
          await self.bot.invoke(ctx)
      return

    ### Either get the server ID or get the author ID (in case of a DM)
    server_id = f"DM_{message.author.id}" if message.guild is None else message.guild.id

    server_lore[server_id] = ""
    server_lore_file = f"data/prompts/{server_id}.txt"
    try:
      with open(server_lore_file, "r") as file:
        server_lore[server_id] = file.read()
    except:
      with open("data/prompts/default_prompt.txt", "r") as file:
        server_lore[server_id] = file.read()

    now = datetime.datetime.now(ist)
    current_time = now.strftime("%H:%M:%S")
    current_day = now.strftime("%A")
    server_lore[server_id] += (
      f"\n\nCurrent Time: {current_time}\nToday is: {current_day}"
    )

    if "reset chat" in prompt.lower():
      server_contexts[server_id] = []
      await message.channel.send(self.context_reset_message)
      return

    if message.guild is not None:
      is_reply = is_direct_reply(message, self.bot)
      is_mention = self.bot.user in message.mentions

      if not (is_reply or is_mention):
        return

      if message.channel.name != self.channel_name:
        ctx = await self.bot.get_context(message)
        try:
          await ctx.send(
            "Ping me in <#1272840978277072918> to talk",
            ephemeral=True,
            reference=message,
          )
        except:
          logger.info(f"Error occured while sending message")
          return
        return

    ### Build the context
    prompt = handle_user_mentions(prompt, message)
    server_contexts[server_id].append(
      {
        "role": "user",
        "content": f"{message.author.name} (aka {message.author.display_name}) said: {prompt}",
      }
    )
    messages = [
      {"role": "system", "content": server_lore[server_id]}
    ] + server_contexts[server_id]

    ### While the typing ... indicator is showing up, process the user input and generate a response
    async with message.channel.typing():
      bot_response = self.llm_service.call_model(messages)
      bot_response_with_emojis = replace_emojis(bot_response, self.custom_emojis)
      bot_response_with_stickers, test_list = replace_stickers(bot_response_with_emojis)
      sticker_list = []
      for sticker in test_list:
        try:
          sticker_list.append(await self.bot.fetch_sticker(int(sticker)))
        except:
          logger.info(f"Error occured while fetching stickers")
          return
      if not sticker_list:
        sticker_list = None
      server_contexts[server_id].append({"role": "assistant", "content": bot_response})
    if len(bot_response) > 2000:
      await ctx.send(file=text_to_file(bot_response))
    else:
      await ctx.send(bot_response_with_stickers, stickers=sticker_list)

    ### Reset the context if the conversation gets too long
    if len(server_contexts[server_id]) >= CONTEXT_LIMIT:
      server_contexts[server_id] = []
      await message.channel.send(self.context_reset_message)


async def setup(bot: commands.Bot) -> None:
  """
  Setup function to add the BotEvents cog to the bot.

  Args:
    bot (commands.Bot): The Discord bot instance.
  """
  await bot.add_cog(BotEvents(bot))
