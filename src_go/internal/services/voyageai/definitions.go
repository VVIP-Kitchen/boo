package voyageai

import "net/http"

const (
	baseURL         = "https://api.voyageai.com/v1/multimodalembeddings"
	defaultModel    = "voyage-multimodal-3"
	maxPixels       = 16_000_000       // 16M pixels
	maxSizeBytes    = 20 * 1024 * 1024 // 20MB
	targetMaxPixels = 1920 * 1080      // ~2M pixels (1080p)
	defaultQuality  = 85
)

// InputType represents the type of input for embeddings
type InputType string

const (
	InputTypeNull     InputType = ""
	InputTypeQuery    InputType = "query"
	InputTypeDocument InputType = "document"
)

// VoyageAIService handles VoyageAI embedding operations
type VoyageAIService struct {
	apiKey string
	model  string
	client *http.Client
}

// ContentItem represents a single piece of content (text or image)
type ContentItem struct {
	Type        string `json:"type"`
	Text        string `json:"text,omitempty"`
	ImageBase64 string `json:"image_base64,omitempty"`
	ImageURL    string `json:"image_url,omitempty"`
}

// Input represents a single input containing content
type Input struct {
	Content []ContentItem `json:"content"`
}

// EmbeddingRequest represents the request body for the API
type EmbeddingRequest struct {
	Inputs         []Input   `json:"inputs"`
	Model          string    `json:"model"`
	InputType      InputType `json:"input_type,omitempty"`
	Truncation     *bool     `json:"truncation,omitempty"`
	OutputEncoding *string   `json:"output_encoding,omitempty"`
}

// EmbeddingData represents a single embedding result
type EmbeddingData struct {
	Object    string    `json:"object"`
	Embedding []float64 `json:"embedding"`
	Index     int       `json:"index"`
}

// Usage represents token usage information
type Usage struct {
	TextTokens  int `json:"text_tokens"`
	ImagePixels int `json:"image_pixels"`
	TotalTokens int `json:"total_tokens"`
}

// EmbeddingResponse represents the API response
type EmbeddingResponse struct {
	Object string          `json:"object"`
	Data   []EmbeddingData `json:"data"`
	Model  string          `json:"model"`
	Usage  Usage           `json:"usage"`
}

// APIError represents an error response from the API
type APIError struct {
	Error struct {
		Message string `json:"message"`
		Type    string `json:"type"`
		Code    string `json:"code"`
	} `json:"error"`
}

// ImageInfo contains metadata about an image
type ImageInfo struct {
	Width     int
	Height    int
	Pixels    int
	SizeBytes int
	SizeMB    float64
}
