package handlers

import (
	"bytes"
	"context"
	"encoding/base64"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"

	"boo/internal/services/db"
	"boo/internal/services/llm"
	"boo/internal/state"

	"github.com/bwmarrin/discordgo"
)

const CONTEXT_LIMIT = 15
const CONTEXT_RESET_MESSAGE = "Context reset! Starting a new conversation. 👋"

func Messages(discord *discordgo.Session, message *discordgo.MessageCreate) {
	if message.Author.ID == discord.State.User.ID {
		return
	}

	env, ok := os.LookupEnv("ENVIRONMENT")
	if !ok {
		env = "dev"
	}

	if env == "dev" && message.ChannelID != "1272840978277072918" {
		return
	}

	if message.Author.Bot {
		return
	}

	// Only replying if bot is mentioned
	mentioned := false
	if len(message.Mentions) > 0 {
		for _, user := range message.Mentions {
			if user.ID == discord.State.User.ID {
				mentioned = true
				break
			}
		}
	}

	if !mentioned {
		return
	}

	fmt.Println("Received Message", message.Author.DisplayName())

	discord.ChannelTyping(message.ChannelID)
	go handleMessages(discord, message)
}

// getServerID returns the appropriate server ID, handling DMs
func getServerID(message *discordgo.MessageCreate) string {
	if message.GuildID == "" {
		return fmt.Sprintf("DM_%s", message.Author.ID)
	}
	return message.GuildID
}

// getReplyContext fetches the content of the message being replied to
func getReplyContext(s *discordgo.Session, m *discordgo.MessageCreate) string {
	if m.ReferencedMessage != nil {
		return m.ReferencedMessage.Content
	}
	if m.MessageReference != nil {
		ref, err := s.ChannelMessage(m.MessageReference.ChannelID, m.MessageReference.MessageID)
		if err == nil {
			return ref.Content
		}
	}
	return ""
}

// downloadImage downloads an image from a URL and returns it as base64 data URI
func downloadImage(url string, contentType string) (string, error) {
	resp, err := http.Get(url)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	if contentType == "" {
		contentType = "image/png"
	}

	base64Data := base64.StdEncoding.EncodeToString(data)
	return fmt.Sprintf("data:%s;base64,%s", contentType, base64Data), nil
}

// sendErrorMessage sends a generic error message to the channel
func sendErrorMessage(s *discordgo.Session, channelID string) {
	s.ChannelMessageSend(channelID, "❌ Sorry, something went wrong. Please try again later.")
}

