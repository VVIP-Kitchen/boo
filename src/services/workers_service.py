import io
import base64
from typing import List, Dict, Union
from PIL import Image
from openai import OpenAI
from utils.logger import logger
from utils.config import OPENROUTER_API_KEY


class WorkersService:
  """
  Service using OpenRouter-hosted LLMs via OpenAI-compatible SDK.
  """

  def __init__(
    self,
    model: str = "mistralai/mistral-small-3.1-24b-instruct:free"
  ):
    self.client = OpenAI(
      base_url="https://openrouter.ai/api/v1",
      api_key=OPENROUTER_API_KEY,
    )
    self.model = model

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
          # Image is a URL
          image_url = image
        else:
          # Image is bytes or BytesIO
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
      return response.choices[0].message.content.strip()

    except Exception as e:
      logger.error(f"OpenRouter chat_completions error: {e}")
      return "😵 Something went wrong while talking to the LLM."

  def analyze_image(self, image: Union[io.BytesIO, bytes, str], prompt: str) -> str:
    return self.chat_completions(image=image, prompt=prompt)
