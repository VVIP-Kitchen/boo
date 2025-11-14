package weather

var weatherCodeEmojis = map[int]string{
	1000: "☀️", // Clear
	1001: "🌤️", // Cloudy
	1100: "🌤️", // Mostly Clear
	1101: "⛅",  // Partly Cloudy
	1102: "☁️", // Mostly Cloudy
	2000: "🌫️", // Fog
	2100: "🌫️", // Light Fog
	4000: "🌦️", // Drizzle
	4001: "🌧️", // Rain
	4200: "🌧️", // Light Rain
	4201: "🌧️", // Heavy Rain
	5000: "❄️", // Snow
	5001: "🌨️", // Flurries
	5100: "🌨️", // Light Snow
	5101: "❄️", // Heavy Snow
	6000: "🌨️", // Freezing Drizzle
	6001: "🧊",  // Freezing Rain
	6200: "🧊",  // Light Freezing Rain
	6201: "🧊",  // Heavy Freezing Rain
	7000: "🌨️", // Ice Pellets
	7101: "🌨️", // Heavy Ice Pellets
	7102: "🌨️", // Light Ice Pellets
	8000: "⛈️", // Thunderstorm
}

var weatherDescriptions = map[int]string{
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

// WeatherResponse represents the API response structure
type WeatherResponse struct {
	Data struct {
		Time   string `json:"time"`
		Values struct {
			Temperature              float64 `json:"temperature"`
			TemperatureApparent      float64 `json:"temperatureApparent"`
			Humidity                 float64 `json:"humidity"`
			WindSpeed                float64 `json:"windSpeed"`
			WindDirection            float64 `json:"windDirection"`
			WindGust                 float64 `json:"windGust"`
			PrecipitationProbability float64 `json:"precipitationProbability"`
			PressureSeaLevel         float64 `json:"pressureSeaLevel"`
			Visibility               float64 `json:"visibility"`
			CloudCover               float64 `json:"cloudCover"`
			DewPoint                 float64 `json:"dewPoint"`
			WeatherCode              int     `json:"weatherCode"`
		} `json:"values"`
	} `json:"data"`
	Location struct {
		Name string `json:"name"`
	} `json:"location"`
}

type WeatherInput struct {
	Location string `json:"location" jsonschema_description:"The location to get weather for"`
}
