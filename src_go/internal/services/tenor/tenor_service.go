package tenor

import (
	"encoding/json"
	"fmt"
	"io"
	"math/rand"
	"net/http"
	"net/url"
	"os"
	"time"
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
		searchLimit: 30,
	}
}

func (t *TenorService) Search(query string) (string, error) {
	// Use a local random generator for concurrency safety and to avoid deprecated rand.Seed
	rng := rand.New(rand.NewSource(time.Now().UnixNano()))

	// Support random pagination (0-4 pages, 10 results per page)
	page := rng.Intn(5)
	offset := page * t.searchLimit

	escapedQuery := url.QueryEscape(query)
	queryString := fmt.Sprintf("%s/search?q=%s&key=%s&limit=%d&pos=%d", t.baseURL, escapedQuery, t.apiKey, t.searchLimit, offset)

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
	resultsArr, ok := results.([]interface{})
	if !ok || len(resultsArr) == 0 {
		return "", fmt.Errorf("no results found: %v", results)
	}
	// Pick a random result from the page
	randomIdx := rng.Intn(len(resultsArr))
	item, ok := resultsArr[randomIdx].(map[string]interface{})
	if !ok {
		return "", fmt.Errorf("unexpected result format: %v", resultsArr[randomIdx])
	}
	output, ok := item["url"].(string)
	if !ok {
		return "", fmt.Errorf("unable to extract URL from result: %v", item)
	}
	return output, nil
}
