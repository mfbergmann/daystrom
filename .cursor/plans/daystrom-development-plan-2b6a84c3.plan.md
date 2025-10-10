<!-- 2b6a84c3-1608-4c6b-80ce-a23dadec9d76 916450bc-6b55-448d-bd0f-f5292c05e317 -->
# Daystrom Development Plan

## Architecture Overview

**Backend**: Python + FastAPI
**Database**: PostgreSQL + pgvector extension for semantic search
**AI**: OpenAI API (gpt-4o for general tasks, o1-preview for complex reasoning, text-embedding-3-large for embeddings)
**Interface**: Telegram Bot
**Calendars**: Google Calendar API + CalDAV (for Apple Calendar)
**Deployment**: Self-hosted on VPS

## Phase 1: Foundation & Core Infrastructure

### 1.1 Project Setup

- Initialize Python project with FastAPI, SQLAlchemy, and async support
- Set up PostgreSQL database with pgvector extension
- Create environment configuration (`.env` for API keys, database credentials)
- Establish project structure: `app/`, `models/`, `services/`, `bot/`, `migrations/`

### 1.2 Database Schema

- **Items table**: Store captured thoughts (id, content, item_type, created_at, metadata)
- **Embeddings table**: Vector embeddings for semantic search (item_id, embedding vector)
- **Users table**: User preferences and settings
- **Tags table**: Extracted tags and counterparties
- **Calendar_events table**: Cached calendar data for context awareness

### 1.3 OpenAI Integration

- Create service layer for OpenAI API calls
- Implement function to get embeddings (text-embedding-3-large or latest)
- Implement chat completion for classification and extraction
- Use structured outputs/function calling for extracting: item_type, due_date, tags, counterparties
- Verify latest model naming (gpt-4o, o1-preview, or gpt-5 if available)

## Phase 2: Telegram Bot Interface

### 2.1 Basic Bot Setup

- Register bot with Telegram BotFather
- Implement webhook receiver in FastAPI
- Handle text messages: capture and store raw input
- Return simple acknowledgment to user

### 2.2 Multi-Modal Input

- **Voice notes**: Use Telegram voice file download + OpenAI Whisper API for transcription
- **Photos**: Download images, use OpenAI Vision API to extract text/context
- Store original media references alongside transcribed content

### 2.3 Bot Commands

- `/start` - Initialize user and explain capabilities
- `/search <query>` - Semantic search across past notes
- `/digest` - Generate summary of recent items
- `/brainstorm <topic>` - Surface related notes and connections

## Phase 3: Intelligence Layer

### 3.1 Automatic Understanding

- On item capture, use OpenAI to classify into: idea, task, event, reference
- Extract structured data: due dates, priority, tags, people mentioned
- Generate embedding and store in pgvector
- Create function calling schema for consistent extraction

### 3.2 Semantic Search

- Implement vector similarity search using pgvector's `<=>` operator
- Create hybrid search: combine semantic + keyword filtering
- Return top-N relevant items with context snippets

### 3.3 Memory Consolidation

- Daily job to analyze related items and suggest connections
- Identify duplicate or similar tasks for consolidation
- Tag extraction using NER or OpenAI function calling

## Phase 4: Calendar Integration

### 4.1 Google Calendar

- Implement OAuth2 flow for Google Calendar API
- Fetch events for next 7 days
- Store in local cache with refresh logic
- Check for conflicts when suggesting task timing

### 4.2 Apple Calendar (CalDAV)

- Implement CalDAV client using `caldav` Python library
- Authenticate with iCloud credentials
- Sync events bidirectionally
- Merge Google + Apple calendar views for complete context

### 4.3 Context Awareness

- Before sending digests, check calendar density
- Avoid reminders during busy calendar blocks
- Suggest task scheduling in free slots

## Phase 5: Proactive Features

### 5.1 Digests

- Daily digest: pending tasks, upcoming events, recent ideas
- Weekly digest: broader overview with trends
- Use OpenAI to format digest in natural, conversational tone
- Adjust length based on calendar availability

### 5.2 Smart Reminders

- Store user-defined or AI-extracted reminder times
- Background task scheduler (using APScheduler or Celery)
- Send reminder via Telegram at appropriate time
- Learn from snooze/dismiss patterns to optimize timing

### 5.3 Conversational Brainstorming

- When user initiates brainstorm mode, retrieve semantically similar items
- Use OpenAI to generate connections and suggestions
- Multi-turn conversation with context retention
- Surface forgotten related ideas automatically

## Phase 6: Adaptation & Learning

### 6.1 Interaction Tracking

- Log all user interactions: completions, snoozes, dismissals, edits
- Track which digest formats get most engagement
- Monitor which reminder times are most effective

### 6.2 Behavior Adjustment

- Implement simple scoring system for item priority based on interaction history
- Adjust digest length based on user read/ignore patterns
- Tune reminder timing using historical response data
- Store learned preferences in user settings

### 6.3 Feedback Loop

- Allow explicit feedback commands: `/helpful`, `/not-helpful`
- Incorporate feedback into prioritization algorithm
- Gradually refine classification accuracy

## Phase 7: Deployment & Operations

### 7.1 VPS Setup

- Install PostgreSQL with pgvector extension
- Set up Python environment with virtualenv
- Configure systemd service for FastAPI application
- Set up nginx reverse proxy with SSL (Let's Encrypt)

### 7.2 Monitoring & Logging

- Implement structured logging (using `loguru` or Python `logging`)
- Set up health check endpoint
- Monitor OpenAI API usage and costs
- Error tracking and alerting via Telegram

### 7.3 Security

- Encrypt sensitive data at rest (API keys, calendar credentials)
- Use environment variables for secrets
- Implement rate limiting on Telegram webhook
- Regular database backups

### 7.4 Maintenance Tasks

- Automated database backups (daily)
- Log rotation
- Vector index optimization
- Calendar cache refresh

## Key Files to Create

- `main.py` - FastAPI app entry point
- `app/bot/telegram_handler.py` - Telegram webhook and message processing
- `app/services/openai_service.py` - OpenAI API wrapper
- `app/services/calendar_service.py` - Calendar integration
- `app/services/memory_service.py` - Semantic search and storage
- `app/models/` - SQLAlchemy models
- `app/schemas/` - Pydantic schemas
- `alembic/` - Database migrations
- `requirements.txt` - Python dependencies
- `.env.example` - Environment variables template
- `README.md` - Setup and deployment instructions
- `systemd/daystrom.service` - Service configuration

## Future Migration Path (Local Model)

- When ready to move to local model:
- Set up Ollama or LM Studio on VPS
- Replace OpenAI service calls with local model endpoints
- Fine-tune local model on interaction patterns
- Keep embedding model local (sentence-transformers)

### To-dos

- [ ] Initialize Python project with FastAPI, PostgreSQL, and dependencies
- [ ] Create database schema with pgvector for items, embeddings, users, tags, and events
- [ ] Implement OpenAI API service for embeddings, classification, and extraction
- [ ] Set up Telegram bot with webhook and basic message handling
- [ ] Add voice and photo support to Telegram bot using Whisper and Vision APIs
- [ ] Implement vector similarity search using pgvector
- [ ] Integrate Google Calendar API with OAuth2 flow
- [ ] Implement CalDAV support for Apple Calendar
- [ ] Build daily/weekly digest generation with calendar-aware formatting
- [ ] Implement smart reminder system with background task scheduling
- [ ] Add interaction tracking and behavior adaptation logic
- [ ] Deploy on VPS with nginx, systemd, SSL, and database setup