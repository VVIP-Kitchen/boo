import os
import sys
import requests
from utils.logger import logger
from typing import List, Dict, Optional
from requests.exceptions import RequestException, Timeout
from tenacity import retry, stop_after_attempt, wait_exponential


class DiscourseService:
  @staticmethod
  def _get_env_var(var_name: str) -> str:
    """Retrieve an environment variable or exit if it's missing."""
    try:
      return os.environ[var_name]
    except KeyError:
      logger.error(f"Environment variable {var_name} is missing")
      sys.exit(1)

  def __init__(self) -> None:
    self.cookie = self._get_env_var("DISCOURSE_COOKIE")
    self.csrf_token = self._get_env_var("DISCOURSE_CSRF_TOKEN")
    self.base_url = "https://discourse.onlinedegree.iitm.ac.in"
    self.search_url = f"{self.base_url}/search"
    self.headers = {
      "Cookie": self.cookie,
      "x-csrf-token": self.csrf_token,
      "X-Requested-With": "XMLHttpRequest",
      "Accept": "application/json, text/javascript, */*; q=0.01",
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }

  @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
  def _make_request(
    self, url: str, params: Optional[Dict[str, str]] = None
  ) -> Optional[Dict]:
    """Make a GET request with retry logic."""
    try:
      response = requests.get(url, headers=self.headers, params=params, timeout=10)
      response.raise_for_status()
      return response.json()
    except Timeout:
      logger.error("Request timed out")
      raise None
    except RequestException as e:
      logger.error(f"Request failed: {str(e)}")
      raise None

  def discourse_search(
    self, search_keyword: str, max_pages: int = 20
  ) -> List[Dict[str, str]]:
    """
    Search Discourse and return results.
    """
    results = []
    page = 1

    while page <= max_pages:
      params = {"q": search_keyword, "page": str(page)}

      try:
        data = self._make_request(self.search_url, params)
      except Exception as e:
        logger.error(f"Search failed on page {page}: {str(e)}")
        break

      topics = data.get("topics", [])
      if not topics:
        break
      posts = data.get("posts", [])
      blurb_dict = {post["topic_id"]: post["blurb"] for post in posts}

      for topic in topics:
        if topic.get("has_accepted_answer"):
          topic_id = topic["id"]
          results.append(
            {
              "id": str(topic_id),
              "Title": topic["title"],
              "Tags": ", ".join(topic.get("tags", [])),
              "Post Link": f"{self.base_url}/t/{topic['slug']}/{topic['id']}",
              "Blurb": blurb_dict.get(topic_id, "No blurb available"),
            }
          )

      page += 1

    return results
