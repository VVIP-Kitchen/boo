package llm

import (
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

type GenKitService struct {
	gk       *genkit.Genkit
	tools    []ai.ToolRef
	provider string
}

type ImageGenInput struct {
	Prompt      string `json:"prompt"`
	AspectRatio string `json:"aspect_ratio"`
}
