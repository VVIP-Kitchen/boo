import re
import io
import json
import redis
import logging
from typing import List
from discord.ext import commands
from services.db_service import DBService
from discord import Message, Member, File
from datetime import datetime, timedelta, timezone

CHANNEL_NAME = "chat"

# Set up logging
logger = logging.getLogger(__name__)

# Initialize Redis connection
redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)

# Initialize DB Service
db_service = DBService()


def should_ignore(message: Message, bot: commands.Bot) -> str | bool:
  ### Ignore bots - this should always return True to ignore
  if message.author.bot:
    return True

  ### Don't ignore DMs
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

  # Handle different combinations
  if is_mentioned and is_reply_to_other:
    return "mentioned_reply_other"
  elif is_mentioned:
    return "mentioned"
  elif is_reply_to_bot:
    return "reply"
  else:
    return True  # Ignore general messages (not mentioned or replied to)


def handle_user_mentions(message: Message) -> str:
  """
  Replace user mentions in a prompt with their corresponding usernames.

  This function takes a prompt string and a Discord message object,
  and replaces any user mentions (e.g., <@user_id>) with the corresponding
  username.

  Args:
    prompt (str): The input prompt containing user mentions.
    message (Message): The Discord message object containing mention information.

  Returns:
    str: The prompt with user mentions replaced by usernames.
  """
  prompt = message.content.strip()
  if "<@" in prompt:
    mentions: List[Member] = message.mentions
    for mention in mentions:
      user_id: int = mention.id
      username: str = mention.name
      prompt = prompt.replace(f"<@{user_id}>", f"{username}")
  return prompt


def prepare_prompt(message: Message) -> str:
  prompt = handle_user_mentions(message)
  for sticker in message.stickers:
    prompt += f"&{sticker.name};{sticker.id};{sticker.url}&"
  return prompt


def text_to_file(bot_response):
  return File(io.BytesIO(str.encode(bot_response, "utf-8")), filename="output.txt")


def store_persistent_messages(message: Message):
  # 💡 1. Skip bot messages
  if message.author.bot or message.webhook_id:
    return

  # 💡 2. Filter low-content messages
  content = message.content.strip()
  if (
    not content
    or len(content) < 1
    or content.startswith(("!", ".", "/", "~", "-", "$"))
    or re.fullmatch(r"(@\S+\s?)+", content)
  ):
    return

  # 💡 3. Media-only messages (no text)
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
  response = db_service.store_message(message_data)
  logger.info(f"Response of adding message: {response}")


def log_message(message: Message) -> None:
  # Skip messages with attachments (files)
  if message.attachments:
    return

  # Store in persistent DB
  store_persistent_messages(message)

  # Create message object for Redis storage
  message_data = {
    "server_name": message.guild.name if message.guild else "Direct Message",
    "server_id": str(message.guild.id) if message.guild else "DM",
    "author_name": message.author.name,
    "content": message.content,
    "timestamp": message.created_at.isoformat(),
  }

  # Use channel ID as Redis key
  channel_key = str(message.channel.id)

  try:
    # Store in Redis as JSON string in a list
    redis_client.lpush(channel_key, json.dumps(message_data))
    logger.info(f"✅ Message stored in Redis for channel {channel_key}")

    # Clean up old messages (older than 15 minutes)
    cleanup_old_messages(channel_key)

  except Exception as e:
    logger.error(f"❌ Failed to store message in Redis: {e}")


def cleanup_old_messages(channel_key: str) -> None:
  """Remove messages older than 15 minutes from Redis"""
  # Use UTC timezone to match Discord's message timestamps
  cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=15)

  try:
    # Get all messages from the list
    messages = redis_client.lrange(channel_key, 0, -1)

    if not messages:
      return

    # Filter out old messages
    valid_messages = []
    for msg_json in messages:
      try:
        msg_data = json.loads(msg_json)
        # Parse the ISO format timestamp (it includes timezone info)
        msg_time = datetime.fromisoformat(msg_data["timestamp"])

        # Ensure both datetimes are timezone-aware for comparison
        if msg_time.tzinfo is None:
          msg_time = msg_time.replace(tzinfo=timezone.utc)

        if msg_time > cutoff_time:
          valid_messages.append(msg_json)
      except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(f"Skipping invalid message data: {e}")
        continue

    # Replace the list with filtered messages
    if valid_messages:
      # Use pipeline for atomic operations
      pipe = redis_client.pipeline()
      pipe.delete(channel_key)
      pipe.lpush(channel_key, *valid_messages)
      pipe.execute()
      logger.info(
        f"🧹 Cleaned up {len(messages) - len(valid_messages)} old messages from channel {channel_key}"
      )
    else:
      redis_client.delete(channel_key)
      logger.info(f"🧹 Deleted empty channel {channel_key}")

  except Exception as e:
    logger.error(f"❌ Failed to cleanup old messages for channel {channel_key}: {e}")


def get_channel_messages(channel_id: str) -> list:
  """Retrieve all messages for a channel from Redis"""
  try:
    messages = redis_client.lrange(str(channel_id), 0, -1)
    return [json.loads(msg) for msg in messages if msg]
  except Exception as e:
    logger.error(f"❌ Failed to retrieve messages for channel {channel_id}: {e}")
    return []


def get_reply_context(message: Message) -> str:
  """
  Extract the context from a replied-to message, including embed content.

  Args:
    message (Message): The Discord message object that might be a reply.

  Returns:
    str: The content of the replied-to message including embeds, or empty string if not a reply.
  """
  if message.reference and message.reference.resolved:
    replied_to_message = message.reference.resolved
    context = (
      f"[Replying to {replied_to_message.author.name}]: {replied_to_message.content}"
    )

    # Add embed content if present
    if replied_to_message.embeds:
      embed_content = []
      for embed in replied_to_message.embeds:
        embed_parts = []

        # Add embed title
        if embed.title:
          embed_parts.append(f"Title: {embed.title}")

        # Add embed description
        if embed.description:
          embed_parts.append(f"Description: {embed.description}")

        # Add embed fields
        if embed.fields:
          for field in embed.fields:
            field_text = f"{field.name}: {field.value}"
            embed_parts.append(field_text)

        # Add embed footer
        if embed.footer:
          embed_parts.append(f"Footer: {embed.footer.text}")

        # Add embed author
        if embed.author:
          embed_parts.append(f"Author: {embed.author.name}")

        # Add embed URL
        if embed.url:
          embed_parts.append(f"URL: {embed.url}")

        if embed_parts:
          embed_content.append("Embed: " + " | ".join(embed_parts))

      if embed_content:
        context += "\n" + "\n".join(embed_content)

    return context
  return ""
