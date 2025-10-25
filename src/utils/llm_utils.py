import re
import json
import base64
import io
from typing import Optional, Union


def to_base64_data_uri(image: Union[io.BytesIO, bytes]) -> str:
  """Convert image bytes to base64 data URI."""
  image_bytes = image.getvalue() if isinstance(image, io.BytesIO) else image
  base64_str = base64.b64encode(image_bytes).decode("utf-8")
  return f"data:image/jpeg;base64,{base64_str}"


def has_vision_content(messages) -> bool:
  """Check if any message contains image content."""
  try:
    for m in messages or []:
      c = m.get("content")
      if isinstance(c, list):
        for item in c:
          if isinstance(item, dict) and item.get("type") == "image_url":
            return True
  except Exception:
    pass
  return False
