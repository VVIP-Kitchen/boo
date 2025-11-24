package llm

import (
	"boo/internal/services/weather"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

func (g *GenKitService) defineTools() {

	// Defining the weather tool
	weatherTool := genkit.DefineTool(g.gk, "getWeather", "Fetches the weather for a given city or location.", func(ctx *ai.ToolContext, weatherInput weather.WeatherInput) (string, error) {
		weatherService := weather.SVC.WeatherInfo(weatherInput.Location)
		return weatherService, nil
	})

	// Defining the generateImage tool
	generateImageTool := genkit.DefineTool(g.gk, "generateImage", "Generates an image based on a text prompt and aspect ratio.", func(ctx *ai.ToolContext, imageInput ImageGenInput) (*ImageResult, error) {
		result, err := g.GenerateImage(ctx, imageInput.Prompt, imageInput.AspectRatio)
		if err != nil {
			return nil, err
		}
		return result, nil
	})

	g.tools = []ai.ToolRef{weatherTool, generateImageTool}
}
