"""
Storage system for managing monitored accounts and session context.
Now uses database instead of state.json file.
"""
from typing import Dict, List, Optional
from datetime import datetime
from database import (
    get_all_accounts,
    add_account_to_db,
    update_account_username_in_db,
    remove_account_from_db,
    get_account_tracking,
    update_account_tracking,
    get_latest_summary_for_account,
    get_latest_summary
)

def get_monitored_accounts() -> List[Dict]:
    """Get list of monitored Twitter accounts with handle and username from database."""
    accounts = get_all_accounts()
    return [
        {
            "handle": acc["handle"],
            "username": acc["username"]
        }
        for acc in accounts
    ]


def get_monitored_account_handles() -> List[str]:
    """Get list of monitored Twitter handles from database."""
    accounts = get_all_accounts()
    return [acc["handle"] for acc in accounts]


def add_account(handle: str, username: Optional[str] = None) -> bool:
    """Add a Twitter handle to monitored accounts in database. Returns True if added, False if already exists."""
    return add_account_to_db(handle, username)


def update_account_username(handle: str, username: str) -> None:
    """Update the username for an existing account in database."""
    update_account_username_in_db(handle, username)


def remove_account(handle: str) -> bool:
    """Remove a Twitter handle from monitored accounts in database. Returns True if removed, False if not found."""
    return remove_account_from_db(handle)


def get_session_context(handle: str) -> Dict:
    """
    Get session context for a specific handle from database.
    Note: previous_summary is no longer stored - fetch from summaries table when needed.
    """
    handle = handle.strip().lstrip('@').lower()
    tracking = get_account_tracking(handle)
    
    if tracking:
        return {
            "last_tweet_id": tracking.get("last_tweet_id"),
            "last_fetch_timestamp_utc": tracking.get("last_fetch_timestamp_utc"),
            "last_summary_id": tracking.get("last_summary_id")
        }
    
    # Return default if no tracking found
    return {
        "last_tweet_id": None,
        "last_fetch_timestamp_utc": None,
        "last_summary_id": None
    }


def update_session_context(handle: str, previous_summary: str, last_tweet_id: Optional[str]) -> None:
    """
    Update session context for a specific handle in database.
    Note: previous_summary parameter is ignored - we don't store it anymore.
    Use update_account_tracking() directly if you need to update timestamp or summary_id.
    """
    handle = handle.strip().lstrip('@').lower()
    
    # Update tracking with last_tweet_id
    # Note: previous_summary is not stored - fetch from summaries table when needed
    update_account_tracking(handle, last_tweet_id=last_tweet_id)


def clear_all_contexts() -> None:
    """Clear all session contexts (reset last_tweet_id for all accounts in database)."""
    accounts = get_all_accounts()
    for account in accounts:
        update_account_tracking(account["handle"], last_tweet_id=None, 
                               last_fetch_timestamp_utc=None, last_summary_id=None)

