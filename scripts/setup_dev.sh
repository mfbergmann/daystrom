#!/bin/bash
# Development environment setup script

set -e

echo "🚀 Setting up Daystrom development environment..."

# Check Python version
if ! command -v python3.11 &> /dev/null; then
    echo "❌ Python 3.11 not found. Please install Python 3.11+"
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check for .env file
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your API keys and credentials"
else
    echo "✅ .env file already exists"
fi

# Create logs directory
mkdir -p logs

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Set up PostgreSQL database with pgvector extension"
echo "3. Run: alembic upgrade head"
echo "4. Run: python main.py"
echo ""
echo "Activate virtual environment with: source venv/bin/activate"

