# <img src="./assets/boo.png" alt="Boo" width="40" height="40" style="border-radius:50%; vertical-align:text-top;" /> Boo — the (un)friendly Discord AI bot

Boo is a snark-powered Discord bot that blends LLM chat, image understanding, and handy utilities into a single docker-compose stack. It’s built for discord servers that want a fast, context-aware assistant with guardrails, a tiny admin API, and a smooth UX.

- Conversational AI with per-guild system prompts
- Automatic image captioning/analysis, with generation workflows
- Short-term context in Redis for channel summaries
- Long-term storage and editable prompts in Postgres (via a lightweight Go API + web UI)
- GIFs, weather, pings, bonks, and more ...

---

## ✨ Features at a glance

| Category  | What Boo does                                                                                                                                                      |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| AI chat   | Conversational replies via OpenRouter, per-server editable system prompt, mentions/replies/DM support, rolling context from Redis |
| Vision    | Auto image caption/analysis on upload                                                                       |
| Utilities | `/weather`, `/bonk @user`, `/ping`, `/skibidi`, `/get_prompt`, `/summary`                                                                                |
| UX & Mod  | ["Guys-check" for inclusive language nudges](https://github.com/VVIP-Kitchen/boo/issues/31), oversized replies sent as text attachments, supports stickers and custom emojis                                        |
| Admin     | `!@sync` to refresh slash commands, prompt editor served by the Go manager on http://localhost:8080                                                         |

---

## 🏗 Repository layout

```
.
├─ compose.yml           # 4 services: postgres, redis, manager, discord-bot
├─ Dockerfile            # Python 3.12 (uv) base for the bot
├─ src/                  # Discord bot (Python / discord.py 2.5)
├─ manager/              # Go API + static Tailwind UI for prompts and token stats
└─ assets/               # diagrams and images
```

---

## ⚙️ Architecture

![](./assets/architecture.png)
- **`bot`**: Python 3.12 container with cogs, tools, and all commands
- **`manager`**: Go (Gin) API for prompts/messages/tokens + static prompt editor
- **`redis`**: 15-minute rolling message buffer per channel for AI summaries
- **`postgres`**: persistent storage (prompts, messages, token usage)

---

## 🚀 Quick start (Docker)

1. Clone the repo

```
git clone https://github.com/VVIP-Kitchen/boo.git
cd boo
```

2. Create a .env file (see sample below)

3. Bring the stack up

```
docker compose up -d
```

When the Discord gateway connects, the bot goes online. Open http://localhost:8080 to view or edit per-guild system prompts.

### .env sample

```
# Discord
DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN
ADMIN_LIST=123456789012345678,987654321098765432
CONTEXT_LIMIT=40

# APIs
TENOR_API_KEY=XXXXXXXXXXXX
TOMORROW_IO_API_KEY=XXXXXXXXXXXX
OPENROUTER_API_KEY=XXXXXXXXXXXX
OPENROUTER_MODEL=meta-llama/llama-4-maverick
TAVILY_API_KEY=XXXXXXXXXXXX

# Database (compose wires these for containers)
POSTGRES_USER=db-user
POSTGRES_PASSWORD=db-password
POSTGRES_DB=db-name
```

The compose file wires these services for the bot:

```
postgres:5432, redis:6379, manager:8080
```

---

## 🛠 Running locally (without Docker)

```
# Python venv
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start Redis and Postgres locally (or disable features that need them)
export $(cat .env | xargs)
python src/main.py
```

Run the Go manager separately:

```
cd manager
go run ./cmd/api
```

---

## 🗨 Commands

| Trigger          | Description                             |
| ---------------- | --------------------------------------- |
| `/ping`          | Check latency                           |
| `/skibidi`       | Ritual noises                           |
| `/weather`       | Realtime weather via Tomorrow.io        |
| `/bonk @user`    | Random Tenor bonk GIF                   |
| `/summary`       | TL;DR of last 15 minutes in the channel |
| `/get_prompt`    | Download the current system prompt      |
| `/update_prompt` | Update system prompt from uploaded file |
| `/add_prompt`    | Add system prompt from uploaded file    |
| `reset chat`     | Type in channel to clear context buffer |
| `!@sync`         | Owner-only; resync slash commands       |

Notes:

- Context is kept per-guild; DMs are supported with a separate context.
- Image uploads are analyzed automatically; multi-image messages are processed in sequence.
- Oversized replies are delivered as `.txt` attachments.

---

## 🔐 Permissions and configuration

- ADMIN_LIST controls privileged commands like sync. Comma-separated user IDs are required.
- The bot requests message content and presence intents for context and UX features.
- Rate-limit handling: if OpenRouter returns 429, Boo relays the retry ETA.

---

## 📦 Manager API (Go)

Endpoints (served on port 8080 inside the network; mapped to localhost:8080 via compose):

- `GET /prompt?guild_id=…` — fetch per-guild system prompt
- `POST /prompt` — add prompt
- `PUT /prompt?guild_id=…` — update prompt
- `POST /message` — archive messages (write-only)
- `POST /token` — record token usage
- `GET /token/stats?guild_id=…&author_id=…&period=[daily|weekly|monthly|yearly]` — usage stats

A minimal Tailwind UI is served as static files for prompt editing.

---

## 🧩 Extensibility

- Add commands: create a new cog in src/commands and load it in bot/bot.py.
- Swap LLMs: change OPENROUTER_MODEL or extend LLMService for different providers/tools.
- Storage: extend manager/internal services and the Python DBService to track more analytics.
- Emoji/stickers: tweak utils/emoji_utils.py to adjust patterns and rendering.

---

## 🤝 Contributing

See [CONTRIBUTING](./CONTRIBUTING.md)

---

## 📄 License

MIT. Summon responsibly.

---

## ⚙️ Tech Stack

- Python 3.12, discord.py 2.5
- OpenRouter (LLM chat + vision)
- Redis, Postgres
- Go (Gin) manager with Tailwind UI
- Docker Compose

---

## 🌐 DeepWiki

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/VVIP-Kitchen/boo)
