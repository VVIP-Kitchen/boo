package llm

import (
	"boo/internal/services/weather"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

func (g *GenKitService) defineTools() {
	weatherTool := genkit.DefineTool(g.gk, "getWeather", "Fetches the weather for a given city or location.", func(ctx *ai.ToolContext, weatherInput weather.WeatherInput) (string, error) {
		weatherService := weather.SVC.WeatherInfo(weatherInput.Location)
		return weatherService, nil
	})
	g.tools = []ai.ToolRef{weatherTool}
}
