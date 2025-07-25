package handler

import (
	"net/http"
	"server/internal/model"
	"server/internal/service"

	"github.com/gin-gonic/gin"
)

type TokenHandler struct {
	service *service.TokenService
}

func NewTokenHandler(service *service.TokenService) *TokenHandler {
	return &TokenHandler{service: service}
}

func (h *TokenHandler) AddTokenUsage(c *gin.Context) {
	var usage model.TokenUsage
	if err := c.ShouldBindJSON(&usage); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	err := h.service.AddTokenUsage(usage)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.Status(http.StatusCreated)
}

func (h *TokenHandler) GetTokenStats(c *gin.Context) {
	guildID := c.Query("guild_id")
	authorID := c.Query("author_id")
	period := c.DefaultQuery("period", "daily")

	stats, err := h.service.GetTokenUsageStats(guildID, authorID, period)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, stats)
}
