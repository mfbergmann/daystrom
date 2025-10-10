#!/usr/bin/env python3
"""Test script to verify connections to external services."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from openai import AsyncOpenAI
from telegram import Bot
from sqlalchemy.ext.asyncio import create_async_engine


async def test_database():
    """Test database connection."""
    print("🔍 Testing database connection...")
    try:
        engine = create_async_engine(settings.database_url)
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def test_openai():
    """Test OpenAI API connection."""
    print("🔍 Testing OpenAI API...")
    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'connection test successful'"}],
            max_tokens=20
        )
        print(f"✅ OpenAI API successful: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"❌ OpenAI API failed: {e}")
        return False


async def test_telegram():
    """Test Telegram Bot connection."""
    print("🔍 Testing Telegram Bot...")
    try:
        bot = Bot(token=settings.telegram_bot_token)
        bot_info = await bot.get_me()
        print(f"✅ Telegram Bot connected: @{bot_info.username}")
        return True
    except Exception as e:
        print(f"❌ Telegram Bot failed: {e}")
        return False


async def main():
    """Run all connection tests."""
    print("🧪 Daystrom Connection Tests\n")
    
    results = []
    results.append(await test_database())
    results.append(await test_openai())
    results.append(await test_telegram())
    
    print("\n" + "="*50)
    if all(results):
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed. Please check your configuration.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

