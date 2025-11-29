package db

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"strings"
)

// Singleton DB service
var svc *dbService

type dbService struct {
	BaseURL string
	Timeout int
}

func GetDBService() *dbService {
	return svc
}

func Setup() {
	baseURL, ok := os.LookupEnv("DB_SERVICE_URL")
	if !ok {
		baseURL = "http://localhost:8080"
	}
	svc = &dbService{
		BaseURL: baseURL,
		Timeout: 10,
	}
}

func (d *dbService) FetchPrompt(guildID string) (map[string]string, error) {
	// sending a request
	endpoint := d.BaseURL + "/prompt"
	params := url.Values{}
	params.Add("guild_id", guildID)
	endpoint += "?" + params.Encode()

	req, err := http.NewRequest(http.MethodGet, endpoint, nil)
	if err != nil {
		return nil, err
	}

	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}

	defer resp.Body.Close()

	// Parsing response
	responseBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	if resp.StatusCode != http.StatusOK {
		log.Printf("Error fetching prompt: %s", string(responseBody))

		return map[string]string{"system_prompt": "You are an helpful assistant."}, nil
	}

	// converting response bytes into a map
	var result map[string]string
	if err := json.Unmarshal(responseBody, &result); err != nil {
		return nil, err
	}

	return result, nil
}

func (d *dbService) UpdatePrompt(guildID, systemPrompt string) error {
	entrypoint := d.BaseURL + "/prompt"
	params := url.Values{}
	params.Add("guild_id", guildID)

	// jsonBody := `{"system_prompt":"` + systemPrompt + `"}`
	payload := map[string]string{
		"system_prompt": systemPrompt,
	}
	jsonBody, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	entrypoint += "?" + params.Encode()
	req, err := http.NewRequest(http.MethodPut, entrypoint, strings.NewReader(string(jsonBody)))
	if err != nil {
		return err
	}

	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}

	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		log.Printf("Error updating prompt: %s", jsonBody)
		return fmt.Errorf("failed to update prompt, status code: %d", resp.StatusCode)
	}

	return nil
}

func (d *dbService) AddPrompt(guildID, systemPrompt string) error {
	entrypoint := d.BaseURL + "/prompt"
	payload := map[string]string{
		"guild_id":      guildID,
		"system_prompt": systemPrompt,
	}
	jsonBody, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	req, err := http.NewRequest(http.MethodPost, entrypoint, strings.NewReader(string(jsonBody)))
	if err != nil {
		return err
	}

	req.Header.Set("Content-Type", "application/json")
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}

	defer resp.Body.Close()

	switch resp.StatusCode {
	case 200, 201:
		return nil
	case 409:
		log.Printf("Prompt already exists for guild_id: %s", guildID)
		return nil
	default:
		log.Printf("Error adding prompt: %s", string(jsonBody))
		return fmt.Errorf("failed to add prompt, status code: %d", resp.StatusCode)
	}
}

func (d *dbService) GetChatHistory(guildID string) ([]map[string]string, error) {
	// sending a request
	endpoint := d.BaseURL + "/chat-history"
	params := url.Values{}
	params.Add("guild_id", guildID)
	endpoint += "?" + params.Encode()

	req, err := http.NewRequest(http.MethodGet, endpoint, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	// Parsing response
	responseBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	switch resp.StatusCode {
	case http.StatusOK:
	// continue processing
	case http.StatusNotFound:
		// No chat history found, return empty slice
		return []map[string]string{}, nil
	default:
		log.Printf("Error fetching chat history: %s", string(responseBody))
		return nil, fmt.Errorf("failed to fetch chat history, status code: %d", resp.StatusCode)
	}

	// converting response bytes into a slice of maps
	var result []map[string]string
	if err := json.Unmarshal(responseBody, &result); err != nil {
		return nil, err
	}
	return result, nil
}

func (d *dbService) UpdateChatHistory(guildID string, history []map[string]string) error {
	entrypoint := d.BaseURL + "/chat-history"
	params := url.Values{}
	params.Add("guild_id", guildID)
	entrypoint += "?" + params.Encode()

	jsonBody, err := json.Marshal(history)
	if err != nil {
		return err
	}
	req, err := http.NewRequest(http.MethodPut, entrypoint, strings.NewReader(string(jsonBody)))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		responseBody, _ := io.ReadAll(resp.Body)
		log.Printf("Error updating chat history: %s", string(responseBody))
		return fmt.Errorf("failed to update chat history, status code: %d", resp.StatusCode)
	}

	return nil
}

func (d *dbService) DeleteChatHistory(guildID string) error {
	entrypoint := d.BaseURL + "/chat-history"
	params := url.Values{}
	params.Add("guild_id", guildID)
	entrypoint += "?" + params.Encode()

	req, err := http.NewRequest(http.MethodDelete, entrypoint, nil)
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		responseBody, _ := io.ReadAll(resp.Body)
		log.Printf("Error deleting chat history: %s", string(responseBody))
		return fmt.Errorf("failed to delete chat history, status code: %d", resp.StatusCode)
	}

	return nil
}

type TokenUsage struct {
	MessageID    string `json:"message_id"`
	GuildID      string `json:"guild_id"`
	AuthorID     string `json:"author_id"`
	InputTokens  int    `json:"input_tokens"`
	OutputTokens int    `json:"output_tokens"`
}

func (d *dbService) StoreTokenUsage(usage TokenUsage) error {
	entrypoint := d.BaseURL + "/token-usage"

	jsonBody, err := json.Marshal(usage)
	if err != nil {
		return err
	}

	req, err := http.NewRequest(http.MethodPost, entrypoint, strings.NewReader(string(jsonBody)))
	if err != nil {
		return err
	}

	req.Header.Set("Content-Type", "application/json")
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
		responseBody, _ := io.ReadAll(resp.Body)
		log.Printf("Error storing token usage: %s", string(responseBody))
		return fmt.Errorf("failed to store token usage, status code: %d", resp.StatusCode)
	}

	return nil
}
