package llm

import (
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/openai/openai-go"
)

type GenKitService struct {
	gk       *genkit.Genkit
	tools    []ai.ToolRef
	provider string

	openaiClient openai.Client
}

type ImageGenInput struct {
	Prompt      string `json:"prompt"`
	AspectRatio string `json:"aspect_ratio"`
}

type ImageResult struct {
	Data     string `json:"data"`   // base64 or URL
	Format   string `json:"format"` // png, jpg, etc
	IsBase64 bool   `json:"is_base64"`
}

type ChatCompletionResponse struct {
	Type string `json:"type"`
	Data string `json:"data"`
}
