import requests
from typing import Dict, Any
from utils.logger import logger
from utils.config import TOMORROW_IO_API_KEY


class WeatherService:
  BASE_URL = "https://api.tomorrow.io/v4/weather/realtime"

  def __init__(self):
    self.session = requests.Session()
    self.session.params = {"apikey": TOMORROW_IO_API_KEY}

  def weather_info(self, location: str) -> str:
    """
    Fetch weather information for a given location.

    Args:
        location (str): The location for weather information.

    Returns:
        str: The weather information or error message.
    """
    try:
      response = self.session.get(self.BASE_URL, params={"location": location})
      response.raise_for_status()
      data = response.json()
      return self._format_weather_data(location, data["data"]["values"])
    except requests.RequestException as e:
      logger.error(f"API request failed: {str(e)}")
      return f"Error: Unable to fetch weather data for {location}"

  def _format_weather_data(self, location: str, values: Dict[str, Any]) -> str:
    """
    Format the weather data into a readable string.

    Args:
        location (str): The location of the weather data.
        values (Dict[str, Any]): The weather data values.

    Returns:
        str: Formatted weather information.
    """
    weather_info = [
      f"## Weather in {location}:",
      f"Temperature: {values.get('temperature', 'N/A')}°C",
      f"Humidity: {values.get('humidity', 'N/A')}%",
      f"Wind Speed: {values.get('windSpeed', 'N/A')} km/h",
      f"Precipitation Probability: {values.get('precipitationProbability', 'N/A')}%",
    ]
    return "\n".join(weather_info)
