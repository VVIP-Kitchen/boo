package database

import "time"

type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type UserMemory struct {
	ID         int       `json:"id"`
	GuildID    string    `json:"guild_id"`
	AuthorID   string    `json:"author_id"`
	AuthorName string    `json:"author_name"`
	Fact       string    `json:"fact"`
	CreatedAt  time.Time `json:"created_at"`
}
