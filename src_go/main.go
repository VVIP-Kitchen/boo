package main

import (
	"boo/internal/discord"
	"os"

	"github.com/joho/godotenv"
)

func main() {
	err := godotenv.Load("../.env")
	if err != nil {
		panic("Error loading .env file")
	}
	botToken, ok := os.LookupEnv("DISCORD_MAGI_TOKEN")
	if !ok {
		panic("DISCORD_MAGI_TOKEN not set in environment")
	}

	env, ok := os.LookupEnv("ENVIRONMENT")
	if !ok {
		panic("ENVIRONMENT not set in environment")
	}

	bot := discord.Bot{Token: botToken, Environment: env}
	bot.Run()
}
