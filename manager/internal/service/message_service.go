package service

import (
	"database/sql"
	"server/internal/model"
)

type MessageService struct {
	db *sql.DB
}

func NewMessageService(db *sql.DB) *MessageService {
	return &MessageService{db: db}
}

func (s *MessageService) AddMessage(msg model.DiscordMessage) error {
	_, err := s.db.Exec("INSERT INTO discord_messages (message_id, server_name, channel_name, channel_id, author_name, author_nickname, author_id, message_content) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)", msg.MessageID, msg.ServerName, msg.ChannelName, msg.ChannelID, msg.AuthorName, msg.AuthorNickname, msg.AuthorID, msg.MessageContent)
	return err
}
