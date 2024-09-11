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

	r := gin.Default()

	r.Static("/static", "./static")
	r.GET("/", func(c *gin.Context) {
		c.File("./static/index.html")
	})

	r.GET("/prompts", promptHandler.ReadAllPrompts)
	r.GET("/prompt", promptHandler.ReadPrompt)
	r.POST("/prompt", promptHandler.AddPrompt)
	r.PUT("/prompt", promptHandler.UpdatePrompt)

	log.Println("Server listening on port 8080")
	log.Fatal(r.Run(":8080"))
}
