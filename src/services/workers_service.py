import io
import time
import base64
from openai import OpenAI
from typing import List, Dict, Union
from utils.config import OPENROUTER_API_KEY, OPENROUTER_MODEL


class WorkersService:
  def __init__(self):
    self.client = OpenAI(
      base_url="https://openrouter.ai/api/v1",
      api_key=OPENROUTER_API_KEY,
    )
    self.model = OPENROUTER_MODEL

  def _to_base64_data_uri(self, image: Union[io.BytesIO, bytes]) -> str:
    if isinstance(image, io.BytesIO):
      image_bytes = image.getvalue()
    else:
      image_bytes = image
    base64_str = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/jpeg;base64,{base64_str}"

  def chat_completions(
    self,
    prompt: str = None,
    image: Union[io.BytesIO, bytes, str] = None,
    messages: Union[str, List[Dict[str, str]]] = None,
    temperature: float = 0.6,
    max_tokens: int = 512,
  ) -> str:
    try:
      if image:
        if isinstance(image, str):
          image_url = image
        else:
          image_url = self._to_base64_data_uri(image)

        content = [
          {"type": "text", "text": prompt or "Describe this image."},
          {"type": "image_url", "image_url": {"url": image_url}},
        ]
        chat_messages = [{"role": "user", "content": content}]
      elif messages:
        chat_messages = (
          [{"role": "user", "content": messages}]
          if isinstance(messages, str)
          else messages
        )
      elif prompt:
        chat_messages = [{"role": "user", "content": prompt}]
      else:
        return "⚠️ No input provided."

      response = self.client.chat.completions.create(
        model=self.model,
        messages=chat_messages,
        max_tokens=max_tokens,
        temperature=temperature,
      )
      return response.choices[0].message.content.strip(), response.usage
    except Exception as e:
      ### 429 + Retry time
      if hasattr(e, "response") and getattr(e.response, "status_code", None) == 429:
        headers = getattr(e.response, "headers", {})
        reset_ts = int(headers.get("X-RateLimit-Reset", "0"))
        current_ts = int(time.time())
        wait_sec = max(0, reset_ts - current_ts)

        mins = wait_sec // 60
        secs = wait_sec % 60
        formatted = f"{mins}m {secs}s" if mins else f"{secs}s"

        return (
          f"⏳ You've hit the rate limit for this model. Try again in {formatted}.\n"
          "You can also consider switching to a paid model on OpenRouter to avoid this."
        )

      ### Catch all
      from utils.logger import logger
      logger.error(f"Unexpected error in chat_completions: {e}")
      return "😵 Something went wrong while generating a response."

  def analyze_image(self, image: Union[io.BytesIO, bytes, str], prompt: str) -> str:
    return self.chat_completions(image=image, prompt=prompt)
