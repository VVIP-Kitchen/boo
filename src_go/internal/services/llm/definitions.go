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
	Type  string `json:"type"`
	Data  string `json:"data"`
	Usage *Usage `json:"usage,omitempty"`
}

type Usage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// ContentItem represents a single piece of content (text or image)
type ContentItem struct {
	Type     string    `json:"type"`                // "text" or "image_url"
	Text     string    `json:"text,omitempty"`      // for text content
	ImageURL *ImageURL `json:"image_url,omitempty"` // for image content
}

// ImageURL represents an image URL structure
type ImageURL struct {
	URL string `json:"url"` // base64 data URI or URL
}

// MultimodalMessage represents a message that can contain text and/or images
type MultimodalMessage struct {
	Role    string        `json:"role"`
	Content []ContentItem `json:"content"`
}

// ChatMessage is a flexible message type that can be simple text or multimodal
type ChatMessage struct {
	Role    string      `json:"role"`
	Content interface{} `json:"content"` // string or []ContentItem
}
