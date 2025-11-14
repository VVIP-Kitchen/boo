package llm

import (
	"context"
	"os"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/compat_oai"
)

var LLM *GenKitService

type GenKitService struct {
	gk *genkit.Genkit
}

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

	LLM = &GenKitService{gk: gk}
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
	)

	if err != nil {
		return "", err
	}

	return resp.Message.Text(), nil
}
