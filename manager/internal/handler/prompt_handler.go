package handler

import (
	"database/sql"
	"server/internal/model"
	"server/internal/service"
	"net/http"

	"github.com/gin-gonic/gin"
)

type PromptHandler struct {
	service *service.PromptService
}

func NewPromptHandler(service *service.PromptService) *PromptHandler {
	return &PromptHandler{service: service}
}

func (h *PromptHandler) ReadAllPrompts(c *gin.Context) {
	prompts, err := h.service.ReadAllPrompts()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, prompts)
}

func (h *PromptHandler) ReadPrompt(c *gin.Context) {
	guildID := c.Query("guild_id")
	if guildID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "guild_id is required"})
		return
	}

	prompt, err := h.service.ReadPrompt(guildID)
	if err != nil {
		if err == sql.ErrNoRows {
			c.JSON(http.StatusNotFound, gin.H{"error": "Prompt not found"})
		} else {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		}
		return
	}

	c.JSON(http.StatusOK, prompt)
}

func (h *PromptHandler) AddPrompt(c *gin.Context) {
	var prompt model.GuildPrompt
	if err := c.ShouldBindJSON(&prompt); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	err := h.service.AddPrompt(prompt)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.Status(http.StatusCreated)
}

func (h *PromptHandler) UpdatePrompt(c *gin.Context) {
	guildID := c.Query("guild_id")
	if guildID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "guild_id is required"})
		return
	}

	var prompt model.GuildPromptEdit
	if err := c.ShouldBindJSON(&prompt); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	rowsAffected, err := h.service.UpdatePrompt(guildID, prompt.SystemPrompt)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if rowsAffected == 0 {
		c.JSON(http.StatusNotFound, gin.H{"error": "Prompt not found"})
		return
	}

	c.Status(http.StatusOK)
}