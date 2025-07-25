package service

import (
	"database/sql"
	"fmt"
	"server/internal/model"
)

type TokenService struct {
	db *sql.DB
}

func NewTokenService(db *sql.DB) *TokenService {
	return &TokenService{db: db}
}

func (s *TokenService) AddTokenUsage(usage model.TokenUsage) error {
	_, err := s.db.Exec(`
		INSERT INTO token_usage (message_id, guild_id, author_id, input_tokens, output_tokens)
		VALUES ($1, $2, $3, $4, $5)
	`, usage.MessageID, usage.GuildID, usage.AuthorID, usage.InputTokens, usage.OutputTokens)
	return err
}

func (s *TokenService) GetTokenUsageStats(guildID, authorID, period string) ([]model.TokenUsage, error) {
	var rows *sql.Rows
	var err error

	query := `
		SELECT message_id, guild_id, author_id, input_tokens, output_tokens, timestamp
		FROM token_usage
		WHERE guild_id = $1 AND author_id = $2 AND timestamp >= NOW() - INTERVAL '%s'
	`
	switch period {
	case "daily":
		rows, err = s.db.Query(fmt.Sprintf(query, "1 day"), guildID, authorID)
	case "weekly":
		rows, err = s.db.Query(fmt.Sprintf(query, "7 days"), guildID, authorID)
	case "monthly":
		rows, err = s.db.Query(fmt.Sprintf(query, "30 days"), guildID, authorID)
	default:
		rows, err = s.db.Query(fmt.Sprintf(query, "365 days"), guildID, authorID)
	}

	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var usages []model.TokenUsage
	for rows.Next() {
		var usage model.TokenUsage
		err := rows.Scan(&usage.MessageID, &usage.GuildID, &usage.AuthorID, &usage.InputTokens, &usage.OutputTokens, &usage.Timestamp)
		if err != nil {
			return nil, err
		}
		usages = append(usages, usage)
	}
	return usages, nil
}
