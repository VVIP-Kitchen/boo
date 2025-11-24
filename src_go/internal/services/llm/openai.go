package llm

import (
	"context"
	"encoding/json"
	"strings"

	"github.com/openai/openai-go"
	"github.com/openai/openai-go/option"
)

func setupOpenAIClient(apiKey, baseURL string) openai.Client {
	return openai.NewClient(
		option.WithBaseURL(baseURL),
		option.WithAPIKey(apiKey),
	)
}

func (g *GenKitService) GenerateImage(ctx context.Context, prompt string, aspectRatio string) (*ImageResult, error) {

	messages := []openai.ChatCompletionMessageParamUnion{
		openai.UserMessage(prompt),
	}

	resp, err := g.openaiClient.Chat.Completions.New(ctx, openai.ChatCompletionNewParams{
		Modalities: []string{"image"},
		Model:      "google/gemini-2.5-flash-image",
		Messages:   messages,
	},
	)

	if err != nil {
		return nil, err
	}

	// Converting the string JSON to a Go value from "resp.Choices[0].Message.JSON.ExtraFields["images"].Raw()"
	imagesRaw := resp.Choices[0].Message.JSON.ExtraFields["images"].Raw()

	var images []map[string]any
	if err := json.Unmarshal([]byte(imagesRaw), &images); err != nil {
		return nil, err
	}

	imageURL := images[0]["image_url"].(map[string]interface{})["url"].(string)

	result := &ImageResult{
		Data:     imageURL,
		IsBase64: strings.HasPrefix(imageURL, "data:"),
	}

	if result.IsBase64 {
		// Extract format from data URI
		if strings.Contains(imageURL, "image/png") {
			result.Format = "png"
		} else if strings.Contains(imageURL, "image/jpeg") {
			result.Format = "jpg"
		}
	}

	return result, nil
}
