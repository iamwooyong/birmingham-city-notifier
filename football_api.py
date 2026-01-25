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

    def get_team_standing(self) -> Optional[Dict]:
        """
        Get Birmingham City's current league standing

        Returns:
            Dictionary with standing information or None if not found
        """
        # Championship is competition ID 2016 in football-data.org
        data = self._make_request("competitions/2016/standings")

        if not data or "standings" not in data:
            return None

        # Find Birmingham City and 6th place team in the standings
        birmingham_standing = None
        sixth_place_points = 0

        for standing_type in data["standings"]:
            if standing_type.get("type") == "TOTAL":
                table = standing_type.get("table", [])

                # Find Birmingham City
                for team in table:
                    if team.get("team", {}).get("id") == self.team_id:
                        birmingham_standing = {
                            "position": team.get("position", 0),
                            "played": team.get("playedGames", 0),
                            "won": team.get("won", 0),
                            "draw": team.get("draw", 0),
                            "lost": team.get("lost", 0),
                            "points": team.get("points", 0),
                            "goals_for": team.get("goalsFor", 0),
                            "goals_against": team.get("goalsAgainst", 0),
                            "goal_difference": team.get("goalDifference", 0)
                        }

                # Find 6th place team points (playoff position)
                for team in table:
                    if team.get("position") == 6:
                        sixth_place_points = team.get("points", 0)
                        break

                break

        if birmingham_standing:
            # Calculate points needed to reach playoff position (6th place)
            current_points = birmingham_standing["points"]
            points_to_playoff = sixth_place_points - current_points

            # If already in playoff position or above, points_to_playoff will be 0 or negative
            if points_to_playoff < 0:
                points_to_playoff = 0
            elif points_to_playoff == 0 and birmingham_standing["position"] > 6:
                points_to_playoff = 1  # Need at least 1 more point if tied but outside playoff

            birmingham_standing["playoff_points"] = sixth_place_points
            birmingham_standing["points_to_playoff"] = points_to_playoff

        return birmingham_standing

    def get_upcoming_future_matches(self, limit: int = 3) -> List[Dict]:
        """
        Get upcoming future matches (up to limit count)

        Args:
            limit: Maximum number of future matches to retrieve (default: 3)

        Returns:
            List of upcoming match dictionaries (up to limit count)
        """
        # Search for matches in the next 60 days to ensure we get enough scheduled matches
        date_from = datetime.now().strftime("%Y-%m-%d")
        date_to = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")

        params = {
            "dateFrom": date_from,
            "dateTo": date_to,
            "status": "SCHEDULED,TIMED"  # Only get scheduled matches
        }

        data = self._make_request(f"teams/{self.team_id}/matches", params)

        if not data or "matches" not in data:
            return []

        # Sort by date ascending and return the first 'limit' matches
        matches = data["matches"]
        sorted_matches = sorted(matches, key=lambda x: x.get("utcDate", ""))
        return sorted_matches[:limit]

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

        print("=== Upcoming Future Matches (Next 3) ===")
        future_matches = client.get_upcoming_future_matches(limit=3)
        for match in future_matches:
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
