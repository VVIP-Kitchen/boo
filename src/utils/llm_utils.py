import io
import base64
from typing import Union


def _detect_mime_type(data: bytes) -> str:
  if data[:8] == b'\x89PNG\r\n\x1a\n':
    return "image/png"
  if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
    return "image/webp"
  if data[:3] == b'GIF':
    return "image/gif"
  return "image/jpeg"


def to_base64_data_uri(image: Union[io.BytesIO, bytes]) -> str:
  """Convert image bytes to base64 data URI with correct MIME type."""
  image_bytes = image.getvalue() if isinstance(image, io.BytesIO) else image
  mime_type = _detect_mime_type(image_bytes)
  base64_str = base64.b64encode(image_bytes).decode("utf-8")
  return f"data:{mime_type};base64,{base64_str}"


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
