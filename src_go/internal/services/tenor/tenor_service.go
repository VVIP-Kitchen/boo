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

func (t *TenorService) Search(query string) (any, error) {
	// URL-encode the query
	escapedQuery := url.QueryEscape(query)

	queryString := fmt.Sprintf("%s/search?q=%s&key=%s&limit=%d", t.baseURL, escapedQuery, t.apiKey, t.searchLimit)

	req, err := http.NewRequest(http.MethodGet, queryString, nil)
	if err != nil {
		return nil, err
	}

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	responseBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("tenor API error: %s", string(responseBody))
	}

	var result map[string]any
	err = json.Unmarshal(responseBody, &result)
	if err != nil {
		return nil, fmt.Errorf("failed to parse JSON: %w; body: %s", err, string(responseBody))
	}

	results, ok := result["results"]
	if !ok {
		return nil, fmt.Errorf("no 'results' field in response: %v", result)
	}
	return results, nil
}
