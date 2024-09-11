package service

import (
	"database/sql"
	"server/internal/model"
)

type PromptService struct {
	db *sql.DB
}

func NewPromptService(db *sql.DB) *PromptService {
	return &PromptService{db: db}
}

func (s *PromptService) ReadAllPrompts() ([]model.GuildPrompt, error) {
	var prompts []model.GuildPrompt
	rows, err := s.db.Query("SELECT guild_id, system_prompt FROM boo_prompts")
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var prompt model.GuildPrompt
		err := rows.Scan(&prompt.GuildID, &prompt.SystemPrompt)
		if err != nil {
			return nil, err
		}
		prompts = append(prompts, prompt)
	}

	return prompts, nil
}

func (s *PromptService) ReadPrompt(guildID string) (model.GuildPrompt, error) {
	var prompt model.GuildPrompt
	err := s.db.QueryRow("SELECT guild_id, system_prompt FROM boo_prompts WHERE guild_id = $1", guildID).Scan(&prompt.GuildID, &prompt.SystemPrompt)
	return prompt, err
}

func (s *PromptService) AddPrompt(prompt model.GuildPrompt) error {
	_, err := s.db.Exec("INSERT INTO boo_prompts (guild_id, system_prompt) VALUES ($1, $2)", prompt.GuildID, prompt.SystemPrompt)
	return err
}

func (s *PromptService) UpdatePrompt(guildID string, systemPrompt string) (int64, error) {
	result, err := s.db.Exec("UPDATE boo_prompts SET system_prompt = $1 WHERE guild_id = $2", systemPrompt, guildID)
	if err != nil {
		return 0, err
	}
	return result.RowsAffected()
}
