package model

type GuildPrompt struct {
	GuildID     string `json:"guild_id" binding:"required"`
	SystemPrompt string `json:"system_prompt" binding:"required"`
}

type GuildPromptEdit struct {
	SystemPrompt string `json:"system_prompt" binding:"required"`
}