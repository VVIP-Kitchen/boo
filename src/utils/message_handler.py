from typing import Optional, Union, List, Dict
import io
from utils.llm_utils import to_base64_data_uri


def prepare_chat_messages(
  prompt: Optional[str] = None,
  image: Optional[Union[io.BytesIO, bytes, str]] = None,
  messages: Optional[Union[str, List[Dict[str, str]]]] = None,
) -> List[Dict]:
  """
  Prepare chat messages from various input formats.

  Returns:
    List of chat messages in OpenAI format
  """
  if image:
    # Image + text mode
    image_url = image if isinstance(image, str) else to_base64_data_uri(image)
    content = [
      {"type": "text", "text": prompt or "Describe this image."},
      {"type": "image_url", "image_url": {"url": image_url}},
    ]
    return [{"role": "user", "content": content}]

  elif messages:
    # Messages format (either string or list)
    if isinstance(messages, str):
      return [{"role": "user", "content": messages}]
    else:
      return messages

  elif prompt:
    # Simple prompt mode
    return [{"role": "user", "content": prompt}]

  else:
    return []
