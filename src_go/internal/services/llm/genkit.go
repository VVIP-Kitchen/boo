package llm

import (
	"context"
	"fmt"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/compat_oai"
)

func setupGenkit(ctx context.Context, baseURL, apiKey, model string) *genkit.Genkit {
	gk := genkit.Init(ctx, genkit.WithPlugins(&compat_oai.OpenAICompatible{
		BaseURL:  baseURL,
		APIKey:   apiKey,
		Provider: "openrouter",
	}), genkit.WithDefaultModel("openrouter/"+model))

	return gk
}

func (g *GenKitService) ChatCompletion(ctx context.Context, messages []map[string]string) (ChatCompletionResponse, error) {

	resp, err := genkit.Generate(ctx, g.gk,
		ai.WithMessages(convertMessages(messages)...),
		ai.WithTools(g.tools...),
		ai.WithReturnToolRequests(true),
	)
	if err != nil {
		return ChatCompletionResponse{}, err
	}

	parts := []*ai.Part{}

	for {
		if len(resp.ToolRequests()) == 0 {
			break
		}

		for _, req := range resp.ToolRequests() {
			tool := genkit.LookupTool(g.gk, req.Name)
			if tool == nil {
				return ChatCompletionResponse{}, fmt.Errorf("tool %q not found", req.Name)
			}

			output, err := tool.RunRaw(ctx, req.Input)
			if err != nil {
				return ChatCompletionResponse{}, fmt.Errorf("tool %q execution failed: %v", tool.Name(), err)
			}

			if tool.Name() == "generateImage" {
				imageResult, ok := output.(map[string]interface{})
				if !ok {
					return ChatCompletionResponse{}, fmt.Errorf("unexpected image result type for tool %q", tool.Name())
				}
				// Directly return the image, no need to send back to LLM
				return ChatCompletionResponse{
					Type: "image",
					Data: imageResult["data"].(string),
				}, nil
			}

			parts = append(parts,
				ai.NewToolResponsePart(&ai.ToolResponse{
					Name:   req.Name,
					Ref:    req.Ref,
					Output: output,
				}))
		}

		// Let the LLM continue processing now that we've provided tool responses.
		resp, err = genkit.Generate(ctx, g.gk,
			ai.WithMessages(convertMessages(messages)...),
			ai.WithTools(g.tools...),
			ai.WithReturnToolRequests(true),
			ai.WithToolResponses(parts...),
		)
		if err != nil {
			return ChatCompletionResponse{}, err
		}
	}

	if err != nil {
		return ChatCompletionResponse{}, err
	}

	return ChatCompletionResponse{
		Type: "text",
		Data: resp.Message.Text(),
	}, nil
}
