import requests
from typing import Optional, Dict
from utils.logger import logger
from utils.config import DB_SERVICE_BASE_URL


class DBService:
  """
  Service for interacting with the database API.
  """

  def __init__(self):
    """
    Initialize the DBService with the base URL for the database API.
    """
    self.base_url = DB_SERVICE_BASE_URL
    self.timeout = 1  ### Timeout of 1s

  def fetch_prompt(self, guild_id: str) -> Optional[Dict[str, str]]:
    """
    Fetch a prompt for a given guild ID.

    Args:
      guild_id (str): The ID of the guild to fetch the prompt for.

    Returns:
      Optional[Dict[str, str]]: A dictionary containing the guild_id and system_prompt, or None if the request fails.
    """
    endpoint = f"http://{self.base_url}/prompt"
    params = {"guild_id": guild_id}

    try:
      response = requests.get(endpoint, params=params, timeout=self.timeout)

      if response.status_code == 404:
        logger.warning(f"No prompt found for guild {guild_id} (404)")
        return {"system_prompt": None}

      response.raise_for_status()
      return response.json()
    except requests.Timeout:
      logger.error(f"Timeout occurred while fetching prompt for guild {guild_id}")
    except requests.ConnectionError:
      logger.error(
        f"Connection error occurred while fetching prompt for guild {guild_id}"
      )
    except requests.RequestException as e:
      logger.error(f"Error fetching prompt for guild {guild_id}: {e}")
    except ValueError as e:
      logger.error(f"Error parsing JSON response for guild {guild_id}: {e}")

    return None

  def store_message(self, msg_payload: dict) -> Optional[Dict[str, str]]:
    endpoint = f"http://{self.base_url}/message"

    try:
      response = requests.post(endpoint, json=msg_payload, timeout=self.timeout)
      response.raise_for_status()
      return response.json()
    except requests.Timeout:
      logger.error("Timeout occurred while adding message")
    except requests.ConnectionError:
      logger.error("Connection error occurred while adding message")
    except requests.RequestException as _e:
      pass
    except ValueError as e:
      logger.error(f"Error parsing JSON response after adding message: {e}")

    return None

  def get_token_stats(self, guild_id: str, author_id: str, period: str = "daily") -> Optional[list]:
    endpoint = f"http://{self.base_url}/token/stats"
    params = {
      "guild_id": guild_id,
      "author_id": author_id,
      "period": period
    }
    
    try:
      response = requests.get(endpoint, params=params, timeout=self.timeout)
      
      if response.status_code == 404:
        logger.warning(f"No token stats found for user {author_id} in guild {guild_id}")
        return []
      
      response.raise_for_status()
      return response.json()
    except requests.Timeout:
      logger.error(f"Timeout occurred while fetching token stats for user {author_id}")
    except requests.ConnectionError:
      logger.error(f"Connection error occurred while fetching token stats for user {author_id}")
    except requests.RequestException as e:
      logger.error(f"Error fetching token stats for user {author_id}: {e}")
    except ValueError as e:
      logger.error(f"Error parsing JSON response for token stats: {e}")
    
    return None
  
  def store_token_usage(self, usage: dict) -> Optional[Dict[str, str]]:
    endpoint = f"http://{self.base_url}/token"
    try:
      response = requests.post(endpoint, json=usage, timeout=self.timeout)
      response.raise_for_status()
      print(response.json())
      return response.json()
    except requests.Timeout:
      logger.error("Timeout occurred while storing token usage")
    except requests.ConnectionError:
      logger.error("Connection error occurred while storing token usage")
    except requests.RequestException as _e:
      pass
    except ValueError as e:
      logger.error(f"Error parsing response after storing token usage: {e}")
    return None
