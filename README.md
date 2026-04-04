# Daystrom v2

Intelligent todo & idea capture that learns from you.

A self-hosted Docker stack with a SvelteKit PWA frontend, FastAPI backend, and local AI via Ollama. No cloud dependencies — your data stays on your hardware.

## Features

- **Instant capture** — Type naturally. Items are stored in <100ms, then enriched asynchronously by AI.
- **Auto-categorization** — Items are classified by type (task, idea, note, event, reference), tagged, and prioritized automatically.
- **Persistent memory** — Daystrom extracts durable facts from your items and remembers them across sessions.
- **Semantic search** — Find anything by meaning, not just keywords, via pgvector embeddings.
- **Chat mode** — Have a conversation with Daystrom. It can create items, search your data, and reason about your tasks.
- **Autonomous agents** — Actionable items ("research X", "compare Y vs Z") automatically spawn agents that work in the background and report results.
- **Learning system** — Tracks your corrections, tag preferences, and behavioral patterns to improve over time.
- **Daily digest** — Activity summary with overdue items, completions, and tag merge suggestions.
- **Offline support** — Service worker caches the app shell and queues captures when offline, syncing when connectivity returns.
- **PWA-ready** — Install on your iPhone home screen for a native-feeling experience with safe area support.
- **Real-time updates** — Server-Sent Events push enrichment results and agent progress live to the UI.

## Prerequisites

- **Docker** (v20.10+) and **Docker Compose** (v2.0+)
- **Ollama** running on your server (or any machine reachable from Docker)

### Install Docker

**Linux (Ubuntu/Debian):**
```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in for group change to take effect

# Docker Compose is included with Docker Engine 20.10+
# Verify:
docker compose version
```

**macOS:**
```bash
# Install Docker Desktop (includes Compose)
brew install --cask docker
# Or download from https://docs.docker.com/desktop/install/mac-install/
```

**Windows:**
```
# Install Docker Desktop (includes Compose)
# Download from https://docs.docker.com/desktop/install/windows-install/
# Enable WSL 2 backend during setup
```

### Install Ollama

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Then pull the required models:
ollama pull gemma4:e4b
ollama pull nomic-embed-text
```

Ollama needs to be running and accessible from Docker. If Ollama is on the same machine, `http://host.docker.internal:11434` works on Docker Desktop. On Linux without Docker Desktop, use your host's LAN IP (e.g., `http://192.168.1.50:11434`).

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/mfbergmann/daystrom.git
cd daystrom

# 2. Configure environment
cp .env.example .env
```

Edit `.env` with your settings:

```env
DB_PASSWORD=daystrom              # PostgreSQL password
SECRET_KEY=change-me-to-random    # JWT signing key
PIN=1234                          # App login PIN (leave empty to disable auth)

OLLAMA_BASE_URL=http://host.docker.internal:11434  # Ollama URL
OLLAMA_MODEL=gemma4:e4b                            # Chat/classification model
OLLAMA_EMBED_MODEL=nomic-embed-text                # Embedding model
```

```bash
# 3. Build and start
docker compose up -d

# 4. Check status
docker compose ps
docker compose logs -f backend   # Watch backend logs
```

The app is available at **http://localhost:3000**.

### Accessing via Tailscale

If running on a homelab, access via your Tailscale IP:

```
http://<tailscale-ip>:3000
```

On iPhone, open in Safari and tap **Share > Add to Home Screen** to install as a PWA.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend   │────▶│   Backend   │────▶│   Ollama    │
│  SvelteKit   │     │   FastAPI   │     │  (external) │
│  :3000       │◀────│   :8000     │     └─────────────┘
└─────────────┘  SSE └──────┬──────┘
                            │
                    ┌───────┴───────┐
                    │               │
              ┌─────▼─────┐  ┌─────▼─────┐
              │  Postgres  │  │   Redis   │
              │  pgvector  │  │  pub/sub  │
              │  :5432     │  │  + queue  │
              └───────────┘  └───────────┘
                                   │
                            ┌──────▼──────┐
                            │   Worker    │
                            │ enrichment  │
                            │ + agents    │
                            └─────────────┘
```

| Service | Image | Purpose |
|---------|-------|---------|
| **frontend** | SvelteKit (Node 22) | PWA interface (port 3000) |
| **backend** | FastAPI (Python 3.12) | REST API server (port 8000) |
| **worker** | Same as backend | Background enrichment, agents, learning sweep |
| **db** | pgvector/pgvector:pg17 | PostgreSQL with vector similarity search |
| **redis** | redis:7-alpine | Job queue (ARQ) + SSE event bus |

### How It Works

1. **Capture** — You type naturally. The item is stored instantly and an enrichment job is queued.
2. **Enrich** — The worker classifies the item (type, tags, priority, due date), generates an embedding, and extracts memory facts — all via your local Ollama instance.
3. **Learn** — Every interaction (completions, tag edits, classification corrections) is tracked. A daily sweep discovers associations, decays old memories, and refines the behavioral model.
4. **Act** — Items flagged as actionable ("research X") automatically spawn agent tasks that execute multi-step plans using tools (search memory, create notes, summarize).
5. **Chat** — Ask Daystrom anything in chat mode. It has full context of your items, memories, and patterns, and can create items or search on your behalf.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/items/capture` | Quick capture (returns <100ms) |
| `GET` | `/api/items` | List items (filter by status, type, tag) |
| `PATCH` | `/api/items/:id` | Update item |
| `DELETE` | `/api/items/:id` | Archive item |
| `GET` | `/api/search?q=` | Hybrid semantic + full-text search |
| `POST` | `/api/chat` | Chat (JSON or streaming SSE) |
| `GET` | `/api/conversations` | List conversations |
| `GET` | `/api/agent-tasks` | List agent tasks |
| `POST` | `/api/agent-tasks` | Create agent task |
| `GET` | `/api/memories` | List memory facts |
| `GET` | `/api/learning/digest` | Daily activity digest |
| `GET` | `/api/learning/model` | Behavioral model |
| `GET` | `/api/events` | SSE stream (real-time updates) |
| `GET` | `/api/health` | Health check |

## Development

### Running Tests

```bash
cd backend
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx aiosqlite
python -m pytest tests/ -v
```

Tests use an in-memory SQLite database with pgvector types patched to Text columns. Some tests that require nested async queries are marked `xfail` (they pass on PostgreSQL).

### Project Structure

```
daystrom/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                 # FastAPI app
│   │   ├── core/                   # Config, DB, security
│   │   ├── models/                 # SQLAlchemy models
│   │   ├── routers/                # API endpoints
│   │   ├── services/               # Business logic
│   │   │   ├── ai_service.py       # Ollama wrapper
│   │   │   ├── capture_service.py  # Two-phase capture
│   │   │   ├── chat_service.py     # Chat + tool use
│   │   │   ├── agent_service.py    # Autonomous agents
│   │   │   ├── classifier.py       # LLM classification
│   │   │   ├── embedding_service.py# Semantic search
│   │   │   ├── memory_service.py   # Persistent memory
│   │   │   ├── context_service.py  # LLM context assembly
│   │   │   └── learning_service.py # Behavioral model
│   │   ├── workers/                # Background jobs
│   │   └── schemas/                # Pydantic models
│   └── tests/
├── frontend/
│   ├── Dockerfile
│   ├── src/
│   │   ├── routes/                 # Pages (inbox, active, chat, agents, search, settings)
│   │   └── lib/                    # API client, stores, SSE
│   └── static/
│       ├── manifest.json
│       └── service-worker.js       # Offline support
└── README.md
```

## Troubleshooting

**Ollama not reachable from Docker:**
- On Docker Desktop: use `http://host.docker.internal:11434`
- On Linux: use your host's IP (e.g., `http://192.168.1.50:11434`)
- Ensure Ollama is listening on `0.0.0.0`: set `OLLAMA_HOST=0.0.0.0` before starting Ollama

**Models not loading:**
```bash
# Check Ollama has the models
ollama list
# Pull if missing
ollama pull gemma4:e4b
ollama pull nomic-embed-text
```

**Database issues:**
```bash
# Reset the database (destroys all data)
docker compose down -v
docker compose up -d
```

**View logs:**
```bash
docker compose logs -f backend worker
```
