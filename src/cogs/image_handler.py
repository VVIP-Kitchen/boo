import discord
from discord.ext import commands
from utils.logger import logger
from services.llm_service import LLMService
from services.async_caller_service import to_thread
from services.voyageai_service import VoyageAiService
from services.task_queue_service import TaskQueueService
from services.meilisearch_service import MeilisearchService
from utils.emoji_utils import replace_emojis, replace_stickers
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
                att for att in message.attachments
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
                    server_id=str(message.guild.id) if message.guild else f"DM_{message.author.id}",
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
                    logger.info(f"✅ Queued image {idx + 1}/{len(image_attachments)}: {image_id} (job: {job_id})")
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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ImageHandlerCog(bot))
