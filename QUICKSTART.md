# Daystrom Quick Start Guide

Get Daystrom up and running in under 10 minutes!

## Prerequisites

- Python 3.11+
- PostgreSQL 15+ (or use Docker)
- OpenAI API key
- Telegram Bot token

## Step 1: Clone & Install (2 minutes)

```bash
# Clone repository
git clone <repository-url>
cd daystrom

# Run setup script
chmod +x scripts/setup_dev.sh
./scripts/setup_dev.sh
```

This will:
- Create virtual environment
- Install all dependencies
- Create `.env` file from template

## Step 2: Configure Environment (2 minutes)

Edit `.env` file:

```bash
nano .env
```

**Minimal required configuration:**

```env
# Database (use Docker or local PostgreSQL)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/daystrom_dev
DATABASE_SYNC_URL=postgresql://postgres:postgres@localhost:5432/daystrom_dev

# OpenAI (get from https://platform.openai.com/api-keys)
OPENAI_API_KEY=sk-your-actual-key-here

# Telegram (get from @BotFather on Telegram)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

## Step 3: Start Database (1 minute)

### Option A: Using Docker (Recommended for dev)
```bash
make docker-up
```

### Option B: Using Local PostgreSQL
```bash
# Create database
sudo -u postgres psql
CREATE DATABASE daystrom_dev;
\q

# Install pgvector
git clone https://github.com/pgvector/pgvector.git /tmp/pgvector
cd /tmp/pgvector
make
sudo make install

# Enable extension
sudo -u postgres psql daystrom_dev -c "CREATE EXTENSION vector;"
```

## Step 4: Initialize Database (1 minute)

```bash
# Activate virtual environment
source venv/bin/activate

# Run migrations
make migrate
```

## Step 5: Test Connections (1 minute)

```bash
make test
```

You should see:
```
✅ Database connection successful
✅ OpenAI API successful
✅ Telegram Bot connected
```

## Step 6: Start Application (1 minute)

```bash
make run
```

You should see:
```
Starting Daystrom application
Database initialized
Task scheduler started
INFO: Uvicorn running on http://0.0.0.0:8000
```

## Step 7: Set Up Telegram Webhook (2 minutes)

### For Local Development (Using ngrok)

1. **Install ngrok:**
```bash
# macOS
brew install ngrok

# Linux
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/
```

2. **Start ngrok in new terminal:**
```bash
ngrok http 8000
```

3. **Copy the HTTPS URL** (e.g., `https://abc123.ngrok.io`)

4. **Set webhook:**
```bash
./scripts/set_webhook.sh https://abc123.ngrok.io/webhook/telegram
```

### For Production

Update `.env` with your domain:
```env
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook/telegram
```

Then:
```bash
./scripts/set_webhook.sh https://yourdomain.com/webhook/telegram
```

## Step 8: Test Your Bot! 🎉

Open Telegram and find your bot (search for username you set with BotFather).

**Try these commands:**

1. **Initialize bot:**
   ```
   /start
   ```

2. **Capture a task:**
   ```
   Buy groceries tomorrow
   ```

3. **Send a voice note** - it will be transcribed!

4. **Search your notes:**
   ```
   /search groceries
   ```

5. **Get a digest:**
   ```
   /digest
   ```

6. **Brainstorm:**
   ```
   /brainstorm productivity ideas
   ```

## Common Issues

### "Database connection failed"
- Check PostgreSQL is running: `sudo systemctl status postgresql` (or `docker ps`)
- Verify DATABASE_URL in `.env` matches your setup

### "OpenAI API failed"
- Verify API key is correct in `.env`
- Check you have credits in your OpenAI account

### "Telegram Bot failed"
- Confirm bot token is correct
- Make sure there are no extra spaces in `.env`

### "Webhook not receiving messages"
- For local dev, ensure ngrok is running
- Webhook URL must be HTTPS
- Check webhook status: 
  ```bash
  curl "https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo"
  ```

## Next Steps

### Add Calendar Integration

**Google Calendar:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth2 credentials
3. Add to `.env`:
   ```env
   GOOGLE_CLIENT_ID=your_client_id
   GOOGLE_CLIENT_SECRET=your_client_secret
   ```
4. In Telegram, use bot to authorize

**Apple Calendar (iCloud):**
1. Generate app-specific password at [appleid.apple.com](https://appleid.apple.com)
2. Add to `.env`:
   ```env
   CALDAV_USERNAME=your_icloud_email
   CALDAV_PASSWORD=your_app_specific_password
   ```

### Customize Settings

Edit `.env` to customize:
- `DIGEST_TIME_DAILY` - When to send daily digests
- `DIGEST_TIME_WEEKLY` - When to send weekly digests
- `TIMEZONE` - Your timezone

### Deploy to Production

See [DEPLOYMENT.md](DEPLOYMENT.md) for full production deployment guide.

## Development Commands

```bash
# Start application
make run

# Run tests
make test

# Create new migration
make migrate-create MSG="add new field"

# Apply migrations
make migrate

# Start Docker services
make docker-up

# Stop Docker services
make docker-down

# Clean temporary files
make clean
```

## Project Structure

```
daystrom/
├── app/
│   ├── bot/              # Telegram bot handlers
│   ├── models/           # Database models
│   ├── schemas/          # Pydantic schemas
│   └── services/         # Business logic
├── alembic/              # Database migrations
├── scripts/              # Utility scripts
├── main.py               # Application entry point
├── config.py             # Configuration
└── requirements.txt      # Python dependencies
```

## Getting Help

- Check [README.md](README.md) for detailed documentation
- See [API.md](API.md) for API documentation
- Read [TESTING.md](TESTING.md) for testing guide
- Review [DEPLOYMENT.md](DEPLOYMENT.md) for production setup

## Tips for Best Results

1. **Be descriptive** when capturing notes - more context = better AI understanding
2. **Use voice notes** for quick capture on the go
3. **Search semantically** - describe what you're looking for, don't just use keywords
4. **Check digests** regularly to stay on top of tasks
5. **Enable calendar integration** for context-aware reminders

Enjoy using Daystrom! 🚀

