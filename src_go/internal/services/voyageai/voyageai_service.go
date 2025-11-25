package voyageai

import (
	"bytes"
	"encoding/json"
	"fmt"
	_ "image/gif"
	_ "image/png"
	"io"
	"log/slog"
	"net/http"
	"os"
	"time"

	_ "golang.org/x/image/webp"
)

// SVC is the global VoyageAI service instance
var SVC *VoyageAIService

// Setup initializes the global VoyageAI service
func Setup() {
	SVC = &VoyageAIService{
		apiKey: os.Getenv("VOYAGEAI_API_KEY"),
		model:  defaultModel,
		client: &http.Client{
			Timeout: 60 * time.Second,
		},
	}
}

// GenerateTextEmbeddings generates embeddings for a single text
func (v *VoyageAIService) GenerateTextEmbeddings(text string) ([]float64, error) {
	input := Input{
		Content: []ContentItem{
			{Type: "text", Text: text},
		},
	}

	resp, err := v.callAPI([]Input{input}, InputTypeNull)
	if err != nil {
		return nil, err
	}

	if len(resp.Data) == 0 {
		return nil, fmt.Errorf("no embeddings returned")
	}

	return resp.Data[0].Embedding, nil
}

// GenerateImageEmbeddings generates embeddings for a single image
// Automatically compresses image if needed to meet Voyage AI requirements
func (v *VoyageAIService) GenerateImageEmbeddings(imgBytes []byte) ([]float64, error) {
	// Log original image info
	imgInfo, err := getImageInfo(imgBytes)
	if err != nil {
		return nil, fmt.Errorf("failed to get image info: %w", err)
	}
	slog.Info("Original image",
		"width", imgInfo.Width,
		"height", imgInfo.Height,
		"pixels", imgInfo.Pixels,
		"size_mb", fmt.Sprintf("%.2f", imgInfo.SizeMB),
	)

	// Check if compression is needed
	isValid, errMsg := validateImageForVoyage(imgBytes)
	if !isValid {
		slog.Warn("Image validation failed, compressing...", "error", errMsg)
		imgBytes, err = compressImage(imgBytes, targetMaxPixels, defaultQuality)
		if err != nil {
			return nil, fmt.Errorf("failed to compress image: %w", err)
		}

		// Validate after compression
		isValid, errMsg = validateImageForVoyage(imgBytes)
		if !isValid {
			return nil, fmt.Errorf("image still invalid after compression: %s", errMsg)
		}
		slog.Info("Image compressed successfully and validated")
	} else {
		slog.Info("Image meets requirements, no compression needed")
	}

	// Convert to base64
	base64Img := imageToBase64(imgBytes)

	input := Input{
		Content: []ContentItem{
			{Type: "image_base64", ImageBase64: base64Img},
		},
	}

	resp, err := v.callAPI([]Input{input}, InputTypeNull)
	if err != nil {
		return nil, err
	}

	if len(resp.Data) == 0 {
		return nil, fmt.Errorf("no embeddings returned")
	}

	return resp.Data[0].Embedding, nil
}

