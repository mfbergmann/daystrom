# Daystrom API Documentation

## Base URL

```
https://your-domain.com
```

## Authentication

Currently, the API uses Telegram user IDs for authentication. Future versions may implement API keys for direct API access.

## Endpoints

### Health & Status

#### GET `/`
Get basic application info.

**Response:**
```json
{
  "name": "Daystrom",
  "version": "1.0.0",
  "status": "running"
}
```

#### GET `/health`
Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "healthy"
}
```

### Telegram Webhook

#### POST `/webhook/telegram`
Receives updates from Telegram.

**Headers:**
- `Content-Type: application/json`

**Request Body:**
Telegram Update object (see [Telegram Bot API](https://core.telegram.org/bots/api#update))

**Response:**
```json
{
  "status": "ok"
}
```

### Google Calendar Authentication

#### GET `/auth/google/authorize`
Initiates Google Calendar OAuth2 flow.

**Query Parameters:**
- `user_id` (required): User ID for authentication

**Response:**
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/auth?..."
}
```

#### GET `/auth/google/callback`
Handles OAuth2 callback from Google.

**Query Parameters:**
- `state`: User ID (passed through OAuth flow)
- `code`: Authorization code from Google

**Response:**
```json
{
  "status": "success",
  "message": "Google Calendar connected successfully"
}
```

## Bot Commands (via Telegram)

### `/start`
Initialize the bot and display welcome message.

**Response:**
Welcome message with bot capabilities and available commands.

### `/help`
Display help information and command list.

**Response:**
Detailed help message with command descriptions.

### `/search <query>`
Perform semantic search across captured items.

**Parameters:**
- `query`: Natural language search query

**Example:**
```
/search machine learning projects
```

**Response:**
List of semantically similar items with:
- Item type
- Content preview
- Similarity score
- Tags

### `/digest`
Generate a summary of recent items and upcoming events.

**Response:**
AI-generated digest including:
- Pending tasks
- Recent ideas
- Upcoming calendar events
- Contextual insights

### `/brainstorm <topic>`
Start a brainstorming session on a topic.

**Parameters:**
- `topic`: The topic to brainstorm about

**Example:**
```
/brainstorm productivity app features
```

**Response:**
AI-generated brainstorming response including:
- Related notes from your memory
- Connections between ideas
- Suggestions and questions
- New angles to explore

## Message Types

### Text Messages
Send any text message to capture it.

**Auto-extracted Information:**
- Item type (idea, task, event, reference, note)
- Due dates
- Priority level
- Tags
- People mentioned

**Response:**
Confirmation message with extracted metadata.

### Voice Messages
Send a voice note for transcription and capture.

**Processing:**
1. Download voice file
2. Transcribe using OpenAI Whisper
3. Extract information
4. Store with original media reference

**Response:**
Transcribed text and confirmation.

### Photo Messages
Send photos with optional captions.

**Processing:**
1. Download image
2. Extract text using OCR (OpenAI Vision)
3. Analyze content
4. Extract information
5. Store with media reference

**Response:**
Extracted text/description and confirmation.

## Data Models

### User
```json
{
  "id": 1,
  "telegram_id": 123456789,
  "telegram_username": "username",
  "first_name": "John",
  "timezone": "America/New_York",
  "digest_enabled": true,
  "digest_time": "08:00",
  "created_at": "2024-10-10T12:00:00Z"
}
```

### Item
```json
{
  "id": 1,
  "user_id": 1,
  "content": "Buy groceries tomorrow",
  "item_type": "task",
  "due_date": "2024-10-11T00:00:00Z",
  "priority": "medium",
  "tags": ["shopping", "personal"],
  "counterparties": [],
  "completed": "pending",
  "created_at": "2024-10-10T12:00:00Z"
}
```

### Calendar Event
```json
{
  "id": 1,
  "user_id": 1,
  "external_id": "google_event_123",
  "source": "google",
  "title": "Team Meeting",
  "description": "Weekly sync",
  "location": "Conference Room A",
  "start_time": "2024-10-11T14:00:00Z",
  "end_time": "2024-10-11T15:00:00Z",
  "all_day": false
}
```

