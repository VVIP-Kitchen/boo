import re
import discord
from discord.ext import commands

from utils.logger import logger
from utils.config import TEMPORAL_TASK_QUEUE
from utils.emoji_utils import extract_custom_emojis
from services.temporal_client import get_client
from workflows.image_workflows import DeleteImageWorkflow


class ImageHandlerCog(commands.Cog):
  """Helpers for sticker/emoji extraction + Meilisearch cleanup on message delete."""

  def __init__(self, bot: commands.Bot) -> None:
    self.bot = bot

  @commands.Cog.listener()
  async def on_message_delete(self, message: discord.Message) -> None:
    img_attachments = [
      att
      for att in message.attachments
      if att.content_type and att.content_type.startswith("image")
    ]
    if not img_attachments:
      return

    try:
      client = await get_client()
      for att in img_attachments:
        image_id = f"{message.id}_{att.id}"
        await client.start_workflow(
          DeleteImageWorkflow.run,
          image_id,
          id=f"image-delete-{image_id}",
          task_queue=TEMPORAL_TASK_QUEUE,
        )
    except Exception as e:
      logger.error(f"Failed to dispatch DeleteImageWorkflow: {e}")

  async def _extract_sticker_urls(self, prompt: str) -> tuple[str, list]:
    """Strip the &name;id;url& placeholders prepare_prompt appended and collect the URLs."""
    sticker_pattern = r"&([a-zA-Z0-9_]+);([0-9]+);([^&]+)&"
    urls: list[str] = []

    def replace_match(match):
      urls.append(match.group(3))
      return ""

    cleaned = re.sub(sticker_pattern, replace_match, prompt)
    return cleaned, urls

  async def _resolve_custom_emoji_urls(self, message: discord.Message) -> list:
    """Map any <:name:id> in the message to CDN URLs the LLM can ingest."""
    emoji_ids = extract_custom_emojis(message.content)
    if not emoji_ids:
      return []

    urls: list = []
    cache = {emoji.id: emoji for guild in self.bot.guilds for emoji in guild.emojis}
    for raw_id in emoji_ids:
      try:
        eid = int(raw_id)
      except ValueError:
        continue
      if eid in cache:
        urls.append(cache[eid].url)
        continue
      try:
        resolved = await self.bot.fetch_emoji(eid)
        urls.append(resolved.url)
      except Exception as e:
        logger.warning(f"Could not resolve emoji {eid}: {e}")
    return urls


async def setup(bot: commands.Bot) -> None:
  await bot.add_cog(ImageHandlerCog(bot))
