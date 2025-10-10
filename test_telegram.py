#!/usr/bin/env python3
"""
Automated Telegram webhook testing script.
This script simulates Telegram webhook calls to test bot functionality.
"""
import asyncio
import json
import aiohttp
import sys
from datetime import datetime

# Test webhook URL
WEBHOOK_URL = "http://localhost:8000/webhook/telegram"

# Sample Telegram update payloads
TEST_UPDATES = {
    "start_command": {
        "update_id": 12345,
        "message": {
            "message_id": 1,
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "language_code": "en"
            },
            "chat": {
                "id": 123456789,
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "type": "private"
            },
            "date": int(datetime.now().timestamp()),
            "text": "/start",
            "entities": [
                {
                    "offset": 0,
                    "length": 6,
                    "type": "bot_command"
                }
            ]
        }
    },
    "help_command": {
        "update_id": 12346,
        "message": {
            "message_id": 2,
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "language_code": "en"
            },
            "chat": {
                "id": 123456789,
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "type": "private"
            },
            "date": int(datetime.now().timestamp()),
            "text": "/help",
            "entities": [
                {
                    "offset": 0,
                    "length": 5,
                    "type": "bot_command"
                }
            ]
        }
    },
    "digest_command": {
        "update_id": 12347,
        "message": {
            "message_id": 3,
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "language_code": "en"
            },
            "chat": {
                "id": 123456789,
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "type": "private"
            },
            "date": int(datetime.now().timestamp()),
            "text": "/digest",
            "entities": [
                {
                    "offset": 0,
                    "length": 7,
                    "type": "bot_command"
                }
            ]
        }
    },
    "text_message": {
        "update_id": 12348,
        "message": {
            "message_id": 4,
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "language_code": "en"
            },
            "chat": {
                "id": 123456789,
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "type": "private"
            },
            "date": int(datetime.now().timestamp()),
            "text": "Remember to buy groceries tomorrow"
        }
    }
}

async def test_webhook(test_name: str, update_data: dict):
    """Test a single webhook call."""
    print(f"\n🧪 Testing {test_name}...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                WEBHOOK_URL,
                json=update_data,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                status = response.status
                text = await response.text()
                
                if status == 200:
                    print(f"✅ {test_name}: SUCCESS (HTTP {status})")
                    print(f"   Response: {text}")
                    return True
                else:
                    print(f"❌ {test_name}: FAILED (HTTP {status})")
                    print(f"   Response: {text}")
                    return False
                    
    except Exception as e:
        print(f"❌ {test_name}: ERROR - {e}")
        return False

async def run_all_tests():
    """Run all webhook tests."""
    print("🚀 Starting Telegram webhook tests...")
    print(f"Testing webhook URL: {WEBHOOK_URL}")
    
    results = {}
    
    for test_name, update_data in TEST_UPDATES.items():
        success = await test_webhook(test_name, update_data)
        results[test_name] = success
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    # Print summary
    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:20} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️  Some tests failed. Check the logs for details.")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(run_all_tests())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test runner failed: {e}")
        sys.exit(1)