func handleMessages(discord *discordgo.Session, message *discordgo.MessageCreate) {
	serverID := getServerID(message)
	messageContent := message.Content

	// Handle reply context
	replyContext := getReplyContext(discord, message)
	if replyContext != "" {
		messageContent = fmt.Sprintf("This is a reply to: %s\n\n%s", replyContext, messageContent)
	}

	// Check for chat reset
	if strings.Contains(strings.ToLower(messageContent), "reset") {
		if strings.Contains(strings.ToLower(messageContent), "reset chat") {
			err := db.GetDBService().DeleteChatHistory(serverID)
			if err != nil {
				fmt.Println("Error resetting chat:", err)
				sendErrorMessage(discord, message.ChannelID)
				return
			}
			discord.ChannelMessageSend(message.ChannelID, CONTEXT_RESET_MESSAGE)
			return
		}
		discord.ChannelMessageSend(message.ChannelID, `-# Say "reset chat"`)
		return
	}

	// Handle image attachments
	var imageAttachments []*discordgo.MessageAttachment
	for _, att := range message.Attachments {
		if strings.HasPrefix(att.ContentType, "image") {
			imageAttachments = append(imageAttachments, att)
		}
	}

	hasImages := len(imageAttachments) > 0
	var imageDataURIs []string

	if hasImages {
		discord.ChannelMessageSend(message.ChannelID,
			fmt.Sprintf("-# Analyzing %d image(s) ... 💭", len(imageAttachments)))

		// Download and convert images to base64
		for _, att := range imageAttachments {
			dataURI, err := downloadImage(att.URL, att.ContentType)
			if err != nil {
				fmt.Println("Error downloading image:", err)
				continue
			}
			imageDataURIs = append(imageDataURIs, dataURI)
		}
	}

	// Fetching the prompt from DB
	if _, exists := state.ServerLore[serverID]; !exists {
		err := loadServerLore(serverID)
		if err != nil {
			fmt.Println("Error loading server lore:", err)
			sendErrorMessage(discord, message.ChannelID)
			return
		}
	}

	ctx := context.Background()

	// Add image note to the stored context
	promptForContext := messageContent
	if hasImages {
		promptForContext = fmt.Sprintf("%s\n\n[Attached %d image(s)]", messageContent, len(imageAttachments))
	}

	err := addUserContext(serverID, message, promptForContext)
	if err != nil {
		fmt.Println("Error adding user context:", err)
	}

	history, err := db.GetDBService().GetChatHistory(serverID)
	if err != nil {
		fmt.Println("Error getting chat history:", err)
		sendErrorMessage(discord, message.ChannelID)
		return
	}

	// Build messages for LLM using multimodal format
	var chatMessages []llm.ChatMessage

	// System message
	chatMessages = append(chatMessages, llm.ChatMessage{
		Role:    "system",
		Content: state.ServerLore[serverID],
	})

	// Add history (text-only from DB)
	for _, h := range history {
		chatMessages = append(chatMessages, llm.ChatMessage{
			Role:    h["role"],
			Content: h["content"],
		})
	}

	// Build user content with images if present
	if hasImages && len(imageDataURIs) > 0 {
		// Multimodal content: text + images
		var contentItems []llm.ContentItem
		contentItems = append(contentItems, llm.ContentItem{
			Type: "text",
			Text: messageContent,
		})
		for _, dataURI := range imageDataURIs {
			contentItems = append(contentItems, llm.ContentItem{
				Type:     "image_url",
				ImageURL: &llm.ImageURL{URL: dataURI},
			})
		}
		chatMessages = append(chatMessages, llm.ChatMessage{
			Role:    "user",
			Content: contentItems,
		})
	} else {
		// Text-only content
		chatMessages = append(chatMessages, llm.ChatMessage{
			Role:    "user",
			Content: messageContent,
		})
	}

	// Use multimodal chat completion - tools disabled when images present
	resp, err := llm.LLM.MultimodalChatCompletion(ctx, chatMessages, !hasImages)
	if err != nil {
		fmt.Println("Error getting chat completion:", err)
		sendErrorMessage(discord, message.ChannelID)
		return
	}

	if resp.Type == "image" {

		var rReader *bytes.Reader
		// Try decoding base64, if that fails use the raw string as bytes
		// First extracting the base64 data by removing the data URL prefix if present
		data := resp.Data
		if len(data) > 22 && data[:22] == "data:image/png;base64," {
			data = data[22:]
		}
		if decoded, err := base64.StdEncoding.DecodeString(data); err == nil {
			rReader = bytes.NewReader(decoded)
		} else {
			rReader = bytes.NewReader([]byte(resp.Data))
		}

		_, err := discord.ChannelMessageSendComplex(message.ChannelID, &discordgo.MessageSend{
			Content: "Here is your generated image:",
			Files: []*discordgo.File{
				{
					Name:        "generated_image.png",
					ContentType: "image/png",
					Reader:      rReader,
				},
			},
		})
		if err != nil {
			fmt.Println("Error sending image:", err)
		}

		return
	}

	// Store token usage if available
	if resp.Usage != nil {
		tokenUsage := db.TokenUsage{
			MessageID:    fmt.Sprintf("%d", message.ID),
			GuildID:      serverID,
			AuthorID:     message.Author.ID,
			InputTokens:  resp.Usage.PromptTokens,
			OutputTokens: resp.Usage.TotalTokens,
		}
		err = db.GetDBService().StoreTokenUsage(tokenUsage)
		if err != nil {
			fmt.Println("Error storing token usage:", err)
		}
	}

	err = addAssistantContext(serverID, resp.Data)
	if err != nil {
		fmt.Println("Error adding assistant context:", err)
	}

	err = trimContext(serverID)
	if err != nil {
		fmt.Println("Error trimming context:", err)
	}

	discord.ChannelMessageSend(message.ChannelID, resp.Data)
}

func loadServerLore(guildID string) error {
	prompt, err := db.GetDBService().FetchPrompt(guildID)
	if err != nil {
		return err
	}
	lore := prompt["system_prompt"]
	state.ServerLore[guildID] = lore

	return nil
}

func addUserContext(serverID string, message *discordgo.MessageCreate, prompt string) error {
	serverContext, err := db.GetDBService().GetChatHistory(serverID)
	if err != nil {
		return err
	}

	content := fmt.Sprintf("%s (aka %s) said: %s", message.Author.Username, message.Author.DisplayName(), prompt)

	serverContext = append(serverContext, map[string]string{
		"role":    "user",
		"content": content,
	})
	return db.GetDBService().UpdateChatHistory(serverID, serverContext)
}

func addAssistantContext(serverID, content string) error {
	serverContext, err := db.GetDBService().GetChatHistory(serverID)
	if err != nil {
		return err
	}

	serverContext = append(serverContext, map[string]string{
		"role":    "assistant",
		"content": content,
	})
	return db.GetDBService().UpdateChatHistory(serverID, serverContext)
}

func trimContext(serverID string) error {
	serverContext, err := db.GetDBService().GetChatHistory(serverID)
	if err != nil {
		fmt.Println("Error trimming context:", err)
		return err
	}

	if len(serverContext) > CONTEXT_LIMIT {
		excess := len(serverContext) - CONTEXT_LIMIT
		serverContext = serverContext[excess:]
		return db.GetDBService().UpdateChatHistory(serverID, serverContext)
	}
	return nil
}
