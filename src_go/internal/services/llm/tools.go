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
	generateImageTool := genkit.DefineTool(g.gk, "generateImage", "Generates an image based on a text prompt and aspect ratio.", func(ctx *ai.ToolContext, imageInput ImageGenInput) (string, error) {
		_, err := g.CreateOrEditImage(ctx, imageInput.Prompt, imageInput.AspectRatio)
		if err != nil {
			return "", err
		}
		return "Image generated successfully.", nil
	})

	g.tools = []ai.ToolRef{weatherTool, generateImageTool}
}
