package voyageai

import (
	"bytes"
	"encoding/base64"
	"fmt"
	"image"
	"image/jpeg"
	"log/slog"
	"math"
	"net/http"

	"golang.org/x/image/draw"
)

// compressImage compresses an image to meet Voyage AI requirements
func compressImage(imgBytes []byte, targetMaxPx, quality int) ([]byte, error) {
	// Decode image
	img, _, err := image.Decode(bytes.NewReader(imgBytes))
	if err != nil {
		return nil, fmt.Errorf("failed to decode image: %w", err)
	}

	bounds := img.Bounds()
	origWidth := bounds.Dx()
	origHeight := bounds.Dy()
	origPixels := origWidth * origHeight

	// Calculate target size
	newWidth, newHeight := calculateTargetSize(origWidth, origHeight, targetMaxPx)

	// Resize if needed
	var resizedImg image.Image
	if newWidth != origWidth || newHeight != origHeight {
		slog.Info("Resizing image",
			"from", fmt.Sprintf("%dx%d (%d pixels)", origWidth, origHeight, origPixels),
			"to", fmt.Sprintf("%dx%d (%d pixels)", newWidth, newHeight, newWidth*newHeight),
		)

		// Create new image with target size
		dst := image.NewRGBA(image.Rect(0, 0, newWidth, newHeight))

		// Use high-quality scaling (CatmullRom is similar to Lanczos)
		draw.CatmullRom.Scale(dst, dst.Bounds(), img, bounds, draw.Over, nil)
		resizedImg = dst
	} else {
		resizedImg = img
	}

	// Encode to JPEG
	var buf bytes.Buffer
	if err := jpeg.Encode(&buf, resizedImg, &jpeg.Options{Quality: quality}); err != nil {
		return nil, fmt.Errorf("failed to encode image: %w", err)
	}

	compressedBytes := buf.Bytes()
	compressionRatio := (1 - float64(len(compressedBytes))/float64(len(imgBytes))) * 100

	slog.Info("Compressed image",
		"from_kb", fmt.Sprintf("%.1f", float64(len(imgBytes))/1024),
		"to_kb", fmt.Sprintf("%.1f", float64(len(compressedBytes))/1024),
		"reduction", fmt.Sprintf("%.1f%%", compressionRatio),
	)

	// If still too large, reduce quality iteratively
	if len(compressedBytes) > maxSizeBytes {
		slog.Warn("Image still too large, reducing quality...",
			"size_mb", fmt.Sprintf("%.1f", float64(len(compressedBytes))/1024/1024),
		)

		for _, reducedQuality := range []int{75, 65, 55, 45} {
			buf.Reset()
			if err := jpeg.Encode(&buf, resizedImg, &jpeg.Options{Quality: reducedQuality}); err != nil {
				return nil, fmt.Errorf("failed to encode image: %w", err)
			}

			compressedBytes = buf.Bytes()
			slog.Info("Trying reduced quality",
				"quality", reducedQuality,
				"size_mb", fmt.Sprintf("%.2f", float64(len(compressedBytes))/1024/1024),
			)

			if len(compressedBytes) <= maxSizeBytes {
				break
			}
		}
	}

	return compressedBytes, nil
}

// imageToBase64 converts image bytes to a base64 data URL
func imageToBase64(imgBytes []byte) string {
	// Detect content type
	contentType := http.DetectContentType(imgBytes)

	// Default to jpeg if unknown
	if contentType == "application/octet-stream" {
		contentType = "image/jpeg"
	}

	encoded := base64.StdEncoding.EncodeToString(imgBytes)
	return fmt.Sprintf("data:%s;base64,%s", contentType, encoded)
}

// getImageInfo returns metadata about an image
func getImageInfo(imgBytes []byte) (*ImageInfo, error) {
	img, _, err := image.Decode(bytes.NewReader(imgBytes))
	if err != nil {
		return nil, err
	}

	bounds := img.Bounds()
	width := bounds.Dx()
	height := bounds.Dy()

	return &ImageInfo{
		Width:     width,
		Height:    height,
		Pixels:    width * height,
		SizeBytes: len(imgBytes),
		SizeMB:    float64(len(imgBytes)) / 1024 / 1024,
	}, nil
}

// validateImageForVoyage checks if image meets Voyage AI requirements
func validateImageForVoyage(imgBytes []byte) (bool, string) {
	imgInfo, err := getImageInfo(imgBytes)
	if err != nil {
		return false, fmt.Sprintf("invalid image: %v", err)
	}

	if imgInfo.Pixels > maxPixels {
		return false, fmt.Sprintf("image too large: %d pixels (max %d)", imgInfo.Pixels, maxPixels)
	}

	if imgInfo.SizeBytes > maxSizeBytes {
		return false, fmt.Sprintf("file too large: %.1fMB (max 20MB)", imgInfo.SizeMB)
	}

	return true, "OK"
}

// calculateTargetSize calculates target dimensions while maintaining aspect ratio
func calculateTargetSize(width, height, maxPx int) (int, int) {
	currentPixels := width * height

	if currentPixels <= maxPx {
		return width, height
	}

	// Calculate scale factor using square root to scale both dimensions proportionally
	scale := math.Sqrt(float64(maxPx) / float64(currentPixels))

	newWidth := int(float64(width) * scale)
	newHeight := int(float64(height) * scale)

	return newWidth, newHeight
}
