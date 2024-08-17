from typing import List
from discord import Message, Member


def handle_user_mentions(prompt: str, message: Message) -> str:
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

  if "<@" in prompt:
    mentions: List[Member] = message.mentions

    for mention in mentions:
      user_id: int = mention.id
      username: str = mention.name
      prompt = prompt.replace(f"<@{user_id}>", f"{username}")

  return prompt
