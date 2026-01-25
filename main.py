#!/usr/bin/env python3
"""
Birmingham City FC Match Notifier
Sends daily Telegram notifications about Birmingham City FC matches

This script should be run daily (e.g., via cron) to send match updates
"""

import sys
from datetime import datetime

try:
    from config import (
        FOOTBALL_API_KEY,
        TELEGRAM_BOT_TOKEN,
        TELEGRAM_CHAT_ID,
        BIRMINGHAM_TEAM_ID
    )
except ImportError:
    print("Error: config.py not found!")
    print("Please create config.py based on config.example.py")
    sys.exit(1)

from football_api import FootballAPIClient
from telegram_bot import TelegramNotifier


def main():
    """Main function to fetch match data and send notifications"""

    print(f"[{datetime.now()}] Starting Birmingham City FC notifier...")

    # Initialize API client and Telegram notifier
    try:
        api_client = FootballAPIClient(FOOTBALL_API_KEY, BIRMINGHAM_TEAM_ID)
        telegram = TelegramNotifier(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    except Exception as e:
        print(f"Error initializing clients: {e}")
        sys.exit(1)

    # Fetch match data
    print("Fetching match data from football-data.org...")

    try:
        # Get upcoming matches (today and tomorrow)
        upcoming_raw = api_client.get_upcoming_matches(days_ahead=2)
        upcoming_matches = [api_client.format_match_info(m) for m in upcoming_raw]
        print(f"Found {len(upcoming_matches)} upcoming matches (today/tomorrow)")

        # Get future matches (next 3 matches)
        future_raw = api_client.get_upcoming_future_matches(limit=3)
        future_matches = [api_client.format_match_info(m) for m in future_raw]
        print(f"Found {len(future_matches)} future matches (next 3)")

        # Get recent results (last 5 games)
        recent_raw = api_client.get_recent_results(limit=5)
        recent_results = [api_client.format_match_info(m) for m in recent_raw]
        print(f"Found {len(recent_results)} recent results (last 5 games)")

    except Exception as e:
        print(f"Error fetching match data: {e}")
        # Send error notification
        try:
            error_message = f"⚠️ 버밍엄 시티 FC 경기 정보를 가져오는데 실패했습니다.\n\n오류: {str(e)}"
            import asyncio
            asyncio.run(telegram.send_message(error_message))
        except:
            pass
        sys.exit(1)

    # Send notification
    print("Sending Telegram notification...")

    try:
        success = telegram.send_notification_sync(
            upcoming_matches,
            future_matches,
            recent_results
        )

        if success:
            print("[SUCCESS] Notification sent successfully!")
            print(f"[{datetime.now()}] Birmingham City FC notifier completed successfully")
            return 0
        else:
            print("[FAILED] Failed to send notification")
            return 1

    except Exception as e:
        print(f"Error sending notification: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
