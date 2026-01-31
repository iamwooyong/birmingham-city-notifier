"""
Database operations for Birmingham City FC Bot
Uses SQLite for storing user preferences
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import contextmanager


class Database:
    """SQLite database manager for the Birmingham bot"""

    def __init__(self, db_path: str = "data/birmingham.db"):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_directory()
        self._init_tables()

    def _ensure_directory(self):
        """Ensure the data directory exists"""
        dir_path = os.path.dirname(self.db_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_tables(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Users table with notification settings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT UNIQUE NOT NULL,
                    username TEXT,
                    morning_notification INTEGER DEFAULT 1,
                    morning_notification_hour INTEGER DEFAULT 9,
                    match_reminder_minutes INTEGER DEFAULT 30,
                    goal_notification INTEGER DEFAULT 1,
                    lineup_notification INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create index
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_chat_id ON users(chat_id)")

    def get_or_create_user(self, chat_id: str, username: str = None) -> Dict[str, Any]:
        """
        Get existing user or create new one

        Args:
            chat_id: Telegram chat ID
            username: Telegram username (optional)

        Returns:
            User dictionary
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Try to get existing user
            cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
            user = cursor.fetchone()

            if user:
                # Update username if changed
                if username and user["username"] != username:
                    cursor.execute(
                        "UPDATE users SET username = ? WHERE chat_id = ?",
                        (username, chat_id)
                    )
                return dict(user)

            # Create new user
            cursor.execute(
                "INSERT INTO users (chat_id, username) VALUES (?, ?)",
                (chat_id, username)
            )
            cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
            return dict(cursor.fetchone())

    def get_user(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """Get user by chat ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
            user = cursor.fetchone()
            return dict(user) if user else None

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            return [dict(row) for row in cursor.fetchall()]

    def update_morning_notification(self, chat_id: str, enabled: bool) -> bool:
        """Enable/disable morning notifications for user"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET morning_notification = ? WHERE chat_id = ?",
                (1 if enabled else 0, chat_id)
            )
            return cursor.rowcount > 0

    def update_morning_notification_hour(self, chat_id: str, hour: int) -> bool:
        """Update morning notification hour for user"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET morning_notification_hour = ? WHERE chat_id = ?",
                (hour, chat_id)
            )
            return cursor.rowcount > 0

    def update_match_reminder(self, chat_id: str, minutes: int) -> bool:
        """Update match reminder time (minutes before match)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET match_reminder_minutes = ? WHERE chat_id = ?",
                (minutes, chat_id)
            )
            return cursor.rowcount > 0

    def update_goal_notification(self, chat_id: str, enabled: bool) -> bool:
        """Enable/disable goal notifications for user"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET goal_notification = ? WHERE chat_id = ?",
                (1 if enabled else 0, chat_id)
            )
            return cursor.rowcount > 0

    def update_lineup_notification(self, chat_id: str, enabled: bool) -> bool:
        """Enable/disable lineup notifications for user"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET lineup_notification = ? WHERE chat_id = ?",
                (1 if enabled else 0, chat_id)
            )
            return cursor.rowcount > 0

    def toggle_setting(self, chat_id: str, setting_name: str) -> bool:
        """Toggle a boolean setting and return new value"""
        user = self.get_user(chat_id)
        if not user:
            return False

        current = user.get(setting_name, 1)
        new_value = 0 if current else 1

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE users SET {setting_name} = ? WHERE chat_id = ?",
                (new_value, chat_id)
            )

        return bool(new_value)

    def get_users_for_morning_notification(self, hour: int) -> List[Dict[str, Any]]:
        """Get all users with morning notification enabled at specific hour"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM users
                WHERE morning_notification = 1
                AND morning_notification_hour = ?
            """, (hour,))
            return [dict(row) for row in cursor.fetchall()]

    def get_users_for_goal_notification(self) -> List[Dict[str, Any]]:
        """Get all users with goal notification enabled"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM users
                WHERE goal_notification = 1
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_users_for_lineup_notification(self) -> List[Dict[str, Any]]:
        """Get all users with lineup notification enabled"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM users
                WHERE lineup_notification = 1
            """)
            return [dict(row) for row in cursor.fetchall()]


# Singleton instance
_db_instance: Optional[Database] = None


def get_database(db_path: str = "data/birmingham.db") -> Database:
    """Get or create database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(db_path)
    return _db_instance
