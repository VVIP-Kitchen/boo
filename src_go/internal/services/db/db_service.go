package db

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"strings"
)

// Singleton DB service

type DBService struct {
	BaseURL string
	Timeout int
}

func (d *DBService) Init() {
	// Connecting to the PG Database
}

func (d *DBService) Close() error {
	// Closing the DB connection
	return nil
}

func (d *DBService) FetchPrompt(guildID string) (map[string]string, error) {
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

		return map[string]string{"system_prompt": ""}, nil
	}

	// converting response bytes into a map
	var result map[string]string
	if err := json.Unmarshal(responseBody, &result); err != nil {
		return nil, err
	}

	return result, nil
}

func (d *DBService) UpdatePrompt(guildID, systemPrompt string) error {
	entrypoint := d.BaseURL + "/prompt"
	params := url.Values{}
	params.Add("guild_id", guildID)

	jsonBody := `{"system_prompt":"` + systemPrompt + `"}`

	req, err := http.NewRequest(http.MethodPut, entrypoint, strings.NewReader(jsonBody))
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

func (d *DBService) AddPrompt(guildID, systemPrompt string) error {
	entrypoint := d.BaseURL + "/prompt"
	jsonBody := `{"guild_id":"` + guildID + `","system_prompt":"` + systemPrompt + `"}`
	req, err := http.NewRequest(http.MethodPost, entrypoint, strings.NewReader(jsonBody))
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
		log.Printf("Error adding prompt: %s", jsonBody)
		return fmt.Errorf("failed to add prompt, status code: %d", resp.StatusCode)
	}
}
