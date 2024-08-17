import requests
import io
from utils.logger import logger
from utils.config import (
  MODEL_NAME,
  CLOUDFLARE_ACCOUNT_ID,
  CLOUDFLARE_WORKERS_AI_API_KEY,
)


class LLMService:
  def __init__(self):
    self.model_inference_url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{MODEL_NAME}"
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

  def generate_image(self, payload):
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/bytedance/stable-diffusion-xl-lightning"
    headers = {
      "Authorization": f"Bearer {CLOUDFLARE_WORKERS_AI_API_KEY}",
      "Content-Type": "application/json",
    }
    json = {"payload": payload}
    bot_response = ""

    try:
      response = requests.post(url, headers=headers, json=json)
      raw_bytes = response.content
      bot_response = io.BytesIO(raw_bytes)
      bot_response = (
        bot_response
        if len(bot_response) != 0
        else "⚠️ Cloudflare Workers AI returned empty string. Change model maybe!"
      )
    except requests.RequestException as e:
      print(f"API request failed: {e}")
      bot_response = (
        "😔 Sorry, I'm having trouble thinking right now. Can you try again later?"
      )
    except KeyError:
      print("Unexpected API response format")
      bot_response = "🤔 I'm a bit confused. Can you rephrase that?"

    return bot_response

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
