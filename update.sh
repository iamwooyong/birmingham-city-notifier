#!/bin/bash
# Birmingham City FC Bot - Update & Restart Script
# Usage: ./update.sh

SCRIPT_DIR="/var/services/homes/admin/scripts/birmingham-city-notifier"
LOG_FILE="$SCRIPT_DIR/bot.log"

echo "=== Birmingham Bot Update ==="

# Go to project directory
cd "$SCRIPT_DIR" || exit 1

# Pull latest changes
echo "[1/3] Pulling latest changes..."
git pull

# Kill existing bot process
echo "[2/3] Stopping existing bot..."
pkill -f "python3 birmingham_bot.py" 2>/dev/null || echo "No existing bot process found"
sleep 1

# Start bot
echo "[3/3] Starting bot..."
nohup /usr/bin/python3 birmingham_bot.py >> "$LOG_FILE" 2>&1 &

echo "=== Done! Bot is running ==="
echo "Check logs: tail -f $LOG_FILE"
