package llm

import (
	"boo/internal/services/tenor"
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

	// Defining the tenor search tool
	tenorTool := genkit.DefineTool(g.gk, "searchGif", "Searches for a GIF based on a query.", func(ctx *ai.ToolContext, queryInput tenor.TenorSearchInput) (any, error) {
		result, err := tenor.SVC.Search(queryInput.Query)
		if err != nil {
			return nil, err
		}
		return result, nil
	})

	g.tools = []ai.ToolRef{weatherTool, generateImageTool, tenorTool}
}
