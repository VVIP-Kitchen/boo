package weather

import (
	"encoding/json"
	"fmt"
	"math"
	"net/http"
	"os"
	"time"
)

const baseURL = "https://api.tomorrow.io/v4/weather/realtime"

var SVC *WeatherService

// WeatherService handles weather-related operations
type WeatherService struct {
	apiKey string
	client *http.Client
}

// NewWeatherService creates a new WeatherService instance
func Setup() {
	SVC = &WeatherService{
		apiKey: os.Getenv("TOMORROW_IO_API_KEY"),
		client: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

// WeatherInfo fetches weather information for a given location
func (ws *WeatherService) WeatherInfo(location string) string {
	req, err := http.NewRequest("GET", baseURL, nil)
	if err != nil {
		return ws.formatErrorMessage(location)
	}

	q := req.URL.Query()
	q.Add("apikey", ws.apiKey)
	q.Add("location", location)
	req.URL.RawQuery = q.Encode()

	resp, err := ws.client.Do(req)
	if err != nil {
		return ws.formatErrorMessage(location)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return ws.formatErrorMessage(location)
	}

	var weatherResp WeatherResponse
	if err := json.NewDecoder(resp.Body).Decode(&weatherResp); err != nil {
		return ws.formatErrorMessage(location)
	}

	return ws.formatWeatherData(weatherResp)
}

func (ws *WeatherService) getWeatherDescription(weatherCode int) string {
	if desc, ok := weatherDescriptions[weatherCode]; ok {
		return desc
	}
	return "Unknown"
}

func (ws *WeatherService) getWindDirection(degrees float64) string {
	directions := []string{
		"N", "NNE", "NE", "ENE",
		"E", "ESE", "SE", "SSE",
		"S", "SSW", "SW", "WSW",
		"W", "WNW", "NW", "NNW",
	}
	index := int(math.Round(degrees/22.5)) % 16
	return directions[index]
}

func (ws *WeatherService) getPressureTrend(pressure float64) string {
	if pressure > 1020 {
		return "📈 High"
	} else if pressure > 1013 {
		return "➡️ Normal"
	}
	return "📉 Low"
}

func (ws *WeatherService) getVisibilityStatus(visibility float64) string {
	if visibility >= 10 {
		return "👁️ Excellent"
	} else if visibility >= 5 {
		return "👀 Good"
	} else if visibility >= 2 {
		return "😶‍🌫️ Moderate"
	}
	return "🌫️ Poor"
}

func (ws *WeatherService) getComfortLevel(temp, humidity float64) string {
	if temp < 10 {
		return "🧊 Cold"
	} else if temp > 30 {
		return "🔥 Hot"
	} else if humidity > 70 {
		return "💧 Humid"
	} else if temp >= 18 && temp <= 24 && humidity >= 40 && humidity <= 60 {
		return "😌 Comfortable"
	}
	return "🌡️ Moderate"
}

func (ws *WeatherService) formatWeatherData(data WeatherResponse) string {
	values := data.Data.Values
	locationInfo := data.Location

	// Extract all the rich data
	temp := values.Temperature
	tempApparent := values.TemperatureApparent
	humidity := values.Humidity
	windSpeed := values.WindSpeed
	windDirection := values.WindDirection
	windGust := values.WindGust
	precipProb := values.PrecipitationProbability
	pressure := values.PressureSeaLevel
	visibility := values.Visibility
	cloudCover := values.CloudCover
	dewPoint := values.DewPoint
	weatherCode := values.WeatherCode

	// Get descriptive information
	weatherEmoji := weatherCodeEmojis[weatherCode]
	if weatherEmoji == "" {
		weatherEmoji = "🌤️"
	}
	weatherDesc := ws.getWeatherDescription(weatherCode)
	windDir := ws.getWindDirection(windDirection)
	pressureTrend := ws.getPressureTrend(pressure)
	visibilityStatus := ws.getVisibilityStatus(visibility)
	comfortLevel := ws.getComfortLevel(temp, humidity)

	// Format location name
	locationName := locationInfo.Name
	if locationName == "" {
		locationName = "Unknown Location"
	}

	// Parse and format time
	formattedTime := "Unknown"
	if timeObj, err := time.Parse(time.RFC3339, data.Data.Time); err == nil {
		formattedTime = timeObj.UTC().Format("03:04 PM UTC")
	}

	// Create the stunning weather report
	weatherReport := fmt.Sprintf(`
╭─────────────────────────────────────╮
│  %s **LIVE WEATHER REPORT** %s  │
╰─────────────────────────────────────╯

📍 **%s**
🕐 **Updated:** `+"`%s`"+`
🌤️ **Conditions:** `+"`%s`"+`

╭─ **🌡️ TEMPERATURE** ─╮
│ **Current:** `+"`%.1f°C`"+`
│ **Feels Like:** `+"`%.1f°C`"+`
│ **Comfort:** %s
│ **Dew Point:** `+"`%.1f°C`"+`
╰─────────────────────╯

╭─ **💨 WIND & AIR** ─╮
│ **Speed:** `+"`%.1f km/h %s`"+`
│ **Gusts:** `+"`%.1f km/h`"+`
│ **Pressure:** `+"`%.1f mb`"+` %s
│ **Humidity:** `+"`%.0f%%`"+`
╰─────────────────────╯

╭─ **☁️ CONDITIONS** ─╮
│ **Cloud Cover:** `+"`%.0f%%`"+`
│ **Visibility:** `+"`%.1f km`"+` %s
│ **Rain Chance:** `+"`%.0f%%`"+`
╰─────────────────────╯

*Weather data refreshed automatically 🔄*`,
		weatherEmoji, weatherEmoji,
		locationName,
		formattedTime,
		weatherDesc,
		temp,
		tempApparent,
		comfortLevel,
		dewPoint,
		windSpeed, windDir,
		windGust,
		pressure, pressureTrend,
		humidity,
		cloudCover,
		visibility, visibilityStatus,
		precipProb,
	)

	return weatherReport
}

func (ws *WeatherService) formatErrorMessage(location string) string {
	return fmt.Sprintf(`
╭─────────────────────────────╮
│  ❌ **WEATHER ERROR** ❌  │
╰─────────────────────────────╯

📍 **Location:** `+"`%s`"+`

⚠️ **Unable to fetch weather data**

**Possible reasons:**
• Invalid location name
• API service temporarily unavailable
• Network connectivity issues

*Please try again with a valid location! 🌍*`, location)
}
