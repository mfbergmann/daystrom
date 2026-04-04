# Daystrom v2

Intelligent todo & idea capture that learns from you.

Self-hosted Docker stack with a SvelteKit PWA frontend, FastAPI backend, and local AI via Ollama.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- [Ollama](https://ollama.ai) running on your server with `gemma4:e4b` and `nomic-embed-text` models

```bash
# Pull the required models
ollama pull gemma4:e4b
ollama pull nomic-embed-text
```

### Run

```bash
cp .env.example .env
# Edit .env with your settings (PIN, Ollama URL, etc.)
docker compose up -d
```

The app will be available at `http://localhost:3000`.

## Architecture

| Service | Purpose |
|---------|---------|
| **frontend** | SvelteKit PWA (port 3000) |
| **backend** | FastAPI API server (port 8000) |
| **worker** | Background AI enrichment & agent tasks |
| **db** | PostgreSQL 17 + pgvector |
| **redis** | Job queue + SSE pub/sub |

### How It Works

1. **Capture** — Type naturally. Items are stored instantly (<100ms).
2. **Enrich** — A background worker classifies, tags, and embeds each item via Ollama.
3. **Learn** — The system extracts memory facts, discovers associations, and tracks your patterns.
4. **Act** — Actionable items spawn autonomous agents that research and report back.

### Key Features

- Two-phase capture pipeline (instant entry + async AI enrichment)
- Persistent memory system that grows smarter over time
- Semantic search via pgvector embeddings
- Auto-categorization with evolving tags
- Autonomous agent system for research tasks
- Real-time updates via Server-Sent Events
- PWA-ready for iOS home screen
