import io
import base64
import requests
from PIL import Image
from utils.logger import logger
from typing import List, Dict, Union
from utils.config import (
  CLOUDFLARE_ACCOUNT_ID,
  CLOUDFLARE_WORKERS_AI_API_KEY,
  CF_WORKERS_VISION_LANGUAGE_MODEL,
  CF_WORKERS_IMAGE_GENERATION_MODEL
)


class WorkersService:
  """
  Service for interacting with language and image generation models.
  """

  def __init__(self) -> None:
    """
    Initialize the LLMService with necessary API endpoints and headers.
    """

    self.search_models_endpoint = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/models/search"
    self.vision_language_model_endpoint = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{CF_WORKERS_VISION_LANGUAGE_MODEL}"
    self.image_generation_model_endpoint = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{CF_WORKERS_IMAGE_GENERATION_MODEL}"
    self.headers = {"Authorization": f"Bearer {CLOUDFLARE_WORKERS_AI_API_KEY}"}
    self.timeout = 30  ### Timeout of 30s
  
  def _image_bytes_to_data_uri(self, image_bytes, mime_type="image/jpeg"):
    base64_str = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{base64_str}"

  def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
    try:
      response = requests.request(method, url, timeout=self.timeout, **kwargs)
      response.raise_for_status()
      return response
    except ConnectionError:
      logger.error(f"Connection error occurred while requesting {url}")
      raise
    except requests.RequestException as e:
      logger.error(f"Request to {url} failed: {e}")
      raise

  def _download_image(self, image: Union[io.BytesIO, bytes, str]) -> bytes:
    if isinstance(image, str):
      response = self._make_request("GET", image)
      return response.content
    elif isinstance(image, io.BytesIO):
      return image.getvalue()
    return image

  def _compress_image(self, image_data: bytes, max_size: int = 600 * 1024, quality: int = 85) -> bytes:
    if len(image_data) <= max_size:
      return image_data

    image = Image.open(io.BytesIO(image_data))
    image = image.convert("RGB")
    output = io.BytesIO()

    while True:
      image.save(output, format="JPEG", quality=quality, optimize=True)
      if output.tell() <= max_size or quality <= 20:
        break
      quality -= 5
      output.seek(0)
      output.truncate()

    return output.getvalue()

  async def generate_image(self, prompt: str, num_steps: int = 4) -> Union[io.BytesIO, str]:
    from services.queue_service import queue_service
    try:
      req_id = await queue_service.add_to_queue({
        "type": "image_generation",
        "params": {
          "prompt": prompt,
          "num_steps": min(max(num_steps, 1), 8)
        }
      })
      result = await queue_service.get_result(req_id, timeout=60)

      if result["status"] == "success":
        ### Error message
        if isinstance(result["result"], str):
          return result["result"]
        
        return result["result"] ### Actual image (io.BytesIO object)
      elif result["status"] == "timeout":
        return "⏱️ Your request is taking longer than expected. Please try again later."
      else:
        return "🤔 I encountered an issue while creating your image. Please try again later."
    except Exception as e:
      logger.error(f"Error in queued generate_image: {e}")
      return "😵 Oops! Something unexpected happened while generating the image."

  def _direct_generate_image(self, prompt: str, num_steps: int = 4) -> Union[io.BytesIO, str]:
    """
    Direct image generation (called by queue processor).
    """
    json_data = { "prompt": prompt, "num_steps": num_steps }

    try:
      response = self._make_request("POST", self.image_generation_model_endpoint, headers=self.headers, json=json_data)
      response.raise_for_status()
      data = response.json()

      if "image" in data["result"]:
        image_data = base64.b64decode(data["result"]["image"])
        return io.BytesIO(image_data)
      else:
        raise ValueError("No image data in the response")
    except Exception as e:
      logger.error(f"Error in _direct_generate_image: {e}")
      return "🤔 I encountered an issue while creating your image."

  def analyze_image(self, image: Union[io.BytesIO, bytes, str], prompt: str) -> str:
    return self.chat_completions(image, prompt)

  async def chat_completions(
    self,
    prompt: str = None,
    image: Union[io.BytesIO, bytes, str] = None,
    messages: Union[str, List[Dict[str, str]]] = None,
    temperature: float = 0.6,
    max_tokens: int = 2048,
  ) -> str:
    """
    Queue-based chat completions.
    """
    from services.queue_service import queue_service
    
    try:
      # Prepare request parameters
      params = {
        "prompt": prompt,
        "image": None,  # We'll handle image separately
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
      }
      
      ### Handle image if provided
      if image is not None:
        image_data = self._download_image(image)
        image_data = self._compress_image(image_data)
        params["image_data_uri"] = self._image_bytes_to_data_uri(image_data, mime_type="image/jpeg")
      
      req_id = await queue_service.add_to_queue({
        "type": "chat_completion",
        "params": params
      })
      
      result = await queue_service.get_result(req_id, timeout=60)
      
      if result["status"] == "success":
        return result["result"]
      elif result["status"] == "timeout":
        return "⏱️ Your request is taking longer than expected. Please try again later."
      else:
        return "🤔 I'm a bit confused. Can you rephrase that?"
            
    except Exception as e:
      logger.error(f"Error in queued chat_completions: {e}")
      return "😵 Oops! Something unexpected happened."

  def _direct_chat_completions(
    self,
    prompt: str = None,
    image_data_uri: str = None,
    messages: Union[str, List[Dict[str, str]]] = None,
    temperature: float = 0.6,
    max_tokens: int = 2048,
  ) -> str:
    """
    Direct chat completions (called by queue processor).
    """
    ### Build request payload
    if image_data_uri is not None:
      messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {
          "role": "user",
          "content": [
            {"type": "text", "text": prompt or "Describe this image."},
            {"type": "image_url", "image_url": {"url": image_data_uri}}
          ]
        }
      ]
      json_payload = {
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
      }
    elif messages is not None:
      if isinstance(messages, str):
        json_payload = {
          "messages": [{"role": "user", "content": messages}],
          "temperature": temperature,
          "max_tokens": max_tokens
        }
      else:
        json_payload = {
          "messages": messages, 
          "temperature": temperature,
          "max_tokens": max_tokens
        }
    elif prompt is not None:
      json_payload = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
      }
    else:
      return "⚠️ No input provided for completion."

    try:
      response = self._make_request(
        "POST",
        self.vision_language_model_endpoint,
        headers=self.headers,
        json=json_payload,
      )
      result = response.json()
      bot_response = str(result.get("result", {}).get("response", ""))
      return (
        bot_response
        if len(bot_response) != 0
        else "⚠️ Cloudflare Workers AI returned empty string."
      )
    except Exception as e:
      logger.error(f"Error in _direct_chat_completions: {e}")
      raise
