import requests
from utils.logger import logger
from utils.config import OPENROUTER_API_KEY


class OpenRouterService:
  def __init__(self):
    self.endpoint = "https://openrouter.ai/api/v1/key"
    self.api_key = OPENROUTER_API_KEY

  def get_status(self):
    headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}

    try:
      response = requests.get(self.endpoint, headers=headers)
      if response.status_code == 200:
        data = response.json()
        return self._format_key_status_as_markdown(data.get("data", {}))
    except Exception as e:
      logger.error(f"OpenRouterService get_status error: {e}")
      return {"error": "😵 Unexpected error while getting OpenRouter status"}

  def _format_key_status_as_markdown(self, info: dict) -> str:
    label = info.get("label", "N/A")
    usage = info.get("usage", 0)
    rl = info.get("rate_limit", {"requests": "?", "interval": "?"})

    def usd(x):
      if x is None:
        return "No limits!"
      try:
        return f"${float(x):,.4f}"
      except Exception:
        return "N/A"

    embed = [
      "# `OpenRouter Usage`",
      f"Key: `{label}`",
      f"Credits Used: `{usd(usage)}`",
      f"Rate Limit: `{rl.get('requests', '?')}` requests per `{rl.get('interval', '?')}`",
    ]
    return "\n".join(embed)
