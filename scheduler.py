"""
Scheduler for Birmingham City FC Bot
Handles morning notifications, match reminders, live scores, and lineups
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot

from config import TELEGRAM_BOT_TOKEN, BIRMINGHAM_TEAM_ID
from database import get_database
from football_api import FootballAPIClient

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class NotificationScheduler:
    """Handles scheduled notifications for Birmingham City FC bot"""

    def __init__(self, api_key: str, db_path: str = "data/birmingham.db"):
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.db = get_database(db_path)
        self.api = FootballAPIClient(api_key, BIRMINGHAM_TEAM_ID)
        self.scheduler = BackgroundScheduler()
        self._match_jobs = {}  # Track scheduled match reminder jobs
        self._live_scores = {}  # Track live match scores for goal detection
        self._lineup_sent = {}  # Track which lineups have been sent

    def start(self):
        """Start the scheduler"""
        # Schedule morning notification - run every hour from 7 AM to 11 AM
        self.scheduler.add_job(
            self._run_morning_notifications,
            CronTrigger(hour="7-11", minute=0),
            id="morning_notification",
            replace_existing=True
        )

        # Schedule match reminder check every 5 minutes
        self.scheduler.add_job(
            self._run_match_reminder_check,
            CronTrigger(minute="*/5"),
            id="match_reminder_check",
            replace_existing=True
        )

        # Schedule live score check every 3 minutes
        self.scheduler.add_job(
            self._run_live_score_check,
            CronTrigger(minute="*/3"),
            id="live_score_check",
            replace_existing=True
        )

        # Schedule lineup check every 30 minutes
        self.scheduler.add_job(
            self._run_lineup_check,
            CronTrigger(minute="*/30"),
            id="lineup_check",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Scheduler started. Morning: 7-11AM, Live score: every 3min, Lineup: every 30min")

    def _run_morning_notifications(self):
        """Sync wrapper for morning notifications"""
        asyncio.run(self.send_morning_notifications())

    def _run_match_reminder_check(self):
        """Sync wrapper for match reminder check"""
        asyncio.run(self.check_and_schedule_match_reminders())

    def _run_live_score_check(self):
        """Sync wrapper for live score check"""
        asyncio.run(self.check_live_scores())

    def _run_lineup_check(self):
        """Sync wrapper for lineup check"""
        asyncio.run(self.check_lineups())

    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")

    async def send_morning_notifications(self):
        """Send morning notifications to users whose notification hour matches current time"""
        current_hour = datetime.now().hour
        logger.info(f"Starting morning notification job for hour {current_hour}...")

        users = self.db.get_users_for_morning_notification(hour=current_hour)
        logger.info(f"Found {len(users)} users for morning notification at {current_hour}:00")

        for user in users:
            try:
                await self._send_morning_notification_to_user(user)
            except Exception as e:
                logger.error(f"Failed to send morning notification to {user['chat_id']}: {e}")

    async def _send_morning_notification_to_user(self, user: Dict[str, Any]):
        """Send morning notification to a single user"""
        chat_id = user["chat_id"]

        now = datetime.now()
        today = now.strftime("%m/%d")
        tomorrow = (now + timedelta(days=1)).strftime("%m/%d")
        today_matches = []

        # Get Birmingham City matches
        matches = self.api.get_upcoming_matches(days_ahead=2)

        for match in matches:
            match_info = self.api.format_match_info(match)
            korea_time = match_info.get("korea_time", "")
            match_date = korea_time[:5]  # MM/DD
            match_time = korea_time[6:11] if len(korea_time) >= 11 else ""  # HH:MM

            # Include today's matches
            if match_date == today:
                today_matches.append(match_info)
            # Include tomorrow's early morning matches (00:00 ~ 09:00)
            elif match_date == tomorrow and match_time < "09:00":
                today_matches.append(match_info)

        if today_matches:
            message = self._format_morning_message(today_matches)
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info(f"Morning notification sent to {chat_id}: {len(today_matches)} matches")

    def _format_morning_message(self, matches: List[Dict]) -> str:
        """Format morning notification message"""
        lines = [
            f"<b>⚽ 오늘의 버밍엄 시티 경기</b>",
            f"<i>{datetime.now().strftime('%Y년 %m월 %d일')}</i>\n"
        ]

        for match in matches:
            home = match.get("home_team", "")
            away = match.get("away_team", "")
            korea_time = match.get("korea_time", "")

            lines.append(f"⏰ {korea_time}")
            lines.append(f"   {home} vs {away}\n")

        lines.append("KRO! 💙")

        return "\n".join(lines)

    async def check_and_schedule_match_reminders(self):
        """Check for upcoming matches and schedule reminders"""
        logger.debug("Checking for matches to schedule reminders...")

        users = self.db.get_all_users()

        for user in users:
            try:
                await self._schedule_reminders_for_user(user)
            except Exception as e:
                logger.error(f"Failed to schedule reminders for {user['chat_id']}: {e}")

    async def _schedule_reminders_for_user(self, user: Dict[str, Any]):
        """Schedule match reminders for a single user"""
        chat_id = user["chat_id"]
        reminder_minutes = user.get("match_reminder_minutes", 30)

        if reminder_minutes <= 0:
            return

        matches = self.api.get_upcoming_matches(days_ahead=1)

        for match in matches:
            match_info = self.api.format_match_info(match)
            match_id = match.get("id")

            if not match_id:
                continue

            job_id = f"reminder_{chat_id}_{match_id}"

            # Skip if already scheduled
            if job_id in self._match_jobs:
                continue

            # Calculate reminder time
            try:
                utc_time = match.get("utcDate", "")
                match_datetime = datetime.fromisoformat(utc_time.replace("Z", "+00:00"))

                # Convert to local time and calculate reminder time
                reminder_time = match_datetime - timedelta(minutes=reminder_minutes)
                now = datetime.now(reminder_time.tzinfo)

                # Only schedule if reminder time is in the future and within 2 hours
                if now < reminder_time < now + timedelta(hours=2):
                    self.scheduler.add_job(
                        self._run_send_match_reminder,
                        'date',
                        run_date=reminder_time,
                        args=[chat_id, match_info, reminder_minutes],
                        id=job_id
                    )
                    self._match_jobs[job_id] = True
                    logger.info(f"Scheduled reminder for {chat_id}: {job_id} at {reminder_time}")

            except Exception as e:
                logger.error(f"Failed to parse match time: {e}")

    def _run_send_match_reminder(self, chat_id: str, match_info: Dict, minutes: int):
        """Sync wrapper for sending match reminder"""
        asyncio.run(self._send_match_reminder(chat_id, match_info, minutes))

    async def _send_match_reminder(self, chat_id: str, match_info: Dict, minutes: int):
        """Send match start reminder"""
        try:
            home = match_info.get("home_team", "")
            away = match_info.get("away_team", "")
            korea_time = match_info.get("korea_time", "")

            message = (
                f"<b>⏰ 경기 시작 알림</b>\n\n"
                f"<b>Birmingham City</b> 경기가 {minutes}분 후에 시작합니다!\n\n"
                f"🏟️ {home} vs {away}\n"
                f"📍 {korea_time}"
            )

            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info(f"Match reminder sent to {chat_id}")

        except Exception as e:
            logger.error(f"Failed to send match reminder to {chat_id}: {e}")

    # ============ Live Score Notifications ============

    async def check_live_scores(self):
        """Check for live matches and detect goals"""
        try:
            # Get all users with goal notification enabled
            users = self.db.get_users_for_goal_notification()
            if not users:
                return

            # Get live matches for Birmingham
            live_matches = self.api.get_live_matches()

            for match in live_matches:
                await self._process_live_match(match, users)

        except Exception as e:
            logger.error(f"Error checking live scores: {e}")

    async def _process_live_match(self, match: Dict, users: List[Dict]):
        """Process a live match for goal detection"""
        match_id = match.get("id")
        if not match_id:
            return

        home_team = match.get("homeTeam", {})
        away_team = match.get("awayTeam", {})
        home_id = home_team.get("id")
        away_id = away_team.get("id")
        home_name = home_team.get("name", "")
        away_name = away_team.get("name", "")

        score = match.get("score", {}).get("fullTime", {})
        home_score = score.get("home", 0) or 0
        away_score = score.get("away", 0) or 0

        # Get previous score
        prev_score = self._live_scores.get(match_id, {"home": 0, "away": 0})
        prev_home = prev_score.get("home", 0)
        prev_away = prev_score.get("away", 0)

        # Detect goal
        if home_score > prev_home or away_score > prev_away:
            # Goal detected!
            if home_score > prev_home:
                scoring_team = home_name
                scoring_team_id = home_id
            else:
                scoring_team = away_name
                scoring_team_id = away_id

            is_birmingham_goal = scoring_team_id == BIRMINGHAM_TEAM_ID

            # Notify all users with goal notification enabled
            for user in users:
                await self._send_goal_notification(
                    user["chat_id"],
                    home_name, away_name,
                    home_score, away_score,
                    scoring_team,
                    is_birmingham_goal
                )

        # Update stored score
        self._live_scores[match_id] = {"home": home_score, "away": away_score}

    async def _send_goal_notification(self, chat_id: str,
                                      home_name: str, away_name: str,
                                      home_score: int, away_score: int,
                                      scoring_team: str, is_birmingham_goal: bool):
        """Send goal notification to user"""
        try:
            emoji = "🎉" if is_birmingham_goal else "⚽"
            message = (
                f"<b>{emoji} 골!</b>\n\n"
                f"<b>{scoring_team}</b> 득점!\n\n"
                f"🏟️ {home_name} {home_score} - {away_score} {away_name}"
            )

            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info(f"Goal notification sent to {chat_id}")

        except Exception as e:
            logger.error(f"Failed to send goal notification to {chat_id}: {e}")

    # ============ Lineup Notifications ============

    async def check_lineups(self):
        """Check for upcoming match lineups"""
        try:
            users = self.db.get_users_for_lineup_notification()
            if not users:
                return

            # Get today's matches
            today_matches = self.api.get_today_matches()

            for match in today_matches:
                await self._process_lineup(match, users)

        except Exception as e:
            logger.error(f"Error checking lineups: {e}")

    async def _process_lineup(self, match: Dict, users: List[Dict]):
        """Process a match for lineup notification"""
        match_id = match.get("id")
        status = match.get("status")

        # Only check matches that are about to start (within 1 hour)
        if status not in ["TIMED", "SCHEDULED"]:
            return

        # Check if lineup already sent
        if match_id in self._lineup_sent:
            return

        # Check if match starts within 1 hour
        try:
            utc_time = match.get("utcDate", "")
            match_datetime = datetime.fromisoformat(utc_time.replace("Z", "+00:00"))
            now = datetime.now(match_datetime.tzinfo)

            time_until_match = (match_datetime - now).total_seconds() / 60

            # Only check if match is within 60 minutes
            if time_until_match > 60 or time_until_match < 0:
                return

        except Exception:
            return

        # Get match details with lineups
        match_details = self.api.get_match_details(match_id)
        if not match_details:
            return

        # Check if lineups are available
        home_lineup = match_details.get("homeTeam", {}).get("lineup", [])
        away_lineup = match_details.get("awayTeam", {}).get("lineup", [])

        if not home_lineup and not away_lineup:
            return

        # Notify all users with lineup notification enabled
        for user in users:
            await self._send_lineup_notification(user["chat_id"], match_details)

        # Mark as sent
        self._lineup_sent[match_id] = True

    async def _send_lineup_notification(self, chat_id: str, match_details: Dict):
        """Send lineup notification to user"""
        try:
            home_team = match_details.get("homeTeam", {})
            away_team = match_details.get("awayTeam", {})
            home_name = home_team.get("name", "")
            away_name = away_team.get("name", "")

            home_lineup = home_team.get("lineup", [])
            away_lineup = away_team.get("lineup", [])

            lines = [
                f"<b>📋 선발 라인업</b>\n",
                f"<b>{home_name} vs {away_name}</b>\n"
            ]

            if home_lineup:
                lines.append(f"\n<b>{home_name}</b>")
                for player in home_lineup[:11]:
                    name = player.get("name", "")
                    position = player.get("position", "")
                    lines.append(f"  {position}: {name}")

            if away_lineup:
                lines.append(f"\n<b>{away_name}</b>")
                for player in away_lineup[:11]:
                    name = player.get("name", "")
                    position = player.get("position", "")
                    lines.append(f"  {position}: {name}")

            message = "\n".join(lines)

            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info(f"Lineup notification sent to {chat_id}")

        except Exception as e:
            logger.error(f"Failed to send lineup notification to {chat_id}: {e}")


# Singleton instance
_scheduler_instance = None


def get_scheduler(api_key: str, db_path: str = "data/birmingham.db") -> NotificationScheduler:
    """Get or create scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = NotificationScheduler(api_key, db_path)
    return _scheduler_instance
