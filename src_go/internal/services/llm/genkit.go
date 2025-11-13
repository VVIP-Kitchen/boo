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

func (g *GenKitService) ChatCompletion(ctx context.Context, systemPrompt string, messages []*ai.Message) (string, error) {

	resp, err := genkit.Generate(ctx, g.gk,
		ai.WithSystem(systemPrompt),
		ai.WithMessages(messages...),
	)

	if err != nil {
		return "", err
	}

	return resp.Message.Text(), nil
}
