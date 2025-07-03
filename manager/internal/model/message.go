package model

type DiscordMessage struct {
	MessageID      string `json:"message_id" binding:"required"`
	ServerName     string `json:"server_name" binding:"required"`
	ChannelName    string `json:"channel_name" binding:"required"`
	ChannelID      string `json:"channel_id" binding:"required"`
	AuthorName     string `json:"author_name" binding:"required"`
	AuthorNickname string `json:"author_nickname"` // Optional
	AuthorID       string `json:"author_id" binding:"required"`
	MessageContent string `json:"message_content" binding:"required"`
	Timestamp      string `json:"timestamp"` // Optional; if not provided, defaults to current time
}
