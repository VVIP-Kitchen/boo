from discord.ext import commands
from services.llm_service import LLMService
from utils.config import CONTEXT_LIMIT, server_contexts, server_lore, PREFIX
from utils.message_utils import handle_user_mentions
from utils.emoji_utils import replace_emojis


class BotEvents(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.llm_service = LLMService()
    self.context_reset_message = "Context reset! Starting a new conversation. 👋"
    self.channel_name = "chat"

  @commands.Cog.listener()
  async def on_ready(self):
    print(f"[INFO] {self.bot.user} has connected to Discord!")
    self.bot.custom_emojis = {
      emoji.name: emoji for guild in self.bot.guilds for emoji in guild.emojis
    }
    print(f"[INFO] Loaded {len(self.bot.custom_emojis)} custom emojis.")

  @commands.Cog.listener()
  async def on_message(self, message):
    if message.author.bot or len(message.content.strip()) == 0:
      return

    if message.content.startswith(PREFIX):
      await self.bot.process_commands(message)
      return

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

    prompt = message.content.strip()

    if "reset chat" in prompt.lower():
      server_contexts[server_id] = []
      await message.channel.send(self.context_reset_message)
      return

    prompt = handle_user_mentions(prompt, message)
    server_contexts[server_id].append(
      {
        "role": "user",
        "content": f"{message.author.name} (aka {message.author.display_name}) said: {prompt}",
      }
    )
    messages = [{"role": "system", "content": server_lore}] + server_contexts[server_id]

    async with message.channel.typing():
      bot_response = self.llm_service.call_model(messages)
      bot_response_with_emojis = replace_emojis(bot_response, self.bot.custom_emojis)
      server_contexts[server_id].append({"role": "assistant", "content": bot_response})

    await message.channel.send(bot_response_with_emojis, reference=message)

    if len(server_contexts[server_id]) >= CONTEXT_LIMIT:
      server_contexts[server_id] = []
      await message.channel.send(self.context_reset_message)


async def setup(bot):
  await bot.add_cog(BotEvents(bot))
