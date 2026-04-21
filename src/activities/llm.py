from dataclasses import dataclass, field
from typing import List

from temporalio import activity

from services.llm_service import LLMService
from activities.models import ChatRequest, ChatResult, GeneratedImage, TokenUsage


@dataclass
class AgenticChatInput:
  request: ChatRequest
  lore: str
  history: List[dict] = field(default_factory=list)
  memories: List[dict] = field(default_factory=list)


def _build_user_content(req: ChatRequest) -> list:
  content: list = [{"type": "text", "text": req.prompt or "Please respond to this message."}]
  for url in req.sticker_urls + req.emoji_urls + req.image_urls:
    content.append({"type": "image_url", "image_url": {"url": url}})
  return content


def _build_system_prompt(req: ChatRequest, lore: str, memories: list) -> str:
  base = lore or "You are a helpful assistant"
  if req.members_list:
    base = f"{base}\n\n{req.members_list}"
  if memories:
    facts = [m.get("fact", "") for m in memories if m.get("fact")]
    if facts:
      base = (
        f"{base}\n\n-# Things you know about {req.author_name}: {', '.join(facts)}"
      )
  return base


@activity.defn
def run_agentic_chat(payload: AgenticChatInput) -> ChatResult:
  req = payload.request
  user_content = _build_user_content(req)
  system_prompt = _build_system_prompt(req, payload.lore, payload.memories)

  messages = (
    [{"role": "system", "content": system_prompt}]
    + payload.history
    + [{"role": "user", "content": user_content}]
  )

  bot_response, usage, generated_images = LLMService().chat_completions(
    messages=messages,
    enable_tools=True,
    guild_id=req.server_id,
  )

  has_imgs = bool(req.image_urls)
  user_log = (
    f"{req.author_name} (aka {req.author_display_name}, ID: {req.author_id}) said: "
    f"{req.prompt}"
    + (f"\n\n[Attached {len(req.image_urls)} image(s)]" if has_imgs else "")
  )

  return ChatResult(
    response_text=bot_response,
    usage=TokenUsage(
      prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
      total_tokens=getattr(usage, "total_tokens", 0) or 0,
    ),
    generated_images=[
      GeneratedImage(data=img["data"], format=img.get("format", "png"))
      for img in (generated_images or [])
    ],
    appended_messages=[
      {"role": "user", "content": user_log},
      {"role": "assistant", "content": bot_response},
    ],
  )
