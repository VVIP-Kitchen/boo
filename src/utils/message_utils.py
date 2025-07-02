import io
from typing import List
from discord.ext import commands
from discord import Message, Member, File


CHANNEL_NAME = "chat"


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


def is_direct_reply(message: Message, bot: commands.Bot) -> bool:
  return (
    message.reference
    and message.reference.resolved
    and message.reference.resolved.author == bot.user
  )


def text_to_file(bot_response):
  return File(io.BytesIO(str.encode(bot_response, "utf-8")), filename="output.txt")


def prepare_prompt(message: Message) -> str:
  prompt = handle_user_mentions(message)
  for sticker in message.stickers:
    prompt += f"&{sticker.name};{sticker.id};{sticker.url}&"
  return prompt

def log_message(message: Message) -> None:
  # Message Content
  print("Content:", message.content)

  # Author Info
  print("Author:", message.author)               # discord.Member or discord.User object
  print("Author Name:", message.author.name)     # Just the username

  # Server (Guild) Name
  if message.guild:
    print("Server Name:", message.guild.name)
    # Channel Name (for server text channels)
    print("Channel Name:", message.channel.name)
  else:
    print("This message is from a DM.")
    print("Channel: Direct Message")

  # Timestamp
  print("Timestamp:", message.created_at)
  print()
