package llm

import (
	"boo/internal/services/tenor"
	"boo/internal/services/weather"
	"context"
	"os"
	"strings"

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

// convertMessages converts simple text messages to ai.Message format
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

// convertMultimodalMessages converts multimodal messages (with images) to ai.Message format
func convertMultimodalMessages(messages []ChatMessage) []*ai.Message {
	var result []*ai.Message

	for _, m := range messages {
		role := ai.Role(m.Role)
		var parts []*ai.Part

		switch content := m.Content.(type) {
		case string:
			// Simple text content
			parts = append(parts, &ai.Part{Text: content})

		case []interface{}:
			// Multimodal content (array of ContentItems from JSON)
			for _, item := range content {
				if itemMap, ok := item.(map[string]interface{}); ok {
					itemType, _ := itemMap["type"].(string)

					switch itemType {
					case "text":
						if text, ok := itemMap["text"].(string); ok {
							parts = append(parts, &ai.Part{Text: text})
						}
					case "image_url":
						if imageURL, ok := itemMap["image_url"].(map[string]interface{}); ok {
							if url, ok := imageURL["url"].(string); ok {
								mediaData := extractMediaFromDataURI(url)
								// Use NewMediaPart - compat_oai uses part.Text as the image URL
								parts = append(parts, ai.NewMediaPart(mediaData.ContentType, url))
							}
						}
					}
				}
			}

		case []ContentItem:
			// Typed multimodal content (from Go code)
			for _, item := range content {
				switch item.Type {
				case "text":
					parts = append(parts, ai.NewTextPart(item.Text))
				case "image_url":
					if item.ImageURL != nil {
						mediaData := extractMediaFromDataURI(item.ImageURL.URL)
						// Use NewMediaPart - compat_oai uses part.Text as the image URL
						parts = append(parts, ai.NewMediaPart(mediaData.ContentType, item.ImageURL.URL))
					}
				}
			}

		default:
			// Fallback: try to convert to string
			if str, ok := m.Content.(string); ok {
				parts = append(parts, &ai.Part{Text: str})
			}
		}

		msg := &ai.Message{
			Role:    role,
			Content: parts,
		}
		result = append(result, msg)
	}
	return result
}

// MediaData holds extracted media information
type MediaData struct {
	ContentType string
	Data        string // base64 encoded data (without the data URI prefix)
	DataURI     string // full data URI
}

// extractMediaFromDataURI extracts content type and data from a data URI
func extractMediaFromDataURI(dataURI string) MediaData {
	// Format: data:image/jpeg;base64,/9j/4AAQ...
	if strings.HasPrefix(dataURI, "data:") {
		// Remove "data:" prefix
		rest := dataURI[5:]

		// Split by comma to get metadata and data
		parts := strings.SplitN(rest, ",", 2)
		if len(parts) == 2 {
			// Parse content type (e.g., "image/jpeg;base64")
			metadata := parts[0]
			contentType := strings.Split(metadata, ";")[0]
			base64Data := parts[1]

			return MediaData{
				ContentType: contentType,
				Data:        base64Data,
				DataURI:     dataURI,
			}
		}
	}

	// Default to PNG if can't parse
	return MediaData{
		ContentType: "image/png",
		Data:        dataURI,
		DataURI:     dataURI,
	}
}

// hasVisionContent checks if any message contains image content
func hasVisionContent(messages []ChatMessage) bool {
	for _, m := range messages {
		switch content := m.Content.(type) {
		case []interface{}:
			for _, item := range content {
				if itemMap, ok := item.(map[string]interface{}); ok {
					if itemType, ok := itemMap["type"].(string); ok && itemType == "image_url" {
						return true
					}
				}
			}
		case []ContentItem:
			for _, item := range content {
				if item.Type == "image_url" {
					return true
				}
			}
		default:
			// Check if it's a slice using reflection-like approach
			// This handles the case where []ContentItem is stored as interface{}
			if items, ok := m.Content.([]ContentItem); ok {
				for _, item := range items {
					if item.Type == "image_url" {
						return true
					}
				}
			}
		}
	}
	return false
}
