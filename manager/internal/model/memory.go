package model

type UserMemory struct {
	GuildID    string `json:"guild_id" binding:"required"`
	AuthorID   string `json:"author_id" binding:"required"`
	AuthorName string `json:"author_name" binding:"required"`
	Fact       string `json:"fact" binding:"required"`
}

type UserMemoryResponse struct {
	ID         int    `json:"id"`
	GuildID    string `json:"guild_id"`
	AuthorID   string `json:"author_id"`
	AuthorName string `json:"author_name"`
	Fact       string `json:"fact"`
	CreatedAt  string `json:"created_at"`
}