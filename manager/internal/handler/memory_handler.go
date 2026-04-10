package handler

import (
	"server/internal/model"
	"server/internal/service"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
)

type MemoryHandler struct {
	service *service.MemoryService
}

func NewMemoryHandler(service *service.MemoryService) *MemoryHandler {
	return &MemoryHandler{service: service}
}

func (h *MemoryHandler) AddMemory(c *gin.Context) {
	var memory model.UserMemory
	if err := c.ShouldBindJSON(&memory); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	id, err := h.service.AddMemory(memory)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, gin.H{"id": id})
}

func (h *MemoryHandler) GetMemories(c *gin.Context) {
	guildID := c.Query("guild_id")
	authorID := c.Query("author_id")
	if guildID == "" || authorID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "guild_id and author_id are required"})
		return
	}

	memories, err := h.service.GetMemories(guildID, authorID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if memories == nil {
		memories = []model.UserMemoryResponse{}
	}

	c.JSON(http.StatusOK, memories)
}

func (h *MemoryHandler) GetRecentMemories(c *gin.Context) {
	guildID := c.Query("guild_id")
	if guildID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "guild_id is required"})
		return
	}

	limitStr := c.DefaultQuery("limit", "50")
	limit, _ := strconv.Atoi(limitStr)

	memories, err := h.service.GetRecentMemories(guildID, limit)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if memories == nil {
		memories = []model.UserMemoryResponse{}
	}

	c.JSON(http.StatusOK, memories)
}

func (h *MemoryHandler) DeleteMemory(c *gin.Context) {
	idStr := c.Query("id")
	if idStr == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "id is required"})
		return
	}

	id, _ := strconv.ParseInt(idStr, 10, 64)
	rows, err := h.service.DeleteMemory(id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if rows == 0 {
		c.JSON(http.StatusNotFound, gin.H{"error": "Memory not found"})
		return
	}

	c.Status(http.StatusOK)
}

func (h *MemoryHandler) UpdateMemory(c *gin.Context) {
	idStr := c.Query("id")
	if idStr == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "id is required"})
		return
	}

	id, _ := strconv.ParseInt(idStr, 10, 64)

	var req struct {
		Fact string `json:"fact"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	rows, err := h.service.UpdateMemory(id, req.Fact)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if rows == 0 {
		c.JSON(http.StatusNotFound, gin.H{"error": "Memory not found"})
		return
	}

	c.Status(http.StatusOK)
}

func (h *MemoryHandler) SearchMemories(c *gin.Context) {
	guildID := c.Query("guild_id")
	if guildID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "guild_id is required"})
		return
	}

	authorID := c.Query("author_id")
	query := c.Query("q")
	if query == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "q (query) is required"})
		return
	}

	memories, err := h.service.SearchMemories(guildID, authorID, query)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if memories == nil {
		memories = []model.UserMemoryResponse{}
	}

	c.JSON(http.StatusOK, memories)
}

func (h *MemoryHandler) GetMemoryByID(c *gin.Context) {
	idStr := c.Query("id")
	if idStr == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "id is required"})
		return
	}

	id, _ := strconv.ParseInt(idStr, 10, 64)

	memory, err := h.service.GetMemoryByID(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Memory not found"})
		return
	}

	c.JSON(http.StatusOK, memory)
}