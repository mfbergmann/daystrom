#!/bin/bash
# Continuous testing script for Daystrom Telegram bot

echo "🚀 Daystrom Telegram Bot - Continuous Testing"
echo "=============================================="

# Function to run tests
run_tests() {
    echo ""
    echo "🧪 Running tests at $(date)"
    echo "-------------------------------------------"
    
    cd /home/daystrom/app
    source venv/bin/activate
    python test_telegram.py
    
    echo ""
    echo "📊 Service Status:"
    systemctl status daystrom.service --no-pager -l | head -10
    
    echo ""
    echo "📋 Recent Logs (last 5 lines):"
    journalctl -u daystrom.service --no-pager -n 5 | tail -5
}

# Function to wait for user input
wait_for_input() {
    echo ""
    echo "Press Enter to run tests again, or Ctrl+C to exit..."
    read
}

# Main loop
while true; do
    run_tests
    wait_for_input
done