### Search Result
```json
{
  "item_id": 1,
  "content": "Machine learning project ideas",
  "item_type": "idea",
  "similarity": 0.89,
  "created_at": "2024-10-10T12:00:00Z",
  "tags": ["ml", "projects"]
}
```

## Item Types

- **idea**: Creative thoughts, concepts, potential projects
- **task**: Action items, todos, things to do
- **event**: Time-specific activities, meetings, appointments
- **reference**: Useful information, links, documentation
- **note**: General observations, thoughts, journal entries

## Priority Levels

- **low**: Nice to have, no urgency
- **medium**: Should be done, moderate importance
- **high**: Critical, urgent, important

## Status Values

- **pending**: Not started
- **active**: In progress
- **completed**: Finished
- **cancelled**: No longer relevant

## Webhook Security

For production deployments, implement webhook verification:

1. Set a secret token in Telegram bot settings
2. Verify `X-Telegram-Bot-Api-Secret-Token` header
3. Reject requests without valid token

## Rate Limits

Current implementation has no explicit rate limits. For production:

- Consider implementing rate limiting per user
- Typical limits: 30 requests/minute per user
- Use Redis or in-memory store for tracking

## Error Responses

### Standard Error Format
```json
{
  "error": "Error description",
  "status_code": 500
}
```

### Common Errors

**400 Bad Request**
```json
{
  "error": "Invalid request format"
}
```

**401 Unauthorized**
```json
{
  "error": "Authentication required"
}
```

**500 Internal Server Error**
```json
{
  "error": "Internal server error"
}
```

## Scheduled Tasks

The system automatically performs these background tasks:

### Daily Digest
- **Schedule**: 8:00 AM (configurable per user)
- **Action**: Sends daily summary via Telegram
- **Content**: Recent items, upcoming events, priorities

### Weekly Digest
- **Schedule**: Monday 9:00 AM (configurable)
- **Action**: Sends weekly overview
- **Content**: Week review, trends, insights

### Calendar Sync
- **Schedule**: Every hour
- **Action**: Syncs Google Calendar and CalDAV events
- **Updates**: New events, changes, deletions

## OpenAI Model Usage

### Embeddings
- **Model**: `text-embedding-3-large`
- **Dimensions**: 3072
- **Use**: Semantic search, similarity matching

### Chat Completion
- **Model**: `gpt-4o`
- **Use**: Classification, extraction, digests, brainstorming

### Reasoning (Future)
- **Model**: `o1-preview`
- **Use**: Complex analysis, deep insights

### Transcription
- **Model**: `whisper-1`
- **Use**: Voice note transcription

### Vision
- **Model**: `gpt-4o` with vision
- **Use**: Image analysis, OCR

## Database Schema

### Vector Search
Uses PostgreSQL with pgvector extension for semantic search:

```sql
-- Example similarity search
SELECT items.*, 
       1 - (embeddings.embedding <=> query_embedding) as similarity
FROM items
JOIN embeddings ON items.id = embeddings.item_id
WHERE 1 - (embeddings.embedding <=> query_embedding) >= 0.7
ORDER BY similarity DESC
LIMIT 10;
```

## Future API Endpoints (Planned)

### GET `/api/items`
List user's items with filtering

### POST `/api/items`
Create item programmatically

### GET `/api/items/{id}`
Get specific item

### PUT `/api/items/{id}`
Update item

### DELETE `/api/items/{id}`
Delete item

### GET `/api/tags`
List popular tags

### GET `/api/calendar/events`
Get upcoming events

### POST `/api/calendar/sync`
Trigger calendar sync

## Webhook Events

Future enhancement: Send webhooks for events

- `item.created`
- `item.completed`
- `reminder.sent`
- `digest.generated`

## SDK (Future)

Python SDK example:
```python
from daystrom import Client

client = Client(api_key="your_api_key")

# Create item
item = client.items.create(
    content="New task",
    item_type="task"
)

# Search
results = client.search("project ideas")

# Get digest
digest = client.digest.generate()
```

## Support & Feedback

For issues or feature requests, check the GitHub repository or contact the development team.

