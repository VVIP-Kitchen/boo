import re
from discord import Emoji
from typing import Dict, List, Tuple


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

  def replace_match(match):
    emoji_name = match.group(1)
    return str(custom_emojis.get(emoji_name, match.group(0)))

  return re.sub(r":([a-zA-Z0-9_]+):", replace_match, text)


def replace_stickers(text: str) -> Tuple[str, List[str]]:
  """
  Replace sticker placeholders in text and extract sticker IDs.

  This function identifies sticker placeholders in the text (e.g., &sticker_name;123&)
  and replaces them with an empty string while collecting the sticker IDs into a list.
  The original formatting of the text is preserved.

  Args:
    text (str): The input text containing sticker placeholders.

  Returns:
    Tuple[str, List[str]]: A tuple with the modified text and a list of sticker IDs.
  """

  sticker_list = []

  def replace_match(match):
    sticker_id = match.group(1)
    sticker_list.append(sticker_id)
    return ""

  updated_text = re.sub(r"&[a-zA-Z0-9_]+;([0-9]+)&", replace_match, text)
  return updated_text, sticker_list
