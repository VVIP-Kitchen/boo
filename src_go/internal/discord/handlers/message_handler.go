package handlers

import (
	"fmt"
	"os"

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

	fmt.Println("Received Message", message.Author.DisplayName())

	// responding with dummy text with typing indicator
	discord.ChannelTyping(message.ChannelID)
	discord.ChannelMessageSend(message.ChannelID, "Hello! This is a response from the Go Discord bot.")
}
