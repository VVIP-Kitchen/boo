package main

import (
	"log"
	"os"

	"server/internal/database"
	"server/internal/handler"
	"server/internal/middleware"
	"server/internal/service"

	"github.com/gin-gonic/gin"
)

func main() {
	authToken := os.Getenv("MANAGER_API_TOKEN")
	if authToken == "" {
		log.Fatal("MANAGER_API_TOKEN environment variable is required")
	}

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
	r.GET("/docs", func(c *gin.Context) {
		c.File("./static/swagger.html")
	})
	r.GET("/openapi.json", func(c *gin.Context) {
		c.File("./static/openapi.json")
	})

	protected := r.Group("/", middleware.NewAuthMiddleware(authToken))

	// Prompt endpoints
	protected.GET("/prompts", promptHandler.ReadAllPrompts)
	protected.GET("/prompt", promptHandler.ReadPrompt)
	protected.POST("/prompt", promptHandler.AddPrompt)
	protected.PUT("/prompt", promptHandler.UpdatePrompt)

	// Message endpoints
	protected.POST("/message", messageHandler.AddMessage)

	// Token endpoints
	protected.POST("/token", tokenHandler.AddTokenUsage)
	protected.GET("/token/stats", tokenHandler.GetTokenStats)

	// Chat history endpoints
	chatHistoryService := service.NewChatHistoryService(db)
	chatHistoryHandler := handler.NewChatHistoryHandler(chatHistoryService)
	protected.GET("/chat-history", chatHistoryHandler.GetChatHistory)
	protected.PUT("/chat-history", chatHistoryHandler.UpdateChatHistory)
	protected.DELETE("/chat-history", chatHistoryHandler.DeleteChatHistory)

	log.Println("Server listening on port 8080")
	log.Fatal(r.Run(":8080"))
}
