import re
import discord

from utils.logger import logger
from discord.ext import commands
from services.llm_service import LLMService
from utils.emoji_utils import replace_emojis, replace_stickers
from utils.config import CONTEXT_LIMIT, server_contexts, server_lore, PREFIX
from utils.message_utils import handle_user_mentions, is_direct_reply


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
    
    for sticker in message.stickers:
      prompt = prompt + f"&{sticker.name};{sticker.id};{sticker.url}&"
      
    if message.author.bot or len(prompt) == 0:
      return

    if message.content.startswith(PREFIX):
      await self.bot.process_commands(message)
      return

    ### Either get the server ID or get the author ID (in case of a DM)
    server_id = f"DM_{message.author.id}" if message.guild is None else message.guild.id

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
        await ctx.send(
          "Ping me in <#1272840978277072918> to talk", ephemeral=True, reference=message
        )
        return

    ### Build the context
    prompt = handle_user_mentions(prompt, message)
    server_contexts[server_id].append(
      {
        "role": "user",
        "content": f"{message.author.name} (aka {message.author.display_name}) said: {prompt}",
      }
    )
    messages = [{"role": "system", "content": server_lore}] + server_contexts[server_id]

    ### While the typing ... indicator is showing up, process the user input and generate a response
    async with message.channel.typing():
      bot_response = self.llm_service.call_model(messages)
      bot_response_with_emojis = replace_emojis(bot_response, self.custom_emojis)
      bot_response_with_stickers, stickerlist = replace_stickers(bot_response_with_emojis)
      if not stickerlist:
        sticker_list = None
      server_contexts[server_id].append({"role": "assistant", "content": bot_response})
    await message.channel.send(bot_response_with_stickers, reference=message,sticker=sticker_list)

    ### Reset the context if the conversation gets too long
    if len(server_contexts[server_id]) >= CONTEXT_LIMIT:
      server_contexts[server_id] = []
      await message.channel.send(self.context_reset_message)

  @commands.Cog.listener()
  async def on_raw_message_delete(self, payload):
    # PREPROCESSING TO CHECK IF THE DELETED MESSAGE IS SAME AS THE ONE SENT BY NQN
    test_id = payload.channel_id
    test_content = payload.cached_message.content
    channel = self.bot.get_channel(test_id)

    def match_object(matchobj):
      return re.search(r"\:.*\:", matchobj.group(0)).group(0)

    messages = [
      message async for message in channel.history(limit=1) if message.author.bot
    ]
    message = messages[0]
    message.content = re.sub(
      r"<[A-Za-z_0-9]*\:[A-Za-z_0-9]*\:[0-9]*>", match_object, message.content
    )
    message.author.bot = False
    if not message.content == test_content:
      return

    prompt = message.content.strip()
    server_id = f"DM_{message.author.id}" if message.guild is None else message.guild.id

    if message.guild is not None:
      is_direct_reply = (
        message.reference
        and message.reference.resolved
        and message.reference.resolved.author == self.bot.user
      )
      is_mention = self.bot.user in message.mentions
      if not (is_direct_reply or is_mention):
        return
      if message.channel.name != self.channel_name:
        ctx = await self.bot.get_context(message)
        await ctx.send(
          "Ping me in <#1272840978277072918> to talk", ephemeral=True, reference=message
        )
        return

    if "reset chat" in prompt.lower():
      server_contexts[server_id] = []
      await message.channel.send(self.context_reset_message)
      return

    ### Build the context
    prompt = handle_user_mentions(prompt, message)
    server_contexts[server_id].append(
      {
        "role": "user",
        "content": f"{message.author.name} (aka {message.author.display_name}) said: {prompt}",
      }
    )
    messages = [{"role": "system", "content": server_lore}] + server_contexts[server_id]

    ### While the typing ... indicator is showing up, process the user input and generate a response
    async with message.channel.typing():
      bot_response = self.llm_service.call_model(messages)
      bot_response_with_emojis = replace_emojis(bot_response, self.custom_emojis)
      server_contexts[server_id].append({"role": "assistant", "content": bot_response})
    await message.channel.send(bot_response_with_emojis, reference=message)

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
