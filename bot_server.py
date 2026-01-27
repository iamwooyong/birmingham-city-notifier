#!/usr/bin/env python3
"""
Birmingham City FC Telegram Bot Server
Listens for commands and sends match information on request

Commands:
    /update - Get current match information
    /menu - Show menu with buttons
    /help - Show available commands
"""

import sys
import logging
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

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

# Initialize API client (reusable)
api_client = FootballAPIClient(FOOTBALL_API_KEY, BIRMINGHAM_TEAM_ID)


def get_menu_keyboard():
    """Create inline keyboard with menu buttons"""
    keyboard = [
        [InlineKeyboardButton("📋 전체 정보", callback_data="all")],
        [
            InlineKeyboardButton("📆 향후 경기", callback_data="future"),
            InlineKeyboardButton("📊 최근 결과", callback_data="recent")
        ],
        [InlineKeyboardButton("🏆 리그 순위표", callback_data="standings")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /menu command - show menu with buttons"""
    await update.message.reply_text(
        "⚽ <b>Birmingham City FC</b>\n\n원하는 정보를 선택하세요:",
        parse_mode='HTML',
        reply_markup=get_menu_keyboard()
    )


async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /update command - fetch and send all match information"""
    chat_id = update.effective_chat.id
    logger.info(f"Received /update command from chat_id: {chat_id}")

    loading_msg = await update.message.reply_text("⏳ 경기 정보를 가져오는 중...")

    try:
        notifier = TelegramNotifier(TELEGRAM_BOT_TOKEN, str(chat_id))

        standing = api_client.get_team_standing()
        all_standings = api_client.get_all_standings()
        upcoming_raw = api_client.get_upcoming_matches(days_ahead=2)
        upcoming_matches = [api_client.format_match_info(m) for m in upcoming_raw]
        future_raw = api_client.get_upcoming_future_matches(limit=3)
        future_matches = [api_client.format_match_info(m) for m in future_raw]
        recent_raw = api_client.get_recent_results(limit=5)
        recent_results = [api_client.format_match_info(m) for m in recent_raw]

        message = notifier.format_match_notification(
            upcoming_matches, future_matches, recent_results, standing, all_standings
        )

        await loading_msg.delete()
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=get_menu_keyboard())

        logger.info(f"Successfully sent match info to chat_id: {chat_id}")

    except Exception as e:
        logger.error(f"Error fetching match data: {e}")
        await loading_msg.edit_text(f"⚠️ 오류가 발생했습니다: {str(e)}")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    callback_data = query.data
    logger.info(f"Button pressed: {callback_data} from chat_id: {chat_id}")

    # Edit message to show loading
    await query.edit_message_text("⏳ 정보를 가져오는 중...")

    try:
        notifier = TelegramNotifier(TELEGRAM_BOT_TOKEN, str(chat_id))
        all_standings = api_client.get_all_standings()

        if callback_data == "all":
            # All information
            standing = api_client.get_team_standing()
            upcoming_raw = api_client.get_upcoming_matches(days_ahead=2)
            upcoming_matches = [api_client.format_match_info(m) for m in upcoming_raw]
            future_raw = api_client.get_upcoming_future_matches(limit=3)
            future_matches = [api_client.format_match_info(m) for m in future_raw]
            recent_raw = api_client.get_recent_results(limit=5)
            recent_results = [api_client.format_match_info(m) for m in recent_raw]

            message = notifier.format_match_notification(
                upcoming_matches, future_matches, recent_results, standing, all_standings
            )

        elif callback_data == "future":
            # Future matches only
            standing = api_client.get_team_standing()
            future_raw = api_client.get_upcoming_future_matches(limit=5)
            future_matches = [api_client.format_match_info(m) for m in future_raw]
            message = notifier.format_future_matches(future_matches, standing, all_standings)

        elif callback_data == "recent":
            # Recent results only
            recent_raw = api_client.get_recent_results(limit=5)
            recent_results = [api_client.format_match_info(m) for m in recent_raw]
            message = notifier.format_recent_results(recent_results, all_standings)

        elif callback_data == "standings":
            # League standings
            standing = api_client.get_team_standing()
            message = notifier.format_standings(standing)

        else:
            message = "알 수 없는 명령입니다."

        await query.edit_message_text(message, parse_mode='HTML', reply_markup=get_menu_keyboard())

    except Exception as e:
        logger.error(f"Error in button callback: {e}")
        await query.edit_message_text(
            f"⚠️ 오류가 발생했습니다: {str(e)}",
            reply_markup=get_menu_keyboard()
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command - show available commands"""
    help_text = """⚽ <b>Birmingham City FC 봇</b>

<b>명령어:</b>
/menu - 메뉴 버튼 표시
/update - 전체 경기 정보 조회
/help - 도움말 표시

<b>버튼:</b>
📋 전체 정보 - 모든 경기 정보
📆 향후 경기 - 다음 5경기 일정
📊 최근 결과 - 최근 5경기 결과
🏆 리그 순위표 - 현재 순위 상세"""

    await update.message.reply_text(help_text, parse_mode='HTML', reply_markup=get_menu_keyboard())


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    start_text = """⚽ <b>Birmingham City FC 알리미</b>에 오신 것을 환영합니다!

아래 버튼을 눌러 원하는 정보를 확인하세요."""

    await update.message.reply_text(start_text, parse_mode='HTML', reply_markup=get_menu_keyboard())


def main() -> None:
    """Start the bot"""
    print(f"[{datetime.now()}] Starting Birmingham City FC Telegram Bot Server...")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("update", update_command))
    application.add_handler(CallbackQueryHandler(button_callback))

    print("Bot is running. Press Ctrl+C to stop.")
    print("Available commands: /start, /help, /menu, /update")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
