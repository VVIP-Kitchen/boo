import re
import io
import base64
import discord
import logging
from typing import List
from discord.ext import commands
from services.db_service import DBService
from discord import Message, Member, File

CHANNEL_NAME = "chat"

logger = logging.getLogger(__name__)
db_service = DBService()


def should_ignore(message: Message, bot: commands.Bot) -> str | bool:
  """Decide whether the bot should respond to this message."""
  if message.author.bot and not message.author.id == 1413943952524054550:
    return True

  if message.guild is None:
    return "dm"

  is_mentioned = bot.user in message.mentions
  is_reply_to_bot = (
    message.reference
    and message.reference.resolved
    and message.reference.resolved.author == bot.user
  )
  is_reply_to_other = (
    message.reference
    and message.reference.resolved
    and message.reference.resolved.author != bot.user
  )

  if is_mentioned and is_reply_to_other:
    return "mentioned_reply_other"
  elif is_mentioned:
    return "mentioned"
  elif is_reply_to_bot:
    return "reply"
  else:
    return True


def handle_user_mentions(message: Message) -> str:
  """Replace `<@user_id>` mentions with `username` so the LLM sees readable names."""
  prompt = message.content.strip()
  if "<@" in prompt:
    mentions: List[Member] = message.mentions
    for mention in mentions:
      prompt = prompt.replace(f"<@{mention.id}>", f"{mention.name}")
  return prompt


def prepare_prompt(message: Message) -> str:
  prompt = handle_user_mentions(message)
  for sticker in message.stickers:
    prompt += f"&{sticker.name};{sticker.id};{sticker.url}&"
  return prompt


def text_to_file(bot_response):
  return File(io.BytesIO(str.encode(bot_response, "utf-8")), filename="output.txt")


def store_persistent_messages(message: Message):
  if message.author.bot or message.webhook_id:
    return

  content = message.content.strip()
  if (
    not content
    or len(content) < 1
    or content.startswith(("!", ".", "/", "~", "-", "$"))
    or re.fullmatch(r"(@\S+\s?)+", content)
  ):
    return

  if not content and message.attachments:
    return

  message_data = {
    "message_id": str(message.id),
    "server_name": message.guild.name if message.guild else "Direct Message",
    "channel_name": message.channel.name if hasattr(message.channel, "name") else "DM",
    "channel_id": str(message.channel.id),
    "author_name": message.author.name,
    "author_nickname": message.author.nick
    if hasattr(message.author, "nick") and message.author.nick
    else message.author.name,
    "author_id": str(message.author.id),
    "message_content": message.content,
    "timestamp": message.created_at.isoformat(),
  }
  db_service.store_message(message_data)


def log_message(message: Message) -> None:
  if message.attachments:
    return
  store_persistent_messages(message)


def get_reply_context(message: Message) -> str:
  """Extract the content + embed of the message being replied to, for LLM context."""
  if not (message.reference and message.reference.resolved):
    return ""

  replied_to_message = message.reference.resolved
  context = (
    f"[Replying to {replied_to_message.author.name}]: {replied_to_message.content}"
  )

  if not replied_to_message.embeds:
    return context

  embed_lines: list[str] = []
  for embed in replied_to_message.embeds:
    parts: list[str] = []
    if embed.title:
      parts.append(f"Title: {embed.title}")
    if embed.description:
      parts.append(f"Description: {embed.description}")
    if embed.fields:
      parts.extend(f"{f.name}: {f.value}" for f in embed.fields)
    if embed.footer:
      parts.append(f"Footer: {embed.footer.text}")
    if embed.author:
      parts.append(f"Author: {embed.author.name}")
    if embed.url:
      parts.append(f"URL: {embed.url}")
    if parts:
      embed_lines.append("Embed: " + " | ".join(parts))

  if embed_lines:
    context += "\n" + "\n".join(embed_lines)
  return context


async def send_error_message(message: Message) -> None:
  try:
    await message.channel.send(
      "I encountered an error while processing your message. Please try again later!",
      reference=message,
    )
  except discord.errors.HTTPException:
    logger.error("Failed to send error message")


async def send_message(message: Message, response: str) -> None:
  await message.channel.send(
    response if len(response) < 1800 else text_to_file(response)
  )


async def send_response(
  message: Message, response: str, stickers: list, _usage, generated_images: list = None
) -> None:
  files = []
  if generated_images:
    for idx, img_data in enumerate(generated_images):
      image_bytes = base64.b64decode(img_data["data"])
      img_format = img_data.get("format", "png")
      filename = f"generated_image_{idx + 1}.{img_format}"
      files.append(File(io.BytesIO(image_bytes), filename=filename))

  if len(response) > 1800:
    await message.channel.send(file=text_to_file(response), reference=message)
    if files:
      await message.channel.send(files=files)
  else:
    await message.channel.send(
      response, reference=message, stickers=stickers, files=files if files else None
    )
