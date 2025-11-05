package llm

import (
	"context"

	"github.com/firebase/genkit/go/genkit"
)

type GenKitService struct {
	// GenKit specific fields
	apiKey string
	model  string
}

func (g *GenKitService) init(ctx context.Context) error {
	gk := genkit.Init(ctx, nil)

	return nil
}
