#!/usr/bin/env python3
"""
Birmingham City FC Telegram Bot Server
Listens for commands and sends match information on request

Commands:
    /update - Get current match information
    /help - Show available commands
"""

import sys
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

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

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /update command - fetch and send match information"""

    chat_id = update.effective_chat.id
    logger.info(f"Received /update command from chat_id: {chat_id}")

    # Send "loading" message
    loading_msg = await update.message.reply_text("⏳ 경기 정보를 가져오는 중...")

    try:
        # Initialize API client and notifier
        api_client = FootballAPIClient(FOOTBALL_API_KEY, BIRMINGHAM_TEAM_ID)
        notifier = TelegramNotifier(TELEGRAM_BOT_TOKEN, str(chat_id))

        # Fetch match data
        standing = api_client.get_team_standing()
        all_standings = api_client.get_all_standings()
        upcoming_raw = api_client.get_upcoming_matches(days_ahead=2)
        upcoming_matches = [api_client.format_match_info(m) for m in upcoming_raw]
        future_raw = api_client.get_upcoming_future_matches(limit=3)
        future_matches = [api_client.format_match_info(m) for m in future_raw]
        recent_raw = api_client.get_recent_results(limit=5)
        recent_results = [api_client.format_match_info(m) for m in recent_raw]

        # Format and send notification
        message = notifier.format_match_notification(
            upcoming_matches,
            future_matches,
            recent_results,
            standing,
            all_standings
        )

        # Delete loading message and send result
        await loading_msg.delete()
        await update.message.reply_text(message, parse_mode='HTML')

        logger.info(f"Successfully sent match info to chat_id: {chat_id}")

    except Exception as e:
        logger.error(f"Error fetching match data: {e}")
        await loading_msg.edit_text(f"⚠️ 오류가 발생했습니다: {str(e)}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command - show available commands"""

    help_text = """⚽ <b>버밍엄 시티 FC 봇 명령어</b>

/update - 경기 정보 조회
/help - 도움말 표시

이 봇은 버밍엄 시티 FC의 경기 일정과 결과를 알려드립니다."""

    await update.message.reply_text(help_text, parse_mode='HTML')


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""

    start_text = """⚽ <b>버밍엄 시티 FC 알리미</b>에 오신 것을 환영합니다!

/update 명령어로 경기 정보를 확인하세요.
/help 명령어로 사용 가능한 명령어를 확인할 수 있습니다."""

    await update.message.reply_text(start_text, parse_mode='HTML')


def main() -> None:
    """Start the bot"""

    print(f"[{datetime.now()}] Starting Birmingham City FC Telegram Bot Server...")

    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("update", update_command))

    print("Bot is running. Press Ctrl+C to stop.")
    print("Available commands: /start, /help, /update")

    # Run the bot until Ctrl+C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
