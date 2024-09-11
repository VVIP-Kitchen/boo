from discord import Emoji
from typing import Dict, Union


def replace_emojis(text: str, custom_emojis: Dict[str, Emoji]) -> str:
  """
  Replace emoji placeholders in text with custom Discord emojis.

  This function takes a text string and a dictionary of custom emojis,
  and replaces any emoji placeholders (e.g., :emoji_name:) with the
  corresponding custom emoji if it exists in the dictionary.

  Args:
      text (str): The input text containing emoji placeholders.
      custom_emojis (Dict[str, Emoji]): A dictionary of custom Discord emojis.

  Returns:
      str: The text with emoji placeholders replaced by custom emojis.
  """

  words = text.split()
  for i, word in enumerate(words):
    ### Check if the word is an emoji placeholder
    if word.startswith(":") and word.endswith(":"):
      emoji_name = word[1:-1]

      ### Replace that placeholder with the custom emoji, if it exists
      if emoji_name in custom_emojis:
        words[i] = str(custom_emojis[emoji_name])
  return " ".join(words)


def replace_stickers(text: str):
  words = text.split()
  sticker_list = []
  for i, word in enumerate(words):
    if word.startswith("&") and word.endswith("&"):
      sticker_id = word.split(";")[1]
      sticker_list.append(sticker_id)

      words[i] = ""
  return " ".join(words), sticker_list
