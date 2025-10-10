#!/usr/bin/env python3
"""Script to manually create a test user."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models import User


async def create_user(telegram_id: int, username: str = None, first_name: str = None):
    """Create a test user."""
    async with AsyncSessionLocal() as db:
        user = User(
            telegram_id=telegram_id,
            telegram_username=username,
            first_name=first_name
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        print(f"✅ Created user:")
        print(f"   ID: {user.id}")
        print(f"   Telegram ID: {user.telegram_id}")
        print(f"   Username: {user.telegram_username}")
        print(f"   Name: {user.first_name}")


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python create_user.py <telegram_id> [username] [first_name]")
        sys.exit(1)
    
    telegram_id = int(sys.argv[1])
    username = sys.argv[2] if len(sys.argv) > 2 else None
    first_name = sys.argv[3] if len(sys.argv) > 3 else None
    
    await create_user(telegram_id, username, first_name)


if __name__ == "__main__":
    asyncio.run(main())

