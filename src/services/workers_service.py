import io
import requests
import numpy as np
from PIL import Image
from utils.logger import logger
from typing import List, Dict, Union
from utils.config import (
  CF_WORKERS_MODEL_NAME,
  CF_WORKERS_IMAGE_MODEL_NAME,
  CLOUDFLARE_ACCOUNT_ID,
  CF_WORKERS_IMAGE_DESCRIPTION_MODEL_NAME,
  CLOUDFLARE_WORKERS_AI_API_KEY,
)


class WorkersService:
  """
  Service for interacting with language and image generation models.
  """

  def __init__(self) -> None:
    """
    Initialize the LLMService with necessary API endpoints and headers.
    """

    self.model_search_url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/models/search"
    self.model_inference_url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{CF_WORKERS_MODEL_NAME}"
    self.model_imagine_url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{CF_WORKERS_IMAGE_MODEL_NAME}"
    self.image_analysis_url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{CF_WORKERS_IMAGE_DESCRIPTION_MODEL_NAME}"
    self.headers = {"Authorization": f"Bearer {CLOUDFLARE_WORKERS_AI_API_KEY}"}
    self.timeout = 30  ### Timeout of 30s

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

  def _get_image_data(self, image: Union[io.BytesIO, bytes, str]) -> bytes:
    if isinstance(image, str):
      response = self._make_request("GET", image)
      return response.content
    elif isinstance(image, io.BytesIO):
      return image.getvalue()
    return image

  def _compress_image(self, image_data: bytes, max_size: int = 600 * 1024) -> bytes:
    if len(image_data) <= max_size:
      return image_data

    image = Image.open(io.BytesIO(image_data))
    image = image.convert("RGB")
    output = io.BytesIO()

    quality = 85
    while True:
      image.save(output, format="JPEG", quality=quality, optimize=True)
      if output.tell() <= max_size or quality <= 20:
        break
      quality -= 5
      output.seek(0)
      output.truncate()

    return output.getvalue()

  def chat_completions(self, messages: List[Dict[str, str]], temperature=0.55) -> str:
    json = {"messages": messages, "temperature": temperature}

    try:
      response = self._make_request(
        "POST", self.model_inference_url, headers=self.headers, json=json
      )
      result = response.json()
      bot_response = str(result["result"]["response"])
      return (
        bot_response
        if len(bot_response) != 0
        else "⚠️ Cloudflare Workers AI returned empty string."
      )
    except ConnectionError:
      return (
        "😔 Sorry, I'm having trouble connecting right now. Can you try again later?"
      )
    except KeyError as ke:
      logger.error("Unexpected API response format", ke)
      return "🤔 I'm a bit confused. Can you rephrase that?"
    except Exception as e:
      logger.error(f"Unexpected error in chat_completions: {e}")
      return "😵 Oops! Something unexpected happened."

  def generate_image(self, prompt: str) -> Union[io.BytesIO, str]:
    json = {"prompt": prompt}

    try:
      response = self._make_request(
        "POST", self.model_imagine_url, headers=self.headers, json=json
      )

      if response.headers.get("content-type") == "image/png":
        return io.BytesIO(response.content)
      else:
        error_data = response.json()
        error_message = error_data.get("errors", [{}])[0].get(
          "message", "Unknown error occurred"
        )
        raise ValueError(error_message)
    except ValueError as e:
      logger.error(f"Error processing the response: {e}")
      return "🤔 I encountered an issue while creating your image. Please try a different prompt or try again later."
    except Exception as e:
      logger.error(f"Unexpected error in generate_image: {e}")
      return "😵 Oops! Something unexpected happened while generating the image."

  def fetch_models(self) -> List[str]:
    try:
      response = self._make_request("GET", self.model_search_url, headers=self.headers)
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
    try:
      image_data = self._get_image_data(image)
      image_data = self._compress_image(image_data)

      input_data = {
        "image": np.frombuffer(image_data, dtype=np.uint8).tolist(),
        "prompt": prompt,
        "max_tokens": 512,
      }

      response = self._make_request(
        "POST", self.image_analysis_url, headers=self.headers, json=input_data
      )
      result = response.json()

      description = result.get("result", {}).get("description", "")
      return (
        description
        if description
        else "I couldn't analyze the image. Could you try uploading it again?"
      )
    except Exception as e:
      logger.error(f"Unexpected error in analyze_image: {e}")
      return "😵 Oops! Something unexpected happened while analyzing the image."
