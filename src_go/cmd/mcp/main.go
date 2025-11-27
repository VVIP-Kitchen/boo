package main

import (
	"fmt"
	"os"

	"boo/internal/services/tenor"
	"boo/internal/services/weather"

	mcp_golang "github.com/metoro-io/mcp-golang"
	"github.com/metoro-io/mcp-golang/transport/stdio"

	"github.com/joho/godotenv"
)

// TenorSearchArguments defines the arguments for the Tenor GIF search tool
type TenorSearchArguments struct {
	Query string `json:"query" jsonschema:"required,description=The search query to find GIFs on Tenor"`
}

// WeatherArguments defines the arguments for the weather lookup tool
type WeatherArguments struct {
	Location string `json:"location" jsonschema:"required,description=The location to get weather information for (city name or coordinates)"`
}

func main() {
	// Load environment variables from the project root .env file
	// Try multiple possible locations
	envPaths := []string{
		"../../.env",           // When running from src_go/cmd/mcp
		"../.env",              // When running from src_go
		".env",                 // Current directory
		"e:/Projects/boo/.env", // Absolute path as fallback
	}

	envLoaded := false
	for _, path := range envPaths {
		if err := godotenv.Load(path); err == nil {
			fmt.Fprintf(os.Stderr, "Loaded environment from: %s\n", path)
			envLoaded = true
			break
		}
	}

	if !envLoaded {
		fmt.Fprintf(os.Stderr, "Warning: Could not load .env file from any location\n")
	}

	// Initialize services
	tenor.Setup()
	weather.Setup()

	// Create MCP server with stdio transport
	done := make(chan struct{})
	server := mcp_golang.NewServer(stdio.NewStdioServerTransport())

	// Register Tenor GIF search tool
	err := server.RegisterTool(
		"tenor_search",
		"Search for GIFs on Tenor. Returns a URL to a random GIF matching the search query.",
		func(arguments TenorSearchArguments) (*mcp_golang.ToolResponse, error) {
			if arguments.Query == "" {
				return nil, fmt.Errorf("query is required")
			}

			gifURL, err := tenor.SVC.Search(arguments.Query)
			if err != nil {
				return nil, fmt.Errorf("failed to search Tenor: %w", err)
			}

			return mcp_golang.NewToolResponse(mcp_golang.NewTextContent(fmt.Sprintf("Found GIF: %s", gifURL))), nil
		},
	)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to register tenor_search tool: %v\n", err)
		os.Exit(1)
	}

	// Register Weather lookup tool
	err = server.RegisterTool(
		"weather",
		"Get current weather information for a location. Returns detailed weather data including temperature, humidity, wind, and conditions.",
		func(arguments WeatherArguments) (*mcp_golang.ToolResponse, error) {
			if arguments.Location == "" {
				return nil, fmt.Errorf("location is required")
			}

			weatherInfo := weather.SVC.WeatherInfo(arguments.Location)

			return mcp_golang.NewToolResponse(mcp_golang.NewTextContent(weatherInfo)), nil
		},
	)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to register weather tool: %v\n", err)
		os.Exit(1)
	}

	// Start the server
	fmt.Fprintf(os.Stderr, "MCP Server starting...\n")
	if err := server.Serve(); err != nil {
		fmt.Fprintf(os.Stderr, "Server error: %v\n", err)
		os.Exit(1)
	}

	<-done
}
