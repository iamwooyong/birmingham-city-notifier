"""
Settings manager for Birmingham City FC Bot
Uses JSON file for storing notification preferences
"""

import json
import os
from typing import Dict, Any

# Default settings
DEFAULT_SETTINGS = {
    "morning_notification": True,
    "morning_notification_hour": 9,
    "match_reminder_minutes": 30,
    "goal_notification": True,
    "lineup_notification": True
}

SETTINGS_FILE = "data/settings.json"


def _ensure_directory():
    """Ensure the data directory exists"""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)


def load_settings() -> Dict[str, Any]:
    """Load settings from JSON file"""
    _ensure_directory()

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                # Merge with defaults for any missing keys
                for key, value in DEFAULT_SETTINGS.items():
                    if key not in settings:
                        settings[key] = value
                return settings
        except (json.JSONDecodeError, IOError):
            pass

    return DEFAULT_SETTINGS.copy()


def save_settings(settings: Dict[str, Any]) -> bool:
    """Save settings to JSON file"""
    _ensure_directory()

    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        return True
    except IOError:
        return False


def get_setting(key: str) -> Any:
    """Get a specific setting value"""
    settings = load_settings()
    return settings.get(key, DEFAULT_SETTINGS.get(key))


def update_setting(key: str, value: Any) -> bool:
    """Update a specific setting"""
    settings = load_settings()
    settings[key] = value
    return save_settings(settings)


def toggle_setting(key: str) -> bool:
    """Toggle a boolean setting and return new value"""
    settings = load_settings()
    current = settings.get(key, DEFAULT_SETTINGS.get(key, False))
    new_value = not current
    settings[key] = new_value
    save_settings(settings)
    return new_value
