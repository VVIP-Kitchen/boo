package llm

import (
	"boo/internal/services/tenor"
	"boo/internal/services/weather"
	"context"
	"os"

	"github.com/firebase/genkit/go/ai"
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

	baseURL := "https://openrouter.ai/api/v1"

	LLM = &GenKitService{
		gk:       setupGenkit(ctx, baseURL, APIKey, Model),
		provider: "openrouter",
	}

	// setting up OpenAI client for image generation
	LLM.openaiClient = setupOpenAIClient(APIKey, baseURL)

	// Initialing tool services
	weather.Setup()
	tenor.Setup()

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
