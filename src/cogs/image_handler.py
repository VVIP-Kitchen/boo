import discord
from discord.ext import commands
from utils.logger import logger
from services.llm_service import LLMService
from services.async_caller_service import to_thread
from services.voyageai_service import VoyageAiService
from services.task_queue_service import TaskQueueService
from services.meilisearch_service import MeilisearchService
from utils.emoji_utils import replace_emojis, replace_stickers, extract_custom_emojis, get_emoji_cdn_url
from services.image_processing_service import ImageProcessingService


class ImageHandlerCog(commands.Cog):
  def __init__(self, bot: commands.Bot) -> None:
    self.bot = bot
    self.llm_service = LLMService()
    self.voyage_service = VoyageAiService()
    self.meili_service = MeilisearchService()
    self.image_processor = ImageProcessingService(
      llm_service=self.llm_service,
      voyage_service=self.voyage_service,
      meilisearch_service=self.meili_service,
    )
    self.task_queue = TaskQueueService()

  @commands.Cog.listener()
  async def on_message_delete(self, message: discord.Message) -> None:
    try:
      img_attachments = [
        att
        for att in message.attachments
        if att.content_type and att.content_type.startswith("image")
      ]
      if not img_attachments:
        return

      logger.info(f"Message {message.id} deleted with {len(img_attachments)} images")
      for att in img_attachments:
        img_id = f"{message.id}_{att.id}"
        try:
          await to_thread(self.meili_service.delete_document, img_id)
          logger.info(f"Delete image {img_id} from Meilisearch")
        except Exception as e:
          logger.error(f"Failed to delete image {img_id}: {e}")
    except Exception as e:
      logger.error(f"Error in on_message_delete: {e}")

  async def _queue_images_for_processing(
    self,
    message: discord.Message,
    image_attachments: list,
    user_caption: str,
  ) -> None:
    if not self.task_queue.queue:
      logger.warning("Task queue not available, skipping background processing")
      return

    logger.info(f"Queueing {len(image_attachments)} images for background processing")
    for idx, attachment in enumerate(image_attachments):
      try:
        img_bytes = await attachment.read()
        message_url = f"https://discord.com/channels/{message.guild.id if message.guild else '@me'}/{message.channel.id}/{message.id}"
        image_id = f"{message.id}_{attachment.id}"
        job_id = await to_thread(
          self.task_queue.enqueue_image_processing,
          image_bytes=img_bytes,
          user_caption=user_caption,
          image_id=image_id,
          message_url=message_url,
          message_id=str(message.id),
          server_id=str(message.guild.id)
          if message.guild
          else f"DM_{message.author.id}",
          server_name=message.guild.name if message.guild else "Direct Message",
          channel_id=str(message.channel.id),
          channel_name=getattr(message.channel, "name", "DM"),
          author_id=str(message.author.id),
          author_name=f"{message.author.name} ({message.author.display_name})",
          attachment_url=attachment.url,
          attachment_filename=attachment.filename,
          attachment_size=attachment.size,
        )
        if job_id:
          logger.info(
            f"✅ Queued image {idx + 1}/{len(image_attachments)}: {image_id} (job: {job_id})"
          )
        else:
          logger.error(f"❌ Failed to queue image {idx + 1}/{len(image_attachments)}")
      except Exception as e:
        logger.error(f"❌ Error queueing attachment {attachment.filename}: {e}")
        continue

  async def _replace_stickers(self, bot_response: str) -> tuple[str, list]:
    custom_emojis = {
      emoji.name: emoji for guild in self.bot.guilds for emoji in guild.emojis
    }
    bot_response = replace_emojis(bot_response, custom_emojis)
    return replace_stickers(bot_response)

  async def _fetch_stickers(self, sticker_ids: list) -> list:
    stickers = []
    for sid in sticker_ids:
      try:
        stickers.append(await self.bot.fetch_sticker(int(sid)))
      except:
        logger.info(f"Sticker not found: {sid}")
    return stickers

  async def _extract_sticker_urls(self, prompt: str) -> tuple[str, list]:
    """Extract sticker URLs from prompt placeholders and return cleaned prompt + URLs"""
    sticker_pattern = r"&([a-zA-Z0-9_]+);([0-9]+);([^&]+)&"
    urls = []

    def replace_match(match):
      urls.append(match.group(3))
      return ""

    cleaned_prompt = re.sub(sticker_pattern, replace_match, prompt)
    return cleaned_prompt, urls

  async def _resolve_custom_emoji_urls(self, message: discord.Message) -> list:
    """Extract custom emoji IDs from message and return CDN URLs for LLM processing"""
    emoji_ids = extract_custom_emojis(message.content)
    if not emoji_ids:
      return []

    urls = []
    # Build emoji cache from all guilds
    emoji_cache = {emoji.id: emoji for guild in self.bot.guilds for emoji in guild.emojis}

    for emoji_id_str in emoji_ids:
      try:
        emoji_id = int(emoji_id_str)
        if emoji_id in emoji_cache:
          emoji = emoji_cache[emoji_id]
          # Use the emoji's URL directly
          urls.append(emoji.url)
        else:
          # Try to fetch from API
          try:
            resolved_emoji = await self.bot.fetch_emoji(emoji_id)
            urls.append(resolved_emoji.url)
          except Exception as e:
            logger.warning(f"Could not resolve emoji {emoji_id}: {e}")
      except ValueError:
        pass

    return urls


async def setup(bot: commands.Bot) -> None:
  await bot.add_cog(ImageHandlerCog(bot))
