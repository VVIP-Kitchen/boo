from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ChatRequest:
  """Everything the worker needs to handle one Discord message end-to-end."""

  channel_id: str
  message_id: str
  guild_id: Optional[str]
  server_id: str
  server_name: str
  channel_name: str
  author_id: str
  author_name: str
  author_display_name: str
  prompt: str
  image_urls: List[str] = field(default_factory=list)
  sticker_urls: List[str] = field(default_factory=list)
  emoji_urls: List[str] = field(default_factory=list)
  members_list: str = ""
  is_reset: bool = False


@dataclass
class TokenUsage:
  prompt_tokens: int = 0
  total_tokens: int = 0


@dataclass
class GeneratedImage:
  data: str
  format: str = "png"


@dataclass
class ChatResult:
  """Output of the agentic LLM activity."""

  response_text: str
  usage: TokenUsage
  generated_images: List[GeneratedImage] = field(default_factory=list)
  appended_messages: List[dict] = field(default_factory=list)


@dataclass
class SendResponseInput:
  channel_id: str
  reply_to: Optional[str]
  content: str
  sticker_ids: List[str] = field(default_factory=list)
  generated_images: List[GeneratedImage] = field(default_factory=list)


@dataclass
class TokenUsageInput:
  message_id: str
  guild_id: str
  author_id: str
  input_tokens: int
  output_tokens: int


@dataclass
class ImageIndexInput:
  image_url: str
  user_caption: Optional[str]
  image_id: str
  message_url: str
  message_id: str
  server_id: str
  server_name: str
  channel_id: str
  channel_name: str
  author_id: str
  author_name: str
  attachment_filename: str
  attachment_size: int
