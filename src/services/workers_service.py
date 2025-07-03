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

  def generate_image(self, prompt: str, num_steps: int = 4) -> Union[io.BytesIO, str]:
    json_data = {
      "prompt": prompt,
      "num_steps": min(max(num_steps, 1), 8)
    }

    try:
      response = self._make_request(
        "POST", self.image_generation_model_endpoint, headers=self.headers, json=json_data
      )
      response.raise_for_status()
      data = response.json()

      if "image" in data["result"]:
        image_data = base64.b64decode(data["result"]["image"])
        return io.BytesIO(image_data)
      else:
        raise ValueError("No image data in the response")
    except requests.exceptions.RequestException as e:
      logger.error(f"Error making request to Cloudflare API: {e}")
      return "🤔 I encountered an issue while creating your image. Please try a different prompt or try again later."
    except ValueError as e:
      logger.error(f"Error processing the response: {e}")
      return "🤔 I encountered an issue while creating your image. Please try a different prompt or try again later."
    except Exception as e:
      logger.error(f"Unexpected error in generate_image: {e}")
      return "😵 Oops! Something unexpected happened while generating the image."

  def fetch_models(self) -> List[str]:
    try:
      response = self._make_request("GET", self.search_models_endpoint, headers=self.headers)
      result = response.json()
      return [
        obj["name"]
        for obj in result["result"]
        if obj["task"]["name"] == "Text Generation"
      ]
    except Exception as e:
      logger.error(f"Unexpected error in fetch_models: {e}")
      return []

  def analyze_image(self, image: Union[io.BytesIO, bytes, str], prompt: str) -> str:
    return self.chat_completions(image, prompt)

  def chat_completions(
    self,
    prompt: str = None,
    image: Union[io.BytesIO, bytes, str] = None,
    messages: Union[str, List[Dict[str, str]]] = None,
    temperature: float = 0.55,
    max_tokens: int = 512,
  ) -> str:
    """
    Unified function for both text and image+prompt requests.
    """
    # If image is provided, use image+prompt format
    if image is not None:
      image_data = self._download_image(image)
      image_data = self._compress_image(image_data)
      data_uri = self._image_bytes_to_data_uri(image_data, mime_type="image/jpeg")
      
      messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {
          "role": "user",
          "content": [
            {"type": "text", "text": prompt or "Describe this image."},
            {
              "type": "image_url", 
              "image_url": {"url": data_uri}
            }
          ]
        }
      ]
      json_payload = {
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
      }
    # For regular chat messages
    elif messages is not None:
      if isinstance(messages, str):
        # Convert string to proper messages format
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
    # For simple prompt
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
    except ConnectionError:
      return "😔 Sorry, I'm having trouble connecting right now. Can you try again later?"
    except KeyError as ke:
      logger.error(f"Unexpected API response format: {ke}")
      return "🤔 I'm a bit confused. Can you rephrase that?"
    except Exception as e:
      logger.error(f"Unexpected error in chat_completions: {e}")
      logger.error(f"Request payload: {json_payload}")
      return "😵 Oops! Something unexpected happened."
