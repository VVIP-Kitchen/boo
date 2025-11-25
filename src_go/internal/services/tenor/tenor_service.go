package tenor

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
)

var SVC *TenorService

type TenorService struct {
	apiKey      string
	baseURL     string
	searchLimit int
}

type TenorSearchInput struct {
	Query string `json:"query"`
}

func Setup() {
	APIKey, ok := os.LookupEnv("TENOR_API_KEY")
	if !ok {
		panic("TENOR_API_KEY not found")
	}
	SVC = &TenorService{
		apiKey:      APIKey,
		baseURL:     "https://tenor.googleapis.com/v2",
		searchLimit: 10,
	}
}

func (t *TenorService) Search(query string) (string, error) {
	// URL-encode the query
	escapedQuery := url.QueryEscape(query)

	queryString := fmt.Sprintf("%s/search?q=%s&key=%s&limit=%d", t.baseURL, escapedQuery, t.apiKey, t.searchLimit)

	req, err := http.NewRequest(http.MethodGet, queryString, nil)
	if err != nil {
		return "", err
	}

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	responseBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("tenor API error: %s", string(responseBody))
	}

	var result map[string]any
	err = json.Unmarshal(responseBody, &result)
	if err != nil {
		return "", fmt.Errorf("failed to parse JSON: %w; body: %s", err, string(responseBody))
	}

	results, ok := result["results"]
	if !ok {
		return "", fmt.Errorf("no 'results' field in response: %v", result)
	}
	output, ok := results.([]interface{})[0].(map[string]interface{})["url"].(string)
	if !ok {
		return "", fmt.Errorf("unable to extract URL from results: %v", results)
	}
	return output, nil
}
