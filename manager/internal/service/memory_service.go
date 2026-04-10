package service

import (
	"database/sql"
	"server/internal/model"
)

type MemoryService struct {
	db *sql.DB
}

func NewMemoryService(db *sql.DB) *MemoryService {
	return &MemoryService{db: db}
}

func (s *MemoryService) AddMemory(memory model.UserMemory) (int64, error) {
	var id int64
	err := s.db.QueryRow(
		"INSERT INTO user_memories (guild_id, author_id, author_name, fact) VALUES ($1, $2, $3, $4) RETURNING id",
		memory.GuildID, memory.AuthorID, memory.AuthorName, memory.Fact,
	).Scan(&id)
	return id, err
}

func (s *MemoryService) GetMemories(guildID, authorID string) ([]model.UserMemoryResponse, error) {
	rows, err := s.db.Query(
		"SELECT id, guild_id, author_id, author_name, fact, created_at FROM user_memories WHERE guild_id = $1 AND author_id = $2 ORDER BY created_at DESC LIMIT 50",
		guildID, authorID,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var memories []model.UserMemoryResponse
	for rows.Next() {
		var m model.UserMemoryResponse
		err := rows.Scan(&m.ID, &m.GuildID, &m.AuthorID, &m.AuthorName, &m.Fact, &m.CreatedAt)
		if err != nil {
			return nil, err
		}
		memories = append(memories, m)
	}
	return memories, nil
}

func (s *MemoryService) GetRecentMemories(guildID string, limit int) ([]model.UserMemoryResponse, error) {
	rows, err := s.db.Query(
		"SELECT id, guild_id, author_id, author_name, fact, created_at FROM user_memories WHERE guild_id = $1 ORDER BY created_at DESC LIMIT $2",
		guildID, limit,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var memories []model.UserMemoryResponse
	for rows.Next() {
		var m model.UserMemoryResponse
		err := rows.Scan(&m.ID, &m.GuildID, &m.AuthorID, &m.AuthorName, &m.Fact, &m.CreatedAt)
		if err != nil {
			return nil, err
		}
		memories = append(memories, m)
	}
	return memories, nil
}

func (s *MemoryService) DeleteMemory(id int64) (int64, error) {
	result, err := s.db.Exec("DELETE FROM user_memories WHERE id = $1", id)
	if err != nil {
		return 0, err
	}
	return result.RowsAffected()
}