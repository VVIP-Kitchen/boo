import io
import requests
import numpy as np
from PIL import Image
from utils.logger import logger
from typing import List, Dict, Union
from utils.config import (
  MODEL_NAME,
  IMAGE_MODEL_NAME,
  CLOUDFLARE_ACCOUNT_ID,
  IMAGE_DESCRIPTION_MODEL_NAME,
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
    self.model_inference_url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{MODEL_NAME}"
    self.model_imagine_url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{IMAGE_MODEL_NAME}"
    self.image_analysis_url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{IMAGE_DESCRIPTION_MODEL_NAME}"
    self.headers = {"Authorization": f"Bearer {CLOUDFLARE_WORKERS_AI_API_KEY}"}

  def chat_completions(self, messages: List[Dict[str, str]], temperature=0.55) -> str:
    """
    Call the language model with given messages.

    Args:
      messages (List[Dict[str, str]]): List of message dictionaries.

    Returns:
      str: The model's response.
    """

    json = {"messages": messages, "temperature": temperature}
    bot_response = ""

    try:
      response = requests.post(
        self.model_inference_url, headers=self.headers, json=json
      )
      result = response.json()
      bot_response = str(result["result"]["response"])
      bot_response = (
        bot_response
        if len(bot_response) != 0
        else "⚠️ Cloudflare Workers AI returned empty string."
      )
    except requests.RequestException as e:
      logger.error(f"API request failed: {e}")
      bot_response = (
        "😔 Sorry, I'm having trouble thinking right now. Can you try again later?"
      )
    except KeyError as ke:
      logger.error("Unexpected API response format", ke)
      bot_response = "🤔 I'm a bit confused. Can you rephrase that?"

    return bot_response

  def generate_image(self, prompt: str) -> Union[io.BytesIO, str]:
    """
    Generate an image based on the given prompt.

    Args:
        prompt (str): The prompt for image generation.

    Returns:
        Union[io.BytesIO, str]: BytesIO object of the generated image or error message.
    """

    json = {"prompt": prompt}

    try:
      response = requests.post(self.model_imagine_url, headers=self.headers, json=json)
      response.raise_for_status()

      if response.headers.get("content-type") == "image/png":
        return io.BytesIO(response.content)
      else:
        error_data = response.json()
        if "errors" in error_data and error_data["errors"]:
          error_message = error_data["errors"][0].get(
            "message", "Unknown error occurred"
          )
        else:
          error_message = "Unexpected response format"
        raise ValueError(error_message)
    except requests.RequestException as e:
      logger.error(f"API request failed: {e}")
      return "😔 Sorry, I'm having trouble generating the image right now. Can you try again later?"
    except ValueError as e:
      logger.error(f"Error processing the response: {e}")
      return "🤔 I encountered an issue while creating your image. Please try a different prompt or try again later."
    except Exception as e:
      logger.error(f"Unexpected error: {e}")
      return "😵 Oops! Something unexpected happened."

  def fetch_models(self) -> List[str]:
    """
    Fetch available models from the API.

    Returns:
        List[str]: List of available model names.
    """

    models = []

    try:
      response = requests.get(self.model_search_url, headers=self.headers)
      result = response.json()

      for obj in result["result"]:
        if obj["task"]["name"] == "Text Generation":
          models.append(obj["name"])
    except Exception as e:
      logger.error(str(e))

    return models

  def analyze_image(self, image: Union[io.BytesIO, bytes], prompt: str):
    """
    Analyze an image based on the given prompt.

    Args:
        image (Union[io.BytesIO, bytes]): The image to analyze.
        prompt (str): The prompt for image analysis.

    Returns:
        str: The analysis result or error message.
    """
    try:
      ### If image is a URL, fetch it
      if isinstance(image, str):
        image_response = requests.get(image)
        image_response.raise_for_status()
        image_data = image_response.content
      else:
        image_data = image

      if len(image_data) > 600 * 1024:
        ### Compress image to 600KB
        image = Image.open(io.BytesIO(image_data))
        image = image.convert("RGB")
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=85, optimize=True)
        image_data = output.getvalue()

      image_array = np.frombuffer(image_data, dtype=np.uint8).tolist()
      input_data = {
        "image": image_array,
        "prompt": prompt,
        "max_tokens": 512,
      }

      response = requests.post(
        self.image_analysis_url, headers=self.headers, json=input_data
      )
      response.raise_for_status()

      result = response.json()
      if len(result.get("result", "")) != 0:
        description = result.get("result")
        return description.get(
          "description",
          "I couldn't analyze the image. Could you try uploading it again?",
        )
      else:
        return "I couldn't analyze the image. Could you try uploading it again?"

    except requests.RequestException as e:
      logger.error(f"API request failed: {e}")
      return "😔 Sorry, I'm having trouble analyzing the image right now. Can you try again later?"

    except Exception as e:
      logger.error(f"Unexpected error: {e}")
      return "😵 Oops! Something unexpected happened while analyzing the image."
