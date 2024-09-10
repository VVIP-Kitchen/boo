import requests
from utils.logger import logger
from utils.config import TOMORROW_IO_API_KEY


class ApiService:
  def __init__(self):
    self.weather_info_url = (
      f"https://api.tomorrow.io/v4/weather/realtime?apikey={TOMORROW_IO_API_KEY}"
    )

  def weather_info(self, location: str) -> str:
    """
    Fetch weather information for a given location.

    Args:
        location (str): The location for weather information.

    Returns:
        str: The weather information or error message.
    """
    # try:

    response = requests.get(f"{self.weather_info_url}&location={location}")
    if response.status_code != 200:
      logger.error(f"API request failed with status code {response.status_code}")
      return f"Error: Unable to fetch weather data for {location}"
    data = response.json()

    # if "data" not in data:
    #         return f"Error: Unable to fetch weather data for {location}"

    values = data["data"]["values"]
    temperature = values.get("temperature", "N/A")
    humidity = values.get("humidity", "N/A")
    wind_speed = values.get("windSpeed", "N/A")
    precipitation_probability = values.get("precipitationProbability", "N/A")

    return (
      f"## Weather in {location}:\n"
      f"Temperature: {temperature}°C\n"
      f"Humidity: {humidity}%\n"
      f"Wind Speed: {wind_speed} km/h\n"
      f"Precipitation Probability: {precipitation_probability}%"
    )

    # except requests.RequestException as e:
    #     logger.error(f"API request failed: {e}")
    #     return "😔 Sorry, I'm having trouble fetching the weather information right now. Can you try again later?"
    # except Exception as e:
    #     logger.error(f"Unexpected error: {e}")
    #     return "😵 Oops! Something unexpected happened while fetching the weather information."
