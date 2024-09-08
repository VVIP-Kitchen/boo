import requests
from utils.logger import logger
from utils.config import TENOR_API_KEY


class TenorService:
  """
  Service for interacting with Tenor APIs
  """

  def __init__(self) -> None:
    """
    Initialize the Tenor API
    """

    self.base_search_url = "https://tenor.googleapis.com/v2/search?q="
    self.search_query = "bonk"
    self.search_results_limit = 50

  def search(self, query=None):
    if query is not None:
      self.search_query = query

    try:
      api_url = (
        self.base_search_url
        + self.search_query
        + "&key="
        + TENOR_API_KEY
        + "&limit="
        + str(self.search_results_limit)
      )
      response = requests.get(api_url)
      result = response.json()
      return list(result["results"])
    except requests.RequestException as e:
      logger.error(f"API request failed: {e}")
      return []
