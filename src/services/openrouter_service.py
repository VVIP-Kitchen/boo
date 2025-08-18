import requests
from utils.logger import logger
from utils.config import OPENROUTER_API_KEY

class OpenRouterService:
  def __init__(self):
    self.endpoint = "https://openrouter.ai/api/v1/key"
    self.api_key = OPENROUTER_API_KEY
  
  def get_status(self):
    headers = {
      "Authorization": f"Bearer {self.api_key}",
      "Accept": "application/json"
    }

    try:
      response = requests.get(self.endpoint, headers=headers)
      if response.status_code == 200:
        data = response.json()
        return self._format_key_status_as_markdown(data.get("data", {}))
    except Exception as e:
      logger.error(f"OpenRouterService get_status error: {e}")
      return {
        "error": "😵 Unexpected error while getting OpenRouter status"
      }
  
  def _format_key_status_as_markdown(self, info: dict) -> str:
    # Defensive defaults
    label = info.get("label", "N/A")
    usd_limit   = info.get("limit")
    usage      = info.get("usage", 0)
    remaining  = info.get("limit_remaining")
    is_provisioning = info.get("is_provisioning_key", False)
    is_free        = info.get("is_free_tier", False)
    rl = info.get("rate_limit", {"requests": "?", "interval": "?"})

    def usd(x):
      # Format only if it's not None, else show a placeholder
      if x is None:
        return "Unlimited"  # or "N/A" if you prefer
      try:
        return f"${float(x):,.4f}"
      except Exception:
        return "N/A"

    embed = [
      "**OpenRouter API Key Status**",
      f"**Key:** `{label}`",
      f"**Provisioning Key:** {'✅' if is_provisioning else '❌'}",
      f"**Free Tier:** {'✅' if is_free else '❌'}",
      "",
      f"**Credits Used:** {usd(usage)} / {usd(usd_limit)}",
      f"**Credits Remaining:** {usd(remaining)}",
      "",
      f"**Rate Limit:** `{rl.get('requests', '?')}` requests / `{rl.get('interval', '?')}`",
    ]
    return "\n".join(embed)

  def _as_markdown_error(self, msg: str) -> str:
    return f"**OpenRouter API Key Status**\n\n> {msg}"
