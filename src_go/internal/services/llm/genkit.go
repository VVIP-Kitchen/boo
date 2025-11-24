package llm

import (
	"boo/internal/services/weather"
	"context"
	"fmt"
	"os"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/compat_oai"
)

var LLM *GenKitService

func Setup(ctx context.Context) {
	APIKey, ok := os.LookupEnv("OPENROUTER_API_KEY")
	if !ok {
		panic("OPENROUTER_API_KEY not set in environment")
	}
	Model, ok := os.LookupEnv("OPENROUTER_MODEL")
	if !ok {
		panic("OPENROUTER_MODEL not set in environment")
	}

	gk := genkit.Init(ctx, genkit.WithPlugins(&compat_oai.OpenAICompatible{
		BaseURL:  "https://openrouter.ai/api/v1",
		APIKey:   APIKey,
		Provider: "openrouter",
	}), genkit.WithDefaultModel("openrouter/"+Model))

	LLM = &GenKitService{gk: gk, provider: "openrouter"}

	// Initialing tool services
	weather.Setup()

	// Defining tools
	LLM.defineTools()
}

func convertMessages(messages []map[string]string) []*ai.Message {
	var result []*ai.Message
	for _, m := range messages {
		role := ai.Role(m["role"]) // e.g., "user", "system", "model"
		text := m["content"]

		part := &ai.Part{
			Text: text,
		}

		msg := &ai.Message{
			Role:    role,
			Content: []*ai.Part{part},
		}
		result = append(result, msg)
	}
	return result
}

func (g *GenKitService) ChatCompletion(ctx context.Context, messages []map[string]string) (string, error) {

	resp, err := genkit.Generate(ctx, g.gk,
		ai.WithMessages(convertMessages(messages)...),
		ai.WithTools(g.tools...),
	)

	if err != nil {
		return "", err
	}

	return resp.Message.Text(), nil
}

func (g *GenKitService) CreateOrEditImage(ctx context.Context, prompt string, aspectRatio string) (string, error) {

	// checking if image_bytes is nil or not
	messages := ai.WithMessages(
		ai.NewUserMessage(
			ai.NewTextPart(prompt),
		),
	)

	modelName := g.provider + "/google/gemini-2.5-flash-image"

	resp, err := genkit.Generate(ctx, g.gk,
		messages,
		ai.WithModelName(modelName),
	)

	if err != nil {
		return "", err
	}

	mediaURL := resp.Media()
	fmt.Println("Generated Media URL:", mediaURL)

	// Getting the image from the response if any
	for _, part := range resp.Message.Content {
		if part.IsImage() {
			if part.Text != "" {
				return part.Text, nil
			}
			if part.Resource != nil {
				return part.Resource.Uri, nil
			}
		}
	}

	return "", nil
}
