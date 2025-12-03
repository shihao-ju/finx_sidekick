"""
File-based storage system for managing monitored accounts and session context.
"""
import json
import os
from typing import Dict, List, Optional
from datetime import datetime

STATE_FILE = "state.json"


def load_state() -> Dict:
    """Load state from JSON file, creating default structure if file doesn't exist."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    # Default state structure
    return {
        "monitored_accounts": [],
        "session_context": {}
    }


def save_state(state: Dict) -> None:
    """Save state to JSON file."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_monitored_accounts() -> List[Dict]:
    """Get list of monitored Twitter accounts with handle and username."""
    state = load_state()
    accounts = []
    for handle in state.get("monitored_accounts", []):
        account_info = {
            "handle": handle,
            "username": state.get("account_info", {}).get(handle, {}).get("username")
        }
        accounts.append(account_info)
    return accounts


def get_monitored_account_handles() -> List[str]:
    """Get list of monitored Twitter handles (for backward compatibility)."""
    state = load_state()
    return state.get("monitored_accounts", [])


def add_account(handle: str, username: Optional[str] = None) -> bool:
    """Add a Twitter handle to monitored accounts. Returns True if added, False if already exists."""
    handle = handle.strip().lstrip('@').lower()
    state = load_state()
    
    if handle not in state["monitored_accounts"]:
        state["monitored_accounts"].append(handle)
        # Initialize session context for new account
        if handle not in state["session_context"]:
            state["session_context"][handle] = {
                "previous_summary": "",
                "last_tweet_id": None
            }
        # Store account info (username)
        if "account_info" not in state:
            state["account_info"] = {}
        if username:
            state["account_info"][handle] = {"username": username}
        save_state(state)
        return True
    return False


def update_account_username(handle: str, username: str) -> None:
    """Update the username for an existing account."""
    handle = handle.strip().lstrip('@').lower()
    state = load_state()
    if "account_info" not in state:
        state["account_info"] = {}
    if handle not in state["account_info"]:
        state["account_info"][handle] = {}
    state["account_info"][handle]["username"] = username
    save_state(state)


def remove_account(handle: str) -> bool:
    """Remove a Twitter handle from monitored accounts. Returns True if removed, False if not found."""
    handle = handle.strip().lstrip('@').lower()
    state = load_state()
    
    if handle in state["monitored_accounts"]:
        state["monitored_accounts"].remove(handle)
        # Optionally keep session context, or remove it
        # For now, we'll keep it in case user re-adds the account
        save_state(state)
        return True
    return False


def get_session_context(handle: str) -> Dict:
    """Get session context for a specific handle."""
    handle = handle.strip().lstrip('@').lower()
    state = load_state()
    return state["session_context"].get(handle, {
        "previous_summary": "",
        "last_tweet_id": None
    })


def update_session_context(handle: str, previous_summary: str, last_tweet_id: Optional[str]) -> None:
    """Update session context for a specific handle."""
    handle = handle.strip().lstrip('@').lower()
    state = load_state()
    
    if handle not in state["session_context"]:
        state["session_context"][handle] = {}
    
    state["session_context"][handle]["previous_summary"] = previous_summary
    state["session_context"][handle]["last_tweet_id"] = last_tweet_id
    
    save_state(state)


def clear_all_contexts() -> None:
    """Clear all session contexts (reset last_tweet_id and previous_summary for all accounts)."""
    state = load_state()
    for handle in state["session_context"]:
        state["session_context"][handle] = {
            "previous_summary": "",
            "last_tweet_id": None
        }
    save_state(state)

