import discord
from discord.ext import commands

from utils.logger import logger
from services.llm_service import LLMService
from utils.emoji_utils import replace_emojis
from utils.message_utils import handle_user_mentions
from utils.config import CONTEXT_LIMIT, server_contexts, server_lore, PREFIX


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
    self.llm_service = LLMService()
    self.context_reset_message = "Context reset! Starting a new conversation. 👋"
    self.channel_name = "chat"

  @commands.Cog.listener()
  async def on_ready(self) -> None:
    """
    Event listener for when the bot is ready and connected.
    """
    logger.info(f"[INFO] {self.bot.user} has connected to Discord!")
    self.bot.custom_emojis = {
      emoji.name: emoji for guild in self.bot.guilds for emoji in guild.emojis
    }
    logger.info(f"[INFO] Loaded {len(self.bot.custom_emojis)} custom emojis.")

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
      return

    if message.content.startswith(PREFIX):
      await self.bot.process_commands(message)
      return

    ### Either get the server ID or get the author ID (in case of a DM)
    server_id = f"DM_{message.author.id}" if message.guild is None else message.guild.id

    if message.guild is not None:
      is_direct_reply = (
        message.reference
        and message.reference.resolved
        and message.reference.resolved.author == self.bot.user
      )
      is_mention = self.bot.user in message.mentions
      if (
        not (is_direct_reply or is_mention) or message.channel.name != self.channel_name
      ):
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
      bot_response_with_emojis = replace_emojis(bot_response, self.bot.custom_emojis)
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
