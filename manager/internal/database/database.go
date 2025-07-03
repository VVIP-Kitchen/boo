package database

import (
	"database/sql"
	"fmt"
	"log"
	"os"

	_ "github.com/lib/pq"
)

func NewConnection() (*sql.DB, error) {
	host := os.Getenv("DB_HOST")
	port := os.Getenv("DB_PORT")
	user := os.Getenv("DB_USER")
	password := os.Getenv("DB_PASSWORD")
	dbname := os.Getenv("DB_NAME")
	connStr := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable", host, port, user, password, dbname)

	db, err := sql.Open("postgres", connStr)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	return db, nil
}

func InitializeSchema(db *sql.DB) error {
	query := `
	CREATE TABLE IF NOT EXISTS boo_prompts (
		guild_id TEXT PRIMARY KEY,
		system_prompt TEXT NOT NULL
	);

	CREATE TABLE IF NOT EXISTS discord_messages (
		message_id TEXT PRIMARY KEY,
		server_name TEXT NOT NULL,
		channel_name TEXT NOT NULL,
		channel_id TEXT NOT NULL,
		author_name TEXT NOT NULL,
		author_nickname TEXT,
		author_id TEXT NOT NULL,
		message_content TEXT NOT NULL,
		timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
	);
	`

	_, err := db.Exec(query)
	if err != nil {
		log.Printf("Error creating tables: %v", err)
		return err
	}

	log.Println("Database schema initialized successfully")
	return nil
}
