import requests
import io
from utils.logger import logger
from utils.config import (
  MODEL_NAME,
  IMAGE_MODEL_NAME,
  CLOUDFLARE_ACCOUNT_ID,
  CLOUDFLARE_WORKERS_AI_API_KEY,
)


class LLMService:
  def __init__(self):
    self.model_inference_url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{MODEL_NAME}"
    self.model_imagine_url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{IMAGE_MODEL_NAME}"
    self.model_search_url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/models/search"
    self.headers = {"Authorization": f"Bearer {CLOUDFLARE_WORKERS_AI_API_KEY}"}

  def call_model(self, messages):
    json = {"messages": messages}
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
        else "⚠️ Cloudflare Workers AI returned empty string. Change model maybe!"
      )
    except requests.RequestException as e:
      logger.error(f"API request failed: {e}")
      bot_response = (
        "😔 Sorry, I'm having trouble thinking right now. Can you try again later?"
      )
    except KeyError:
      logger.error("Unexpected API response format")
      bot_response = "🤔 I'm a bit confused. Can you rephrase that?"

    return bot_response

  def generate_image(self, prompt):
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

  def fetch_models(self):
    models = []

    try:
      response = requests.get(self.model_search_url, headers=self.headers)
      result = response.json()

      for obj in result["result"]:
        if "meta" in obj["name"]:
          models.append(obj["name"])
    except Exception as e:
      logger.error(str(e))

    return models
