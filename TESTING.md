# Testing Guide for Daystrom

This guide covers how to test Daystrom during development and after deployment.

## Prerequisites

- PostgreSQL database set up with pgvector extension
- Valid `.env` file with all API keys
- Virtual environment activated

## Initial Setup Testing

### 1. Test Database Connection

```bash
python scripts/test_connection.py
```

This will verify:
- ✅ PostgreSQL connection
- ✅ OpenAI API access
- ✅ Telegram Bot token validity

### 2. Run Database Migrations

```bash
alembic upgrade head
```

Expected output: Migration runs without errors

### 3. Start the Application

```bash
python main.py
```

Expected output:
```
Starting Daystrom application
Database initialized
Task scheduler started
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 4. Test Health Check

In another terminal:
```bash
curl http://localhost:8000/health
```

Expected: `{"status":"healthy"}`

## Testing Telegram Integration

### 1. Set Webhook (Local Testing)

For local testing, use ngrok to expose your local server:

```bash
# Install ngrok if not already installed
# Run ngrok
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`) and set the webhook:

```bash
./scripts/set_webhook.sh https://abc123.ngrok.io/webhook/telegram
```

### 2. Test Bot Commands

Open Telegram and message your bot:

**Test `/start` command:**
- Send: `/start`
- Expected: Welcome message with instructions

**Test text capture:**
- Send: "Buy groceries tomorrow"
- Expected: Confirmation with item type (likely "task"), tags, and due date

**Test voice capture:**
- Send a voice note
- Expected: Transcription and confirmation

**Test photo capture:**
- Send a photo with text
- Expected: OCR extraction and confirmation

**Test `/search` command:**
- Send: `/search groceries`
- Expected: Relevant items from your notes

**Test `/digest` command:**
- Send: `/digest`
- Expected: Summary of recent items

**Test `/brainstorm` command:**
- Send: `/brainstorm productivity ideas`
- Expected: AI-generated connections and suggestions

## Testing OpenAI Integration

### Manual Test Script

Create a test file `test_openai.py`:

```python
import asyncio
from app.services.openai_service import openai_service

async def test():
    # Test embedding
    embedding = await openai_service.get_embedding("test message")
    print(f"✅ Embedding dimension: {len(embedding)}")
    
    # Test classification
    result = await openai_service.classify_and_extract(
        "Schedule meeting with John tomorrow at 2pm"
    )
    print(f"✅ Classification result: {result}")
    
    # Test digest
    items = [
        {"content": "Buy groceries", "item_type": "task", "due_date": None},
        {"content": "Meeting with team", "item_type": "event", "due_date": "2024-10-11T14:00:00"}
    ]
    digest = await openai_service.generate_digest(items)
    print(f"✅ Digest: {digest}")

asyncio.run(test())
```

Run:
```bash
python test_openai.py
```

## Testing Semantic Search

### Create Test Data

```python
import asyncio
from app.database import AsyncSessionLocal
from app.services.memory_service import memory_service
from app.schemas.item import ItemCreate

async def create_test_items():
    async with AsyncSessionLocal() as db:
        user_id = 1  # Use your actual user ID
        
        items = [
            "Learn Python for machine learning",
            "Build a web scraper with BeautifulSoup",
            "Study neural networks and deep learning",
            "Create a React todo app",
            "Read about PostgreSQL optimization",
        ]
        
        for content in items:
            item_data = ItemCreate(content=content, item_type="note")
            await memory_service.create_item(db, user_id, item_data)
            print(f"✅ Created: {content}")

asyncio.run(create_test_items())
```

### Test Search

```python
import asyncio
from app.database import AsyncSessionLocal
from app.services.memory_service import memory_service

async def test_search():
    async with AsyncSessionLocal() as db:
        results = await memory_service.semantic_search(
            db, user_id=1, query="artificial intelligence", limit=5
        )
        
        print("Search results:")
        for result in results:
            print(f"- {result['content']} (similarity: {result['similarity']:.2f})")

asyncio.run(test_search())
```

Expected: Items about machine learning and neural networks should rank highest.

## Testing Calendar Integration

### Google Calendar

1. Get OAuth URL:
```bash
curl "http://localhost:8000/auth/google/authorize?user_id=1"
```

2. Visit the URL and authorize
3. The callback should save the refresh token
4. Test sync:

```python
import asyncio
from app.database import AsyncSessionLocal
from app.services.calendar_service import calendar_service

async def test_google_sync():
    async with AsyncSessionLocal() as db:
        events = await calendar_service.sync_google_calendar(db, user_id=1)
        print(f"✅ Synced {len(events)} events")
        for event in events[:5]:
            print(f"- {event.title} at {event.start_time}")

