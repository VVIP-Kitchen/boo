package handler

import (
	"net/http"
	"server/internal/database"
	"server/internal/service"

	"github.com/gin-gonic/gin"
)

type ChatHistoryHandler struct {
	service *service.ChatHistoryService
}

func NewChatHistoryHandler(service *service.ChatHistoryService) *ChatHistoryHandler {
	return &ChatHistoryHandler{service: service}
}

func (h *ChatHistoryHandler) GetChatHistory(c *gin.Context) {
	guildID := c.Query("guild_id")
	if guildID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "guild_id is required"})
		return
	}

	messages, err := h.service.GetChatHistory(guildID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get chat history"})
		return
	}

	c.JSON(http.StatusOK, messages)
}

func (h *ChatHistoryHandler) UpdateChatHistory(c *gin.Context) {
	guildID := c.Query("guild_id")
	if guildID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "guild_id is required"})
		return
	}

	var messages []database.Message
	if err := c.ShouldBindJSON(&messages); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
		return
	}

	if err := h.service.UpdateChatHistory(guildID, messages); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update chat history"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Chat history updated successfully"})
}

func (h *ChatHistoryHandler) DeleteChatHistory(c *gin.Context) {
	guildID := c.Query("guild_id")
	if guildID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "guild_id is required"})
		return
	}

	if err := h.service.DeleteChatHistory(guildID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete chat history"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Chat history deleted successfully"})
}
