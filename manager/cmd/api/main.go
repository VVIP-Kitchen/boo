package main

import (
	"log"

	"server/internal/database"
	"server/internal/handler"
	"server/internal/service"

	"github.com/gin-gonic/gin"
)

func main() {
	db, err := database.NewConnection()
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer db.Close()

	err = database.InitializeSchema(db)
	if err != nil {
		log.Fatalf("Failed to initialize database schema: %v", err)
	}

	promptService := service.NewPromptService(db)
	promptHandler := handler.NewPromptHandler(promptService)

	messageService := service.NewMessageService(db)
	messageHandler := handler.NewMessageHandler(messageService)

	tokenService := service.NewTokenService(db)
	tokenHandler := handler.NewTokenHandler(tokenService)

	r := gin.Default()

	r.Static("/static", "./static")
	r.GET("/", func(c *gin.Context) {
		c.File("./static/index.html")
	})

	// Prompt endpoints
	r.GET("/prompts", promptHandler.ReadAllPrompts)
	r.GET("/prompt", promptHandler.ReadPrompt)
	r.POST("/prompt", promptHandler.AddPrompt)
	r.PUT("/prompt", promptHandler.UpdatePrompt)

	// Message endpoints
	r.POST("/message", messageHandler.AddMessage)

	// Token endpoints
	r.POST("/token", tokenHandler.AddTokenUsage)
	r.GET("/token/stats", tokenHandler.GetTokenStats)

	// Chat history endpoints
	chatHistoryService := service.NewChatHistoryService(db)
	chatHistoryHandler := handler.NewChatHistoryHandler(chatHistoryService)
	r.GET("/chat-history", chatHistoryHandler.GetChatHistory)
	r.PUT("/chat-history", chatHistoryHandler.UpdateChatHistory)
	r.DELETE("/chat-history", chatHistoryHandler.DeleteChatHistory)

	log.Println("Server listening on port 8080")
	log.Fatal(r.Run(":8080"))
}