// GenerateBatchEmbeddings generates embeddings for multiple inputs (text and/or images) in one API call
// Automatically compresses images if needed
func (v *VoyageAIService) GenerateBatchEmbeddings(inputs []interface{}) ([][]float64, error) {
	preparedInputs := make([]Input, 0, len(inputs))

	for idx, item := range inputs {
		switch val := item.(type) {
		case string:
			// Text input
			preparedInputs = append(preparedInputs, Input{
				Content: []ContentItem{
					{Type: "text", Text: val},
				},
			})

		case []byte:
			// Image bytes - compress if needed
			imgBytes := val

			imgInfo, err := getImageInfo(imgBytes)
			if err != nil {
				return nil, fmt.Errorf("input %d: failed to get image info: %w", idx, err)
			}
			slog.Info(fmt.Sprintf("Input %d: Image", idx),
				"width", imgInfo.Width,
				"height", imgInfo.Height,
				"pixels", imgInfo.Pixels,
				"size_mb", fmt.Sprintf("%.2f", imgInfo.SizeMB),
			)

			isValid, errMsg := validateImageForVoyage(imgBytes)
			if !isValid {
				slog.Warn(fmt.Sprintf("Input %d: Compression needed", idx), "reason", errMsg)
				imgBytes, err = compressImage(imgBytes, targetMaxPixels, defaultQuality)
				if err != nil {
					return nil, fmt.Errorf("input %d: failed to compress image: %w", idx, err)
				}

				// Validate after compression
				isValid, errMsg = validateImageForVoyage(imgBytes)
				if !isValid {
					return nil, fmt.Errorf("input %d: still invalid after compression: %s", idx, errMsg)
				}
				slog.Info(fmt.Sprintf("Input %d: Compressed successfully", idx))
			} else {
				slog.Info(fmt.Sprintf("Input %d: No compression needed", idx))
			}

			base64Img := imageToBase64(imgBytes)
			preparedInputs = append(preparedInputs, Input{
				Content: []ContentItem{
					{Type: "image_base64", ImageBase64: base64Img},
				},
			})

		default:
			return nil, fmt.Errorf("unsupported input type at index %d: %T", idx, item)
		}
	}

	// Single API call for all inputs
	slog.Info("Generating embeddings", "count", len(preparedInputs))
	resp, err := v.callAPI(preparedInputs, InputTypeNull)
	if err != nil {
		return nil, err
	}
	slog.Info("Successfully generated embeddings", "count", len(resp.Data))

	// Extract embeddings in order
	embeddings := make([][]float64, len(resp.Data))
	for _, data := range resp.Data {
		embeddings[data.Index] = data.Embedding
	}

	return embeddings, nil
}

// GenerateEmbeddingsWithType generates embeddings with a specific input type (query/document)
func (v *VoyageAIService) GenerateEmbeddingsWithType(text string, inputType InputType) ([]float64, error) {
	input := Input{
		Content: []ContentItem{
			{Type: "text", Text: text},
		},
	}

	resp, err := v.callAPI([]Input{input}, inputType)
	if err != nil {
		return nil, err
	}

	if len(resp.Data) == 0 {
		return nil, fmt.Errorf("no embeddings returned")
	}

	return resp.Data[0].Embedding, nil
}

// GenerateMultimodalEmbeddings generates embeddings for content that combines text and image
func (v *VoyageAIService) GenerateMultimodalEmbeddings(text string, imgBytes []byte) ([]float64, error) {
	// Compress image if needed
	isValid, errMsg := validateImageForVoyage(imgBytes)
	if !isValid {
		slog.Warn("Image validation failed, compressing...", "error", errMsg)
		var err error
		imgBytes, err = compressImage(imgBytes, targetMaxPixels, defaultQuality)
		if err != nil {
			return nil, fmt.Errorf("failed to compress image: %w", err)
		}
	}

	base64Img := imageToBase64(imgBytes)

	input := Input{
		Content: []ContentItem{
			{Type: "text", Text: text},
			{Type: "image_base64", ImageBase64: base64Img},
		},
	}

	resp, err := v.callAPI([]Input{input}, InputTypeNull)
	if err != nil {
		return nil, err
	}

	if len(resp.Data) == 0 {
		return nil, fmt.Errorf("no embeddings returned")
	}

	return resp.Data[0].Embedding, nil
}

// callAPI makes the actual API request to VoyageAI
func (v *VoyageAIService) callAPI(inputs []Input, inputType InputType) (*EmbeddingResponse, error) {
	reqBody := EmbeddingRequest{
		Inputs:    inputs,
		Model:     v.model,
		InputType: inputType,
	}

	jsonBody, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	req, err := http.NewRequest("POST", baseURL, bytes.NewReader(jsonBody))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Authorization", "Bearer "+v.apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := v.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		var apiErr APIError
		if json.Unmarshal(body, &apiErr) == nil && apiErr.Error.Message != "" {
			return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, apiErr.Error.Message)
		}
		return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, string(body))
	}

	var embeddingResp EmbeddingResponse
	if err := json.Unmarshal(body, &embeddingResp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return &embeddingResp, nil
}
