package service

import (
	"database/sql"
	"encoding/json"
	"server/internal/database"
)

type ChatHistoryService struct {
	db *sql.DB
}

func NewChatHistoryService(db *sql.DB) *ChatHistoryService {
	return &ChatHistoryService{db: db}
}

func (s *ChatHistoryService) GetChatHistory(guildID string) ([]database.Message, error) {
	rows, err := s.db.Query("SELECT messages FROM chat_history WHERE guild_id = $1", guildID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	if rows.Next() {
		var messagesJSON string
		if err := rows.Scan(&messagesJSON); err != nil {
			return nil, err
		}
		var messages []database.Message
		if err := json.Unmarshal([]byte(messagesJSON), &messages); err != nil {
			return nil, err
		}
		return messages, nil
	}

	return []database.Message{}, nil
}

func (s *ChatHistoryService) UpdateChatHistory(guildID string, messages []database.Message) error {
	messagesJSON, err := json.Marshal(messages)
	if err != nil {
		return err
	}

	_, err = s.db.Exec(`
		INSERT INTO chat_history (guild_id, messages)
		VALUES ($1, $2)
		ON CONFLICT (guild_id)
		DO UPDATE SET messages = $2`,
		guildID, messagesJSON,
	)
	return err
}

func (s *ChatHistoryService) DeleteChatHistory(guildID string) error {
	_, err := s.db.Exec("DELETE FROM chat_history WHERE guild_id = $1", guildID)
	return err
}