asyncio.run(test_google_sync())
```

### CalDAV (Apple Calendar)

Ensure CalDAV credentials are in `.env`, then:

```python
import asyncio
from app.database import AsyncSessionLocal
from app.services.calendar_service import calendar_service

async def test_caldav_sync():
    async with AsyncSessionLocal() as db:
        events = await calendar_service.sync_caldav_calendar(db, user_id=1)
        print(f"✅ Synced {len(events)} events")
        for event in events[:5]:
            print(f"- {event.title} at {event.start_time}")

asyncio.run(test_caldav_sync())
```

## Testing Scheduled Tasks

### Test Digest Generation

```python
import asyncio
from app.scheduler import task_scheduler

# Manually trigger digest
asyncio.run(task_scheduler.send_daily_digests())
```

Check your Telegram for the digest message.

### Test Calendar Sync

```python
import asyncio
from app.scheduler import task_scheduler

asyncio.run(task_scheduler.sync_calendars())
```

## Load Testing

### Test Concurrent Requests

```bash
# Install apache bench
sudo apt install apache2-utils

# Test health endpoint
ab -n 1000 -c 10 http://localhost:8000/health
```

### Test Telegram Webhook

```python
import asyncio
import aiohttp

async def test_webhook():
    update_data = {
        "update_id": 123456789,
        "message": {
            "message_id": 123,
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Test"
            },
            "chat": {
                "id": 123456789,
                "first_name": "Test",
                "type": "private"
            },
            "date": 1634567890,
            "text": "test message"
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            'http://localhost:8000/webhook/telegram',
            json=update_data
        ) as resp:
            print(f"Status: {resp.status}")
            print(f"Response: {await resp.json()}")

asyncio.run(test_webhook())
```

## Database Testing

### Check Tables Created

```bash
psql -U daystrom_user -d daystrom -c "\dt"
```

Expected tables:
- users
- items
- embeddings
- tags
- calendar_events
- interactions
- alembic_version

### Check Vector Extension

```bash
psql -U daystrom_user -d daystrom -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

### Check Indexes

```bash
psql -U daystrom_user -d daystrom -c "SELECT indexname, tablename FROM pg_indexes WHERE schemaname = 'public';"
```

## Common Issues and Solutions

### Issue: "relation does not exist"
**Solution:** Run migrations: `alembic upgrade head`

### Issue: "could not connect to server"
**Solution:** Check PostgreSQL is running: `sudo systemctl status postgresql`

### Issue: "OpenAI API error"
**Solution:** Verify API key in `.env` and check OpenAI account has credits

### Issue: "Telegram webhook failed"
**Solution:** 
- Check bot token is correct
- Ensure webhook URL is HTTPS (use ngrok for local testing)
- Verify webhook is set: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`

### Issue: "Vector similarity search returns no results"
**Solution:** 
- Ensure pgvector extension is installed
- Check embeddings table has data
- Lower similarity threshold in search

## Performance Benchmarks

Expected performance (on 2GB VPS):

- **API Response Time**: < 100ms for health check
- **Message Processing**: < 3s for text, < 10s for voice/photo
- **Semantic Search**: < 500ms for 1000 items
- **Digest Generation**: < 5s
- **Memory Usage**: ~300-500MB
- **CPU Usage**: < 20% during normal operation

## Monitoring in Production

### Check Application Logs

```bash
# Real-time logs
sudo journalctl -u daystrom -f

# Last 100 lines
sudo journalctl -u daystrom -n 100

# Errors only
sudo journalctl -u daystrom -p err
```

### Check Database Size

```bash
psql -U daystrom_user -d daystrom -c "SELECT pg_size_pretty(pg_database_size('daystrom'));"
```

### Check OpenAI API Usage

Log into OpenAI platform and check usage dashboard.

## Security Testing

### Check for Exposed Secrets

```bash
# Should return nothing
grep -r "sk-" . --exclude-dir=venv --exclude=".env*"
```

### Test Rate Limiting

```bash
# Should eventually get rate limited
for i in {1..100}; do curl http://localhost:8000/health; done
```

### Check File Permissions

```bash
# .env should be readable only by owner
ls -la .env
# Expected: -rw------- (600)
```

## Continuous Testing

Set up a cron job to test critical functionality daily:

```bash
0 6 * * * cd /home/daystrom/app && /home/daystrom/app/venv/bin/python scripts/test_connection.py >> /home/daystrom/logs/daily_test.log 2>&1
```

This ensures you're alerted if any external service becomes unavailable.

