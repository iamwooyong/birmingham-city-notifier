"""
Telegram Bot module for sending Birmingham City FC match notifications
"""

import asyncio
from telegram import Bot
from telegram.error import TelegramError
from typing import List, Dict
from datetime import datetime


class TelegramNotifier:
    """Telegram bot for sending match notifications"""

    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram notifier

        Args:
            bot_token: Telegram bot token from BotFather
            chat_id: Telegram chat ID to send messages to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.bot = Bot(token=bot_token)

    async def send_message(self, message: str) -> bool:
        """
        Send a message to the configured chat

        Args:
            message: Message text to send

        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            return True
        except TelegramError as e:
            print(f"Failed to send Telegram message: {e}")
            return False

    def format_match_notification(
        self,
        upcoming_matches: List[Dict],
        this_week_matches: List[Dict],
        next_week_matches: List[Dict],
        recent_results: List[Dict],
        team_name: str = "버밍엄 시티 FC"
    ) -> str:
        """
        Format match information into a notification message

        Args:
            upcoming_matches: List of upcoming matches (today/tomorrow)
            this_week_matches: List of matches this week
            next_week_matches: List of matches next week
            recent_results: List of recent match results (last 5 games)
            team_name: Team name to display

        Returns:
            Formatted message string
        """
        today = datetime.now().strftime("%Y-%m-%d")
        message_parts = [f"⚽ <b>{team_name} 경기 정보</b> ({today})\n"]

        # 1. Upcoming matches (today/tomorrow)
        message_parts.append("📅 <b>오늘/내일 경기:</b>")
        if upcoming_matches:
            for match in upcoming_matches:
                home = match.get("home_team", "Unknown")
                away = match.get("away_team", "Unknown")
                korea_time = match.get("korea_time", "Unknown")
                uk_time = match.get("uk_time", "Unknown")
                venue = match.get("venue", "Unknown")

                message_parts.append(f"🇰🇷 한국: {korea_time} / 🇬🇧 영국: {uk_time}")
                message_parts.append(f"{home} vs {away}")
                if venue != "Unknown":
                    message_parts.append(f"장소: {venue}")
                message_parts.append("")
        else:
            message_parts.append("오늘/내일 예정된 경기가 없습니다.\n")

        # 2. This week matches
        if this_week_matches:
            message_parts.append("📆 <b>이번주 경기 일정:</b>")
            for match in this_week_matches:
                home = match.get("home_team", "Unknown")
                away = match.get("away_team", "Unknown")
                korea_time = match.get("korea_time", "Unknown")
                uk_time = match.get("uk_time", "Unknown")

                # Determine if Birmingham is home or away
                is_home = "버밍엄" in home or "Birmingham" in home
                location = "(홈)" if is_home else "(원정)"
                opponent = away if is_home else home

                message_parts.append(f"🇰🇷 {korea_time} / 🇬🇧 {uk_time}")
                message_parts.append(f"vs {opponent} {location}")
                message_parts.append("")

        # 3. Next week matches
        if next_week_matches:
            message_parts.append("📆 <b>다음주 경기 일정:</b>")
            for match in next_week_matches:
                home = match.get("home_team", "Unknown")
                away = match.get("away_team", "Unknown")
                korea_time = match.get("korea_time", "Unknown")
                uk_time = match.get("uk_time", "Unknown")

                # Determine if Birmingham is home or away
                is_home = "버밍엄" in home or "Birmingham" in home
                location = "(홈)" if is_home else "(원정)"
                opponent = away if is_home else home

                message_parts.append(f"🇰🇷 {korea_time} / 🇬🇧 {uk_time}")
                message_parts.append(f"vs {opponent} {location}")
                message_parts.append("")

        # 4. Recent results (last 5 games)
        if recent_results:
            message_parts.append("📊 <b>최근 경기 결과 (최근 5경기):</b>")
            for match in recent_results:
                home = match.get("home_team", "Unknown")
                away = match.get("away_team", "Unknown")
                korea_time = match.get("korea_time", "Unknown")
                uk_time = match.get("uk_time", "Unknown")
                home_score = match.get("home_score", 0)
                away_score = match.get("away_score", 0)

                # Determine if Birmingham won, lost, or drew
                is_home = "버밍엄" in home or "Birmingham" in home
                is_away = "버밍엄" in away or "Birmingham" in away

                if is_home:
                    result_emoji = "✅" if home_score > away_score else ("❌" if home_score < away_score else "🟰")
                elif is_away:
                    result_emoji = "✅" if away_score > home_score else ("❌" if away_score < home_score else "🟰")
                else:
                    result_emoji = ""

                message_parts.append(f"🇰🇷 {korea_time} / 🇬🇧 {uk_time}")
                message_parts.append(f"{home} {home_score} - {away_score} {away} {result_emoji}")
                message_parts.append("")

        # If absolutely no matches at all
        if not upcoming_matches and not this_week_matches and not next_week_matches and not recent_results:
            message_parts.append("\n현재 예정된 경기 및 최근 결과가 없습니다.")
            message_parts.append("다음 경기 일정을 기다려주세요.")

        return "\n".join(message_parts)

    def send_notification_sync(
        self,
        upcoming_matches: List[Dict],
        this_week_matches: List[Dict],
        next_week_matches: List[Dict],
        recent_results: List[Dict]
    ) -> bool:
        """
        Synchronous wrapper for sending match notifications

        Args:
            upcoming_matches: List of upcoming matches
            this_week_matches: List of this week matches
            next_week_matches: List of next week matches
            recent_results: List of recent results

        Returns:
            True if notification was sent successfully
        """
        message = self.format_match_notification(
            upcoming_matches,
            this_week_matches,
            next_week_matches,
            recent_results
        )

        # Run async function in sync context
        return asyncio.run(self.send_message(message))


# Test the Telegram bot when run directly
if __name__ == "__main__":
    import sys

    try:
        from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

        notifier = TelegramNotifier(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)

        # Test with sample data
        test_upcoming = [
            {
                "home_team": "Birmingham City",
                "away_team": "Leeds United",
                "korea_time": "2026-01-27 00:00",
                "uk_time": "2026-01-26 15:00",
                "venue": "St Andrew's Stadium"
            }
        ]

        test_this_week = [
            {
                "home_team": "Birmingham City",
                "away_team": "Norwich City",
                "korea_time": "2026-01-29 04:45",
                "uk_time": "2026-01-28 19:45"
            }
        ]

        test_next_week = [
            {
                "home_team": "Millwall",
                "away_team": "Birmingham City",
                "korea_time": "2026-02-02 00:00",
                "uk_time": "2026-02-01 15:00"
            }
        ]

        test_results = [
            {
                "home_team": "Birmingham City",
                "away_team": "Sheffield Wednesday",
                "korea_time": "2026-01-24 04:45",
                "uk_time": "2026-01-23 19:45",
                "home_score": 2,
                "away_score": 1
            },
            {
                "home_team": "Leeds United",
                "away_team": "Birmingham City",
                "korea_time": "2026-01-20 04:00",
                "uk_time": "2026-01-19 19:00",
                "home_score": 1,
                "away_score": 1
            }
        ]

        print("Sending test notification...")
        success = notifier.send_notification_sync(
            test_upcoming,
            test_this_week,
            test_next_week,
            test_results
        )

        if success:
            print("[SUCCESS] Test notification sent successfully!")
        else:
            print("[FAILED] Failed to send test notification")
            sys.exit(1)

    except ImportError:
        print("Please create config.py with TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
