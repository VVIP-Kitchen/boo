import discord
from discord.ext import commands

from utils.logger import logger
from utils.message_utils import (
  CHANNEL_NAME,
  log_message,
  should_ignore,
  prepare_prompt,
  get_reply_context,
  send_error_message,
)
from services.temporal_client import get_client
from utils.config import TEMPORAL_TASK_QUEUE
from activities.models import ChatRequest, ImageIndexInput
from workflows.chat_workflow import BooChatWorkflow
from workflows.image_workflows import ImageIndexWorkflow
from .image_handler import ImageHandlerCog


class MessageHandlerCog(commands.Cog):
  """Discord gateway listener. Builds a ChatRequest and starts a Temporal workflow."""

  def __init__(self, bot: commands.Bot) -> None:
    self.bot = bot
    self.channel_name = CHANNEL_NAME
    self.image_handler = ImageHandlerCog(bot)

  @commands.Cog.listener()
  async def on_message(self, message: discord.Message) -> None:
    if message.author.bot and message.author.id != 1413943952524054550:
      return
    self.bot.loop.create_task(self.dispatch(message))

  async def dispatch(self, message: discord.Message) -> None:
    log_message(message)
    reason = should_ignore(message, self.bot)
    if reason is True:
      return

    try:
      if reason in ("reply", "mentioned_reply_other"):
        reply_context = get_reply_context(message)
        if reply_context:
          message.content = f"This is a reply to: {reply_context}\n\n{message.content}"

      server_id = (
        f"DM_{message.author.id}" if message.guild is None else str(message.guild.id)
      )

      prompt_with_stickers = prepare_prompt(message)
      cleaned_prompt, sticker_urls = await self.image_handler._extract_sticker_urls(
        prompt_with_stickers
      )
      emoji_urls = await self.image_handler._resolve_custom_emoji_urls(message)

      image_attachments = [
        att
        for att in message.attachments
        if (att.content_type and att.content_type.startswith("image"))
        or att.filename.lower().endswith((".gif", ".png", ".jpg", ".jpeg", ".webp"))
      ]

      lower = cleaned_prompt.lower()
      is_reset = "reset" in lower and "reset chat" in lower

      members_list = ""
      if message.guild is not None:
        members_list = await self._format_members_list(message.guild)

      req = ChatRequest(
        channel_id=str(message.channel.id),
        message_id=str(message.id),
        guild_id=str(message.guild.id) if message.guild else None,
        server_id=server_id,
        server_name=message.guild.name if message.guild else "Direct Message",
        channel_name=getattr(message.channel, "name", "DM"),
        author_id=str(message.author.id),
        author_name=message.author.name,
        author_display_name=message.author.display_name,
        prompt=cleaned_prompt,
        image_urls=[att.url for att in image_attachments],
        sticker_urls=sticker_urls,
        emoji_urls=emoji_urls,
        members_list=members_list,
        is_reset=is_reset,
      )

      client = await get_client()
      await client.start_workflow(
        BooChatWorkflow.run,
        req,
        id=f"chat-{message.id}",
        task_queue=TEMPORAL_TASK_QUEUE,
      )

      message_url = (
        f"https://discord.com/channels/"
        f"{message.guild.id if message.guild else '@me'}/"
        f"{message.channel.id}/{message.id}"
      )
      for att in image_attachments:
        index_input = ImageIndexInput(
          image_url=att.url,
          user_caption=cleaned_prompt or None,
          image_id=f"{message.id}_{att.id}",
          message_url=message_url,
          message_id=str(message.id),
          server_id=server_id,
          server_name=req.server_name,
          channel_id=str(message.channel.id),
          channel_name=req.channel_name,
          author_id=str(message.author.id),
          author_name=f"{message.author.name} ({message.author.display_name})",
          attachment_filename=att.filename,
          attachment_size=att.size,
        )
        await client.start_workflow(
          ImageIndexWorkflow.run,
          index_input,
          id=f"image-index-{message.id}-{att.id}",
          task_queue=TEMPORAL_TASK_QUEUE,
        )

    except Exception as e:
      logger.error(f"Failed to dispatch message {message.id}: {e}", exc_info=True)
      await send_error_message(message)

  async def _format_members_list(self, guild: discord.Guild) -> str:
    try:
      await guild.chunk()
      members = [
        f"- {m.name} (Display: {m.display_name}) - ID: {m.id}"
        for m in guild.members
        if not m.bot
      ]
      if not members:
        return "## Server Members\nNo members found."
      return (
        "## Server Members\n"
        "To ping a member, use <@user_id> format. Available members:\n"
        + "\n".join(members)
      )
    except Exception as e:
      logger.error(f"Failed to chunk guild members: {e}")
      return ""


async def setup(bot: commands.Bot) -> None:
  await bot.add_cog(MessageHandlerCog(bot))
