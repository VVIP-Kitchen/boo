import requests
from typing import Dict, Any
from datetime import datetime
from utils.logger import logger
from utils.config import TOMORROW_IO_API_KEY


class WeatherService:
  BASE_URL = "https://api.tomorrow.io/v4/weather/realtime"

  # Weather condition emojis based on weather codes
  WEATHER_CODE_EMOJIS = {
    1000: "☀️",  # Clear
    1001: "🌤️",  # Cloudy
    1100: "🌤️",  # Mostly Clear
    1101: "⛅",  # Partly Cloudy
    1102: "☁️",  # Mostly Cloudy
    2000: "🌫️",  # Fog
    2100: "🌫️",  # Light Fog
    4000: "🌦️",  # Drizzle
    4001: "🌧️",  # Rain
    4200: "🌧️",  # Light Rain
    4201: "🌧️",  # Heavy Rain
    5000: "❄️",  # Snow
    5001: "🌨️",  # Flurries
    5100: "🌨️",  # Light Snow
    5101: "❄️",  # Heavy Snow
    6000: "🌨️",  # Freezing Drizzle
    6001: "🧊",  # Freezing Rain
    6200: "🧊",  # Light Freezing Rain
    6201: "🧊",  # Heavy Freezing Rain
    7000: "🌨️",  # Ice Pellets
    7101: "🌨️",  # Heavy Ice Pellets
    7102: "🌨️",  # Light Ice Pellets
    8000: "⛈️",  # Thunderstorm
  }

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
      return self._format_weather_data(data)
    except requests.RequestException as e:
      logger.error(f"API request failed: {str(e)}")
      return self._format_error_message(location)

  def _get_weather_description(self, weather_code: int) -> str:
    """Get weather description based on weather code."""
    weather_descriptions = {
      1000: "Clear Sky",
      1001: "Cloudy",
      1100: "Mostly Clear",
      1101: "Partly Cloudy",
      1102: "Mostly Cloudy",
      2000: "Fog",
      2100: "Light Fog",
      4000: "Drizzle",
      4001: "Rain",
      4200: "Light Rain",
      4201: "Heavy Rain",
      5000: "Snow",
      5001: "Flurries",
      5100: "Light Snow",
      5101: "Heavy Snow",
      6000: "Freezing Drizzle",
      6001: "Freezing Rain",
      6200: "Light Freezing Rain",
      6201: "Heavy Freezing Rain",
      7000: "Ice Pellets",
      7101: "Heavy Ice Pellets",
      7102: "Light Ice Pellets",
      8000: "Thunderstorm",
    }
    return weather_descriptions.get(weather_code, "Unknown")

  def _get_wind_direction(self, degrees: float) -> str:
    """Convert wind direction degrees to compass direction."""
    directions = [
      "N",
      "NNE",
      "NE",
      "ENE",
      "E",
      "ESE",
      "SE",
      "SSE",
      "S",
      "SSW",
      "SW",
      "WSW",
      "W",
      "WNW",
      "NW",
      "NNW",
    ]
    index = round(degrees / 22.5) % 16
    return directions[index]

  def _get_pressure_trend(self, pressure: float) -> str:
    """Get pressure indicator."""
    if pressure > 1020:
      return "📈 High"
    elif pressure > 1013:
      return "➡️ Normal"
    else:
      return "📉 Low"

  def _get_visibility_status(self, visibility: float) -> str:
    """Get visibility status."""
    if visibility >= 10:
      return "👁️ Excellent"
    elif visibility >= 5:
      return "👀 Good"
    elif visibility >= 2:
      return "😶‍🌫️ Moderate"
    else:
      return "🌫️ Poor"

  def _get_comfort_level(self, temp: float, humidity: float) -> str:
    """Determine comfort level based on temperature and humidity."""
    if temp < 10:
      return "🧊 Cold"
    elif temp > 30:
      return "🔥 Hot"
    elif humidity > 70:
      return "💧 Humid"
    elif 18 <= temp <= 24 and 40 <= humidity <= 60:
      return "😌 Comfortable"
    else:
      return "🌡️ Moderate"

  def _format_weather_data(self, data: Dict[str, Any]) -> str:
    """
    Format the weather data into a beautiful Discord-friendly string.

    Args:
        data (Dict[str, Any]): The complete API response data.

    Returns:
        str: Formatted weather information.
    """
    values = data["data"]["values"]
    location_info = data["location"]

    # Extract all the rich data
    temp = values.get("temperature", 0)
    temp_apparent = values.get("temperatureApparent", temp)
    humidity = values.get("humidity", 0)
    wind_speed = values.get("windSpeed", 0)
    wind_direction = values.get("windDirection", 0)
    wind_gust = values.get("windGust", 0)
    precip_prob = values.get("precipitationProbability", 0)
    pressure = values.get("pressureSeaLevel", 0)
    visibility = values.get("visibility", 0)
    cloud_cover = values.get("cloudCover", 0)
    dew_point = values.get("dewPoint", 0)
    weather_code = values.get("weatherCode", 1000)

    # Get descriptive information
    weather_emoji = self.WEATHER_CODE_EMOJIS.get(weather_code, "🌤️")
    weather_desc = self._get_weather_description(weather_code)
    wind_dir = self._get_wind_direction(wind_direction)
    pressure_trend = self._get_pressure_trend(pressure)
    visibility_status = self._get_visibility_status(visibility)
    comfort_level = self._get_comfort_level(temp, humidity)

    # Format location name
    location_name = location_info.get("name", "Unknown Location")

    # Parse and format time
    time_str = data["data"].get("time", "")
    try:
      time_obj = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
      formatted_time = time_obj.strftime("%I:%M %p UTC")
    except Exception as _e:
      formatted_time = "Unknown"

    # Create the stunning weather report
    weather_report = f"""
╭─────────────────────────────────────╮
│  {weather_emoji} **LIVE WEATHER REPORT** {weather_emoji}  │
╰─────────────────────────────────────╯

📍 **{location_name}**
🕐 **Updated:** `{formatted_time}`
🌤️ **Conditions:** `{weather_desc}`

╭─ **🌡️ TEMPERATURE** ─╮
│ **Current:** `{temp}°C`
│ **Feels Like:** `{temp_apparent}°C`
│ **Comfort:** {comfort_level}
│ **Dew Point:** `{dew_point}°C`
╰─────────────────────╯

╭─ **💨 WIND & AIR** ─╮
│ **Speed:** `{wind_speed} km/h {wind_dir}`
│ **Gusts:** `{wind_gust} km/h`
│ **Pressure:** `{pressure:.1f} mb` {pressure_trend}
│ **Humidity:** `{humidity}%`
╰─────────────────────╯

╭─ **☁️ CONDITIONS** ─╮
│ **Cloud Cover:** `{cloud_cover}%`
│ **Visibility:** `{visibility} km` {visibility_status}
│ **Rain Chance:** `{precip_prob}%`
╰─────────────────────╯

*Weather data refreshed automatically 🔄*
        """.strip()

    return weather_report

  def _format_error_message(self, location: str) -> str:
    """Format error message in a Discord-friendly way."""
    return f"""
╭─────────────────────────────╮
│  ❌ **WEATHER ERROR** ❌  │
╰─────────────────────────────╯

📍 **Location:** `{location}`

⚠️ **Unable to fetch weather data**

**Possible reasons:**
• Invalid location name
• API service temporarily unavailable
• Network connectivity issues

*Please try again with a valid location! 🌍*
        """
