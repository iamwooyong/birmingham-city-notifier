#!/usr/bin/env python3
"""
Birmingham City FC Telegram Bot Server
Listens for commands and sends match information on request
Supports multiple users with individual notification settings

Commands:
    /update - Get current match information
    /menu - Show menu with buttons
    /help - Show available commands
"""

import sys
import os
import logging
import subprocess
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from database import get_database
from scheduler import get_scheduler

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

# Initialize scheduler
scheduler = get_scheduler(FOOTBALL_API_KEY)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize API client and database
api_client = FootballAPIClient(FOOTBALL_API_KEY, BIRMINGHAM_TEAM_ID)
db = get_database()

# Restart flag file path
RESTART_FLAG_FILE = "/var/services/homes/admin/scripts/birmingham-city-notifier/.restart_flag"


def get_menu_keyboard():
    """Create inline keyboard with menu buttons"""
    keyboard = [
        [InlineKeyboardButton("📋 전체 정보", callback_data="all")],
        [
            InlineKeyboardButton("📆 향후 경기", callback_data="future"),
            InlineKeyboardButton("📊 최근 결과", callback_data="recent")
        ],
        [InlineKeyboardButton("🏆 리그 순위표", callback_data="standings")],
        [InlineKeyboardButton("🔔 알림 설정", callback_data="notifications")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_notification_keyboard(chat_id: str):
    """Create notification settings keyboard for specific user"""
    user = db.get_or_create_user(chat_id)

    morning_text = "🔔 아침 알림: 켜짐" if user.get("morning_notification") else "🔕 아침 알림: 꺼짐"
    morning_hour = user.get("morning_notification_hour", 9)
    reminder_minutes = user.get("match_reminder_minutes", 30)
    goal_text = "⚽ 골 알림: 켜짐" if user.get("goal_notification") else "⚽ 골 알림: 꺼짐"
    lineup_text = "📋 라인업 알림: 켜짐" if user.get("lineup_notification") else "📋 라인업 알림: 꺼짐"

    keyboard = [
        [InlineKeyboardButton(morning_text, callback_data="toggle_morning")],
        [InlineKeyboardButton(f"🕐 아침 알림 시간: {morning_hour}시", callback_data="morning_hour_settings")],
        [InlineKeyboardButton(f"⏰ 경기 알림: {reminder_minutes}분 전" if reminder_minutes > 0 else "⏰ 경기 알림: 꺼짐", callback_data="reminder_settings")],
        [InlineKeyboardButton(goal_text, callback_data="toggle_goal")],
        [InlineKeyboardButton(lineup_text, callback_data="toggle_lineup")],
        [InlineKeyboardButton("🔙 메뉴", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_morning_hour_keyboard():
    """Create morning hour selection keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("7시", callback_data="set_morning_hour_7"),
            InlineKeyboardButton("8시", callback_data="set_morning_hour_8"),
            InlineKeyboardButton("9시", callback_data="set_morning_hour_9")
        ],
        [
            InlineKeyboardButton("10시", callback_data="set_morning_hour_10"),
            InlineKeyboardButton("11시", callback_data="set_morning_hour_11")
        ],
        [InlineKeyboardButton("🔙 알림 설정", callback_data="notifications")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_reminder_keyboard():
    """Create match reminder selection keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("5분 전", callback_data="set_reminder_5"),
            InlineKeyboardButton("10분 전", callback_data="set_reminder_10"),
            InlineKeyboardButton("15분 전", callback_data="set_reminder_15")
        ],
        [
            InlineKeyboardButton("30분 전", callback_data="set_reminder_30"),
            InlineKeyboardButton("60분 전", callback_data="set_reminder_60"),
            InlineKeyboardButton("끄기", callback_data="set_reminder_0")
        ],
        [InlineKeyboardButton("🔙 알림 설정", callback_data="notifications")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /menu command - show menu with buttons"""
    chat_id = str(update.effective_chat.id)
    username = update.effective_user.username
    db.get_or_create_user(chat_id, username)

    await update.message.reply_text(
        "⚽ <b>Birmingham City FC</b>\n\n원하는 정보를 선택하세요:",
        parse_mode='HTML',
        reply_markup=get_menu_keyboard()
    )


async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /update command - fetch and send all match information"""
    chat_id = str(update.effective_chat.id)
    username = update.effective_user.username
    db.get_or_create_user(chat_id, username)
    logger.info(f"Received /update command from chat_id: {chat_id}")

    loading_msg = await update.message.reply_text("⏳ 경기 정보를 가져오는 중...")

    try:
        notifier = TelegramNotifier(TELEGRAM_BOT_TOKEN, chat_id)

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

    chat_id = str(update.effective_chat.id)
    username = update.effective_user.username
    callback_data = query.data
    logger.info(f"Button pressed: {callback_data} from chat_id: {chat_id}")

    # Ensure user exists
    db.get_or_create_user(chat_id, username)

    try:
        # Notification settings callbacks (no API calls needed)
        if callback_data == "main_menu":
            await query.edit_message_text(
                "⚽ <b>Birmingham City FC</b>\n\n원하는 정보를 선택하세요:",
                parse_mode='HTML',
                reply_markup=get_menu_keyboard()
            )
            return

        elif callback_data == "notifications":
            message = """<b>🔔 알림 설정</b>

아래 버튼을 눌러 알림을 설정하세요."""
            await query.edit_message_text(
                message,
                parse_mode='HTML',
                reply_markup=get_notification_keyboard(chat_id)
            )
            return

        elif callback_data == "toggle_morning":
            new_value = db.toggle_setting(chat_id, "morning_notification")
            status = "켜짐 ✅" if new_value else "꺼짐 ❌"
            message = f"""<b>🔔 알림 설정</b>

아침 알림이 {status}으로 변경되었습니다."""
            await query.edit_message_text(
                message,
                parse_mode='HTML',
                reply_markup=get_notification_keyboard(chat_id)
            )
            return

        elif callback_data == "toggle_goal":
            new_value = db.toggle_setting(chat_id, "goal_notification")
            status = "켜짐 ✅" if new_value else "꺼짐 ❌"
            message = f"""<b>🔔 알림 설정</b>

골 알림이 {status}으로 변경되었습니다."""
            await query.edit_message_text(
                message,
                parse_mode='HTML',
                reply_markup=get_notification_keyboard(chat_id)
            )
            return

        elif callback_data == "toggle_lineup":
            new_value = db.toggle_setting(chat_id, "lineup_notification")
            status = "켜짐 ✅" if new_value else "꺼짐 ❌"
            message = f"""<b>🔔 알림 설정</b>

라인업 알림이 {status}으로 변경되었습니다."""
            await query.edit_message_text(
                message,
                parse_mode='HTML',
                reply_markup=get_notification_keyboard(chat_id)
            )
            return

        elif callback_data == "morning_hour_settings":
            message = """<b>🕐 아침 알림 시간 설정</b>

몇 시에 아침 알림을 받을지 선택하세요."""
            await query.edit_message_text(
                message,
                parse_mode='HTML',
                reply_markup=get_morning_hour_keyboard()
            )
            return

        elif callback_data.startswith("set_morning_hour_"):
            hour = int(callback_data.split("_")[3])
            db.update_morning_notification_hour(chat_id, hour)
            message = f"""<b>🔔 알림 설정</b>

아침 알림 시간이 {hour}시로 변경되었습니다."""
            await query.edit_message_text(
                message,
                parse_mode='HTML',
                reply_markup=get_notification_keyboard(chat_id)
            )
            return

        elif callback_data == "reminder_settings":
            message = """<b>⏰ 경기 알림 시간 설정</b>

경기 시작 몇 분 전에 알림을 받을지 선택하세요."""
            await query.edit_message_text(
                message,
                parse_mode='HTML',
                reply_markup=get_reminder_keyboard()
            )
            return

        elif callback_data.startswith("set_reminder_"):
            minutes = int(callback_data.split("_")[2])
            db.update_match_reminder(chat_id, minutes)
            if minutes == 0:
                status_text = "경기 알림이 꺼졌습니다."
            else:
                status_text = f"경기 시작 {minutes}분 전에 알림을 보내드립니다."
            message = f"""<b>🔔 알림 설정</b>

{status_text}"""
            await query.edit_message_text(
                message,
                parse_mode='HTML',
                reply_markup=get_notification_keyboard(chat_id)
            )
            return

        # API calls for match data
        await query.edit_message_text("⏳ 정보를 가져오는 중...")

        notifier = TelegramNotifier(TELEGRAM_BOT_TOKEN, chat_id)
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
            # Full league table
            league_table = api_client.get_league_table()
            logger.info(f"League table: {len(league_table)} teams")
            message = notifier.format_standings(league_table, BIRMINGHAM_TEAM_ID)

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
    chat_id = str(update.effective_chat.id)
    username = update.effective_user.username
    db.get_or_create_user(chat_id, username)

    help_text = """⚽ <b>Birmingham City FC 봇</b>

<b>명령어:</b>
/menu - 메뉴 버튼 표시
/update - 전체 경기 정보 조회
/help - 도움말 표시

<b>버튼:</b>
📋 전체 정보 - 모든 경기 정보
📆 향후 경기 - 다음 5경기 일정
📊 최근 결과 - 최근 5경기 결과
🏆 리그 순위표 - 현재 순위 상세
🔔 알림 설정 - 알림 켜기/끄기"""

    await update.message.reply_text(help_text, parse_mode='HTML', reply_markup=get_menu_keyboard())


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    chat_id = str(update.effective_chat.id)
    username = update.effective_user.username
    db.get_or_create_user(chat_id, username)

    start_text = """⚽ <b>Birmingham City FC 알리미</b>에 오신 것을 환영합니다!

아래 버튼을 눌러 원하는 정보를 확인하세요."""

    await update.message.reply_text(start_text, parse_mode='HTML', reply_markup=get_menu_keyboard())


async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /restart command - pull latest code and restart bot (admin only)"""
    chat_id = str(update.effective_chat.id)

    # Check if user is admin
    if chat_id != str(TELEGRAM_CHAT_ID):
        logger.warning(f"Unauthorized /restart attempt from chat_id: {chat_id}")
        await update.message.reply_text("⛔ 권한이 없습니다.", reply_markup=get_menu_keyboard())
        return

    logger.info(f"Restart command received from admin: {chat_id}")
    await update.message.reply_text("🔄 봇을 업데이트하고 재시작합니다...")

    try:
        # Create restart flag file with chat_id
        with open(RESTART_FLAG_FILE, "w") as f:
            f.write(chat_id)

        # Run update.sh script
        script_path = "/var/services/homes/admin/scripts/birmingham-city-notifier/update.sh"
        subprocess.Popen(
            ["bash", script_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        logger.info("Update script started")
    except Exception as e:
        logger.error(f"Failed to run update script: {e}")
        await update.message.reply_text(f"⚠️ 재시작 실패: {str(e)}", reply_markup=get_menu_keyboard())


async def send_restart_success_message():
    """Send success message if bot was restarted via /restart command"""
    if os.path.exists(RESTART_FLAG_FILE):
        try:
            with open(RESTART_FLAG_FILE, "r") as f:
                chat_id = f.read().strip()

            # Delete flag file
            os.remove(RESTART_FLAG_FILE)

            # Send success message
            from telegram import Bot
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            await bot.send_message(
                chat_id=chat_id,
                text="✅ 봇이 성공적으로 업데이트되고 재시작되었습니다!",
                reply_markup=get_menu_keyboard()
            )
            logger.info(f"Restart success message sent to {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send restart success message: {e}")


def main() -> None:
    """Start the bot"""
    print(f"[{datetime.now()}] Starting Birmingham City FC Telegram Bot Server...")

    # Start the scheduler for notifications
    scheduler.start()
    print("Notification scheduler started")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(
        lambda app: send_restart_success_message()
    ).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("update", update_command))
    application.add_handler(CommandHandler("restart", restart_command))
    application.add_handler(CallbackQueryHandler(button_callback))

    print("Bot is running. Press Ctrl+C to stop.")
    print("Available commands: /start, /help, /menu, /update, /restart (admin only)")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
