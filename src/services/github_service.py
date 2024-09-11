import requests
from typing import List, Dict
from utils.logger import logger
from utils.config import GITHUB_TOKEN, GH_MODEL_NAME


class GithubService:
  """
  Service for interacting with language models provided by GitHub.
  """

  def __init__(self) -> None:
    self.chat_completions_url = "https://models.inference.ai.azure.com/chat/completions"
    self.headers = {
      "Content-Type": "application/json",
      "Authorization": f"Bearer {GITHUB_TOKEN}",
    }
    self.timeout = 30

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

  def chat_completions(self, messages: List[Dict[str, str]]) -> str:
    json = {"messages": messages, "model": GH_MODEL_NAME}

    try:
      response = self._make_request(
        "POST", self.chat_completions_url, headers=self.headers, json=json
      )
      result = response.json()
      bot_response = result["choices"][0]["message"]["content"]
      return (
        bot_response
        if len(bot_response) != 0
        else "⚠️ GitHub Models returned an empty string."
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
