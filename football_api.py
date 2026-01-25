"""
Football API Client for football-data.org
Fetches Birmingham City FC match schedules and results
"""

import requests
import pytz
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class FootballAPIClient:
    """Client for interacting with football-data.org API"""

    BASE_URL = "https://api.football-data.org/v4"

    def __init__(self, api_key: str, team_id: int = 332):
        """
        Initialize the API client

        Args:
            api_key: football-data.org API key
            team_id: Birmingham City FC team ID (default: 332)
        """
        self.api_key = api_key
        self.team_id = team_id
        self.headers = {
            "X-Auth-Token": api_key
        }

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make a request to the API

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            JSON response as dictionary
        """
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return {}

    def get_upcoming_matches(self, days_ahead: int = 2) -> List[Dict]:
        """
        Get upcoming matches for Birmingham City (today/tomorrow)

        Args:
            days_ahead: Number of days to look ahead (default: 2 for today/tomorrow)

        Returns:
            List of upcoming match dictionaries
        """
        date_from = datetime.now().strftime("%Y-%m-%d")
        date_to = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

        params = {
            "dateFrom": date_from,
            "dateTo": date_to
        }

        data = self._make_request(f"teams/{self.team_id}/matches", params)

        if not data or "matches" not in data:
            return []

        return data["matches"]

    def get_recent_results(self, limit: int = 5) -> List[Dict]:
        """
        Get recent match results for Birmingham City

        Args:
            limit: Number of recent matches to retrieve (default: 5)

        Returns:
            List of recent match dictionaries with results
        """
        # Get matches from the last 60 days to ensure we have enough finished matches
        date_to = datetime.now().strftime("%Y-%m-%d")
        date_from = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")

        params = {
            "dateFrom": date_from,
            "dateTo": date_to,
            "status": "FINISHED"
        }

        data = self._make_request(f"teams/{self.team_id}/matches", params)

        if not data or "matches" not in data:
            return []

        # Return only the most recent 'limit' matches
        matches = data["matches"]
        # Sort by date descending and return the latest ones
        sorted_matches = sorted(matches, key=lambda x: x.get("utcDate", ""), reverse=True)
        return sorted_matches[:limit]

    def get_this_week_matches(self) -> List[Dict]:
        """
        Get matches for this week (until Sunday)

        Returns:
            List of match dictionaries for this week
        """
        now = datetime.now()
        # Calculate days until Sunday
        days_until_sunday = (6 - now.weekday()) % 7
        if days_until_sunday == 0:
            days_until_sunday = 7  # If today is Sunday, get until next Sunday

        date_from = now.strftime("%Y-%m-%d")
        date_to = (now + timedelta(days=days_until_sunday)).strftime("%Y-%m-%d")

        params = {
            "dateFrom": date_from,
            "dateTo": date_to
        }

        data = self._make_request(f"teams/{self.team_id}/matches", params)

        if not data or "matches" not in data:
            return []

        return data["matches"]

    def get_next_week_matches_only(self) -> List[Dict]:
        """
        Get matches for next week only (Monday to Sunday of next week)

        Returns:
            List of match dictionaries for next week
        """
        now = datetime.now()
        # Calculate next Monday
        days_until_next_monday = (7 - now.weekday()) % 7
        if days_until_next_monday == 0:
            days_until_next_monday = 7

        next_monday = now + timedelta(days=days_until_next_monday)
        next_sunday = next_monday + timedelta(days=6)

        date_from = next_monday.strftime("%Y-%m-%d")
        date_to = next_sunday.strftime("%Y-%m-%d")

        params = {
            "dateFrom": date_from,
            "dateTo": date_to
        }

        data = self._make_request(f"teams/{self.team_id}/matches", params)

        if not data or "matches" not in data:
            return []

        return data["matches"]

    @staticmethod
    def format_match_info(match: Dict) -> Dict:
        """
        Format match information for display with timezone info

        Args:
            match: Match dictionary from API

        Returns:
            Formatted match information including UK and Korea times
        """
        home_team = match.get("homeTeam", {}).get("name", "Unknown")
        away_team = match.get("awayTeam", {}).get("name", "Unknown")
        match_date = match.get("utcDate", "")
        venue = match.get("venue", "Unknown")
        status = match.get("status", "SCHEDULED")

        # Parse date and convert to timezones
        uk_time_str = ""
        korea_time_str = ""
        formatted_date = match_date

        try:
            # Parse UTC time
            dt_utc = datetime.fromisoformat(match_date.replace("Z", "+00:00"))

            # Convert to UK time (Europe/London)
            uk_tz = pytz.timezone('Europe/London')
            dt_uk = dt_utc.astimezone(uk_tz)
            uk_time_str = dt_uk.strftime("%Y-%m-%d %H:%M")

            # Convert to Korea time (Asia/Seoul)
            korea_tz = pytz.timezone('Asia/Seoul')
            dt_korea = dt_utc.astimezone(korea_tz)
            korea_time_str = dt_korea.strftime("%Y-%m-%d %H:%M")

            formatted_date = dt_utc.strftime("%Y-%m-%d %H:%M")
        except:
            formatted_date = match_date

        result = {
            "home_team": home_team,
            "away_team": away_team,
            "date": formatted_date,
            "uk_time": uk_time_str,
            "korea_time": korea_time_str,
            "venue": venue,
            "status": status
        }

        # Add score if match is finished
        if status == "FINISHED":
            score = match.get("score", {}).get("fullTime", {})
            result["home_score"] = score.get("home", 0)
            result["away_score"] = score.get("away", 0)

        return result


# Test the API client when run directly
if __name__ == "__main__":
    # This is for testing purposes only
    # You need to replace with your actual API key
    import sys

    try:
        from config import FOOTBALL_API_KEY, BIRMINGHAM_TEAM_ID

        client = FootballAPIClient(FOOTBALL_API_KEY, BIRMINGHAM_TEAM_ID)

        print("=== Upcoming Matches (Today/Tomorrow) ===")
        upcoming = client.get_upcoming_matches(days_ahead=2)
        for match in upcoming:
            info = client.format_match_info(match)
            print(f"UK: {info['uk_time']} / KR: {info['korea_time']}")
            print(f"{info['home_team']} vs {info['away_team']}\n")

        print("=== Recent Results (Last 5) ===")
        recent = client.get_recent_results(limit=5)
        for match in recent:
            info = client.format_match_info(match)
            print(f"UK: {info['uk_time']} / KR: {info['korea_time']}")
            print(f"{info['home_team']} {info.get('home_score', 0)} - {info.get('away_score', 0)} {info['away_team']}\n")

        print("=== This Week Matches ===")
        this_week = client.get_this_week_matches()
        for match in this_week:
            info = client.format_match_info(match)
            print(f"UK: {info['uk_time']} / KR: {info['korea_time']}")
            print(f"{info['home_team']} vs {info['away_team']}\n")

        print("=== Next Week Matches ===")
        next_week = client.get_next_week_matches_only()
        for match in next_week:
            info = client.format_match_info(match)
            print(f"UK: {info['uk_time']} / KR: {info['korea_time']}")
            print(f"{info['home_team']} vs {info['away_team']}\n")

    except ImportError:
        print("Please create config.py with FOOTBALL_API_KEY and BIRMINGHAM_TEAM_ID")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
