package model

type TokenUsage struct {
	MessageID    string `json:"message_id" binding:"required"`
	GuildID      string `json:"guild_id" binding:"required"`
	AuthorID     string `json:"author_id" binding:"required"`
	InputTokens  int    `json:"input_tokens"`
	OutputTokens int    `json:"output_tokens"`
	Timestamp    string `json:"timestamp"`
}
