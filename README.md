# Daystrom - AI-Powered Personal Memory & Task Assistant

Daystrom is an intelligent assistant that captures your thoughts, tasks, and ideas through Telegram, understands them using AI, and helps you stay organized with context-aware reminders and insights.

## Features

- **Multi-modal input**: Text, voice notes, and photos via Telegram
- **Intelligent understanding**: Automatic classification and extraction of tasks, events, ideas, and references
- **Semantic search**: Find related notes using natural language queries
- **Calendar integration**: Google Calendar and Apple Calendar (CalDAV) support
- **Smart digests**: Context-aware daily and weekly summaries
- **Proactive reminders**: AI-optimized reminder timing based on your calendar and behavior
- **Conversational brainstorming**: Surface related ideas and connections

## Architecture

- **Backend**: Python + FastAPI
- **Database**: PostgreSQL with pgvector extension
- **AI**: OpenAI API (GPT-4o, o1-preview, text-embedding-3-large)
- **Interface**: Telegram Bot
- **Deployment**: Self-hosted on VPS

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ with pgvector extension
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- OpenAI API Key
- (Optional) Google Calendar API credentials
- (Optional) Apple Calendar (iCloud) credentials

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd daystrom
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up PostgreSQL with pgvector:
```bash
# Install PostgreSQL (example for Ubuntu)
sudo apt-get install postgresql postgresql-contrib

# Install pgvector
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# Create database
sudo -u postgres createdb daystrom
sudo -u postgres psql daystrom -c "CREATE EXTENSION vector;"
```

5. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and credentials
```

6. Run database migrations:
```bash
alembic upgrade head
```

7. Start the application:
```bash
python main.py
```

## Usage

### Setting up Telegram Webhook

1. Start the application
2. Set webhook URL with Telegram:
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=<YOUR_WEBHOOK_URL>"
```

### Basic Commands

- `/start` - Initialize and get started
- `/search <query>` - Search your notes semantically
- `/digest` - Get a summary of recent items
- `/brainstorm <topic>` - Surface related ideas and connections

### Capturing Information

Simply send messages to the bot:
- **Text**: Type your thoughts, tasks, or ideas
- **Voice**: Send voice notes (automatically transcribed)
- **Photos**: Send images with or without captions (OCR applied)

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions for production VPS setup.

## Development

### Running locally

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Database migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```

## License

MIT License

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

