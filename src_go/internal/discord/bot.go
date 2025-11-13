package discord

import (
	"boo/internal/discord/handlers"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/bwmarrin/discordgo"
)

type Bot struct {
	Token       string
	Environment string
}

func (b *Bot) Run() {
	discord, err := discordgo.New("Bot " + b.Token)
	if err != nil {
		log.Fatal("Error creating Discord session: ", err)
	}

	discord.Identify.Intents = discordgo.IntentMessageContent |
		discordgo.IntentGuildMessages

	// Register handlers
	discord.AddHandler(ready)
	discord.AddHandler(handlers.Messages)
	discord.AddHandler(handlers.SlashCommands)

	// Open a websocket connection to Discord
	err = discord.Open()
	if err != nil {
		log.Fatal("Error opening connection: ", err)
	}

	//Register slash commands
	for _, cmd := range handlers.Commands {
		_, err := discord.ApplicationCommandCreate(discord.State.User.ID, "", cmd)
		if err != nil {
			log.Fatalf("Cannot create slash command %s: %v", cmd.Name, err)
		}
	}

	defer discord.Close() // Ensure the connection is closed when done

	fmt.Println("Bot is now running. Press CTRL+C to exit.")

	// Listen for interrupt signal (CTRL+C)
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGTERM)
	<-stop

	fmt.Println("Shutting down bot...")
}

func ready(discord *discordgo.Session, event *discordgo.Ready) {
	discord.UpdateGameStatus(0, "with Go!")
}
