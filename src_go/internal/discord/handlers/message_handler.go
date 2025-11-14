package handlers

import (
	"context"
	"fmt"
	"os"

	"boo/internal/services/db"
	"boo/internal/services/llm"
	"boo/internal/state"

	"github.com/bwmarrin/discordgo"
)

const CONTEXT_LIMIT = 15

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

	// responding with dummy text with typing indicator
	discord.ChannelTyping(message.ChannelID)
	go handleMessages(discord, message)
}

func handleMessages(discord *discordgo.Session, message *discordgo.MessageCreate) {
	// Fetching the prompt from DB
	if _, exists := state.ServerLore[message.GuildID]; !exists {
		err := loadServerLore(message.GuildID)
		if err != nil {
			fmt.Println("Error loading server lore:", err)
			return
		}
	}

	ctx := context.Background()
	guildID := message.GuildID

	addUserContext(guildID, message)

	history, err := db.GetDBService().GetChatHistory(message.GuildID)
	if err != nil {
		fmt.Println("Error getting chat history:", err)
		return
	}
	messages := []map[string]string{
		{"role": "system", "content": state.ServerLore[message.GuildID]},
	}
	messages = append(messages, history...)
	messages = append(messages, map[string]string{"role": "user", "content": message.Content})

	resp, err := llm.LLM.ChatCompletion(ctx, messages)
	if err != nil {
		fmt.Println("Error getting chat completion:", err)
		return
	}
	addAssistantContext(guildID, resp)
	trimContext(guildID)
	discord.ChannelMessageSend(message.ChannelID, resp)
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

func addUserContext(guildID string, message *discordgo.MessageCreate) error {
	serverContext, err := db.GetDBService().GetChatHistory(guildID)
	if err != nil {
		return err
	}

	content := fmt.Sprintf("%s (aka %s) said: %s", message.Author.Username, message.Author.DisplayName(), message.Content)

	serverContext = append(serverContext, map[string]string{
		"role":    "user",
		"content": content,
	})
	return db.GetDBService().UpdateChatHistory(guildID, serverContext)
}

func addAssistantContext(guildID, content string) error {
	serverContext, err := db.GetDBService().GetChatHistory(guildID)
	if err != nil {
		return err
	}

	serverContext = append(serverContext, map[string]string{
		"role":    "assistant",
		"content": content,
	})
	return db.GetDBService().UpdateChatHistory(guildID, serverContext)
}

func trimContext(guildID string) error {
	serverContext, err := db.GetDBService().GetChatHistory(guildID)
	if err != nil {
		fmt.Println("Error trimming context:", err)
		return err
	}

	if len(serverContext) > CONTEXT_LIMIT {
		excess := len(serverContext) - CONTEXT_LIMIT
		serverContext = serverContext[excess:]
		return db.GetDBService().UpdateChatHistory(guildID, serverContext)
	}
	return nil
}

func resetContext(guildID string, message *discordgo.MessageCreate) error {
	prompt := message.Content
	if prompt == "reset context" {
		return db.GetDBService().DeleteChatHistory(guildID)
	}
	return nil
}
