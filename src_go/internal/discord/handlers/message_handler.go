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

	history, err := db.GetDBService().GetChatHistory(message.GuildID)
	if err != nil {
		fmt.Println("Error getting chat history:", err)
		return
	}

	resp, err := llm.LLM.ChatCompletion(ctx, state.ServerLore[message.GuildID], history, message.Content)
	if err != nil {
		fmt.Println("Error getting chat completion:", err)
		return
	}
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
