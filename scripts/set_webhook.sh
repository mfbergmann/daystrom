#!/bin/bash
# Script to set Telegram webhook

if [ -z "$1" ]; then
    echo "Usage: ./set_webhook.sh <webhook_url>"
    echo "Example: ./set_webhook.sh https://yourdomain.com/webhook/telegram"
    exit 1
fi

# Load bot token from .env
if [ ! -f .env ]; then
    echo "Error: .env file not found"
    exit 1
fi

BOT_TOKEN=$(grep TELEGRAM_BOT_TOKEN .env | cut -d '=' -f2)

if [ -z "$BOT_TOKEN" ]; then
    echo "Error: TELEGRAM_BOT_TOKEN not found in .env"
    exit 1
fi

WEBHOOK_URL=$1

echo "Setting webhook to: $WEBHOOK_URL"

RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${WEBHOOK_URL}")

echo "Response: $RESPONSE"

# Check webhook info
echo ""
echo "Current webhook info:"
curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo" | python3 -m json.tool

