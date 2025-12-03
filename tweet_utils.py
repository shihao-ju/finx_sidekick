"""
Utility functions for extracting tweet IDs and timestamps from summaries and tweets.
"""
import re
from typing import List, Dict, Optional
from datetime import datetime
import json
import os


def extract_tweet_ids_from_summary(summary: str) -> List[str]:
    """
    Extract tweet IDs from source URLs in a summary.
    Pattern: [Source: @handle](https://x.com/handle/status/TWEET_ID)
    
    Returns:
        List of unique tweet IDs found in the summary
    """
    # Pattern to match: [Source: @handle](https://x.com/handle/status/TWEET_ID)
    pattern = r'https?://(?:x\.com|twitter\.com)/\w+/status/(\d+)'
    matches = re.findall(pattern, summary)
    return list(set(matches))  # Remove duplicates


def get_tweet_timestamp(tweet_id: str, tweets_data: Optional[Dict] = None) -> Optional[datetime]:
    """
    Get timestamp for a tweet ID from tweets data.
    
    Args:
        tweet_id: Tweet ID to look up
        tweets_data: Dictionary with tweets data (from test_tweets_data.json format)
                    If None, loads from test_tweets_data.json
    
    Returns:
        datetime object or None if not found
    """
    if tweets_data is None:
        # Try to load from test_tweets_data.json
        if os.path.exists("test_tweets_data.json"):
            try:
                with open("test_tweets_data.json", "r", encoding="utf-8") as f:
                    tweets_data = json.load(f)
            except Exception:
                return None
        else:
            return None
    
    # Search through all accounts' tweets
    accounts = tweets_data.get("accounts", [])
    for account_data in accounts:
        tweets = account_data.get("tweets", [])
        for tweet in tweets:
            tweet_id_str = str(tweet.get("id_str") or tweet.get("id", ""))
            if tweet_id_str == str(tweet_id):
                created_at = tweet.get("createdAt")
                if created_at:
                    # Parse format: "Tue Dec 02 03:56:50 +0000 2025"
                    try:
                        # Try parsing the Twitter date format
                        dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
                        return dt
                    except ValueError:
                        # Try ISO format if different
                        try:
                            return datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        except:
                            pass
    return None


def get_latest_tweet_timestamp(tweet_ids: List[str], tweets_data: Optional[Dict] = None) -> Optional[datetime]:
    """
    Get the latest timestamp from a list of tweet IDs.
    
    Args:
        tweet_ids: List of tweet IDs
        tweets_data: Dictionary with tweets data (optional)
    
    Returns:
        Latest datetime or None if no timestamps found
    """
    timestamps = []
    for tweet_id in tweet_ids:
        ts = get_tweet_timestamp(tweet_id, tweets_data)
        if ts:
            timestamps.append(ts)
    
    if timestamps:
        return max(timestamps)
    return None


def format_relative_time(timestamp: datetime) -> str:
    """
    Format a datetime as relative time (e.g., "1h ago", "2d ago") or date if > 1 day.
    
    Args:
        timestamp: datetime object
    
    Returns:
        Formatted string like "1min ago", "1h ago", "12h ago", or "2025/12/01"
    """
    now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
    delta = now - timestamp
    
    total_seconds = int(delta.total_seconds())
    
    if total_seconds < 60:
        return f"{total_seconds}s ago" if total_seconds > 0 else "now"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        return f"{minutes}min ago"
    elif total_seconds < 86400:  # Less than 1 day
        hours = total_seconds // 3600
        return f"{hours}h ago"
    else:
        # More than 1 day - show date
        return timestamp.strftime("%Y/%m/%d")

