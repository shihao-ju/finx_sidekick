"""
FastAPI backend for Financial Signal Aggregator.
"""
import os
import json
import sys
import asyncio
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import pytz
from fastapi import FastAPI, HTTPException, Response, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx
from openai import OpenAI
from typing import Optional

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from storage import (
    get_monitored_accounts,
    get_monitored_account_handles,
    add_account,
    update_account_username,
    remove_account,
    get_session_context,
    update_session_context
)
from database import (
    init_database,
    save_summary,
    get_latest_summary,
    get_summaries,
    get_summary_count,
    migrate_from_state_json,
    update_account_tracking,
    get_all_parsed_news_items,
    get_all_parsed_trades_items
)
from tweet_utils import (
    extract_tweet_ids_from_summary,
    get_tweet_timestamp,
    get_latest_tweet_timestamp,
    format_relative_time
)
from summary_parser import parse_news_items, parse_trades_items

# Load environment variables
# Explicitly load .env file from current directory
load_dotenv(dotenv_path=".env", override=True)

app = FastAPI(title="Financial Signal Aggregator API")

# Authentication
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "dev-admin-token-change-in-production")

def verify_admin_token_query(token: Optional[str] = Query(None)):
    """Verify admin token from query parameter."""
    if not token or token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing admin token")
    return token

def verify_token(token: str):
    """Verify token value."""
    if not token or token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing admin token")
    return token

def verify_admin_token_header(x_admin_token: Optional[str] = Header(None)):
    """Verify admin token from X-Admin-Token header (for main page API calls)."""
    if not x_admin_token or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing admin token")
    return x_admin_token

def verify_auth_token(x_admin_token: Optional[str] = Header(None)):
    """Verify auth token from X-Admin-Token header (same token for both admin and regular auth)."""
    if not x_admin_token or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Authentication required")
    return x_admin_token

# Dependencies
require_admin_query = Depends(verify_admin_token_query)
require_admin_header = Depends(verify_admin_token_header)
require_auth = Depends(verify_auth_token)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database, run migration, and start scheduler."""
    init_database()
    
    # Run migration from state.json to database (one-time, idempotent)
    try:
        migration_report = migrate_from_state_json()
        if migration_report["accounts_migrated"] > 0 or migration_report["tracking_migrated"] > 0:
            print(f"[INFO] Migration completed: {migration_report['accounts_migrated']} accounts, "
                  f"{migration_report['tracking_migrated']} tracking records migrated", flush=True)
        if migration_report["errors"]:
            print(f"[WARNING] Migration errors: {migration_report['errors']}", flush=True)
    except Exception as e:
        print(f"[WARNING] Migration failed (non-critical): {e}", flush=True)
    
    # Start scheduler (must be done after event loop is running)
    # AsyncIOScheduler requires a running event loop
    # Since we're in an async startup event, the loop is already running
    try:
        from scheduler import get_scheduler_manager
        scheduler_manager = get_scheduler_manager()
        # Start scheduler - it will check for running event loop internally
        scheduler_manager.start()
        print("[INFO] Scheduler startup initiated", flush=True)
    except Exception as e:
        print(f"[ERROR] Failed to start scheduler: {e}", flush=True)
        import traceback
        traceback.print_exc()


@app.on_event("shutdown")
async def shutdown_event():
    """Stop scheduler on shutdown."""
    try:
        from scheduler import get_scheduler_manager
        scheduler_manager = get_scheduler_manager()
        scheduler_manager.stop()
    except Exception as e:
        print(f"[ERROR] Error stopping scheduler: {e}", flush=True)
        print(f"[WARNING] Migration failed (non-critical): {e}", flush=True)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load AI Builder API key with retry logic
# Check SECOND_MIND_API_KEY first (for backward compatibility), then AI_BUILDER_TOKEN (for deployment)
SECOND_MIND_API_KEY = os.getenv("SECOND_MIND_API_KEY") or os.getenv("AI_BUILDER_TOKEN")
if not SECOND_MIND_API_KEY:
    # Retry loading .env file
    load_dotenv(dotenv_path=".env", override=True)
    SECOND_MIND_API_KEY = os.getenv("SECOND_MIND_API_KEY") or os.getenv("AI_BUILDER_TOKEN")

# Initialize OpenAI client for AI Builder API
if not SECOND_MIND_API_KEY:
    print("[ERROR] SECOND_MIND_API_KEY not found in environment variables!")
    print(f"Current working directory: {os.getcwd()}")
    print(f".env file exists: {os.path.exists('.env')}")
    openai_client = None
else:
    openai_client = OpenAI(
        api_key=SECOND_MIND_API_KEY,
        base_url="https://space.ai-builders.com/backend/v1",
        timeout=120.0  # 2 minute timeout for AI API calls
    )
    print(f"[OK] AI Builder API key loaded: {SECOND_MIND_API_KEY[:15]}...")

# Load Twitter API key with retry logic
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
if not TWITTER_API_KEY:
    # Retry loading .env file
    load_dotenv(dotenv_path=".env", override=True)
    TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")

TWITTER_API_BASE = "https://api.twitterapi.io"

# Verify API key is loaded at startup
if TWITTER_API_KEY:
    print(f"[OK] Twitter API key loaded: {TWITTER_API_KEY[:15]}...")
else:
    print("[ERROR] Twitter API key NOT loaded!")
    print(f"Current working directory: {os.getcwd()}")
    print(f".env file exists: {os.path.exists('.env')}")
    if os.path.exists('.env'):
        with open('.env', 'r', encoding='utf-8') as f:
            content = f.read()
            print(f".env file content preview: {content[:100]}")


# Request/Response models
class AccountRequest(BaseModel):
    handle: str


class AccountInfo(BaseModel):
    handle: str
    username: Optional[str] = None


class AccountResponse(BaseModel):
    accounts: List[AccountInfo]


class RefreshResponse(BaseModel):
    summary: str


class SummaryItem(BaseModel):
    id: int
    timestamp: str
    summary: str
    tweet_ids: List[str]
    created_at: str


class SummariesResponse(BaseModel):
    summaries: List[SummaryItem]
    total: int
    limit: int
    offset: int


class NewsTradeItem(BaseModel):
    title: str
    content: str
    source_tags: List[Dict]
    timestamp: str
    tweet_ids: List[str]
    is_liked: Optional[bool] = None  # Added for batch liked status
    thought: Optional[str] = None  # Added for batch thoughts
    
    def model_dump(self, *, exclude_none: bool = False, **kwargs):
        # Override to ensure None values are included in JSON output
        # This allows frontend to detect batch data by checking if fields exist
        return super().model_dump(exclude_none=False, **kwargs)


class MergedItemsResponse(BaseModel):
    news: List[NewsTradeItem]
    trades: List[NewsTradeItem]
    total_news: int
    total_trades: int


class ChatRequest(BaseModel):
    question: str
    summary: str


class ChatResponse(BaseModel):
    answer: str


class NewsLikeRequest(BaseModel):
    news_hash: str
    title: str
    content: str
    timestamp: str
    source_tags: List[Dict]
    tweet_ids: List[str]


class NewsThoughtRequest(BaseModel):
    news_hash: str
    thought: str
    title: Optional[str] = None
    content: Optional[str] = None
    timestamp: Optional[str] = None
    source_tags: Optional[List[Dict]] = None
    tweet_ids: Optional[List[str]] = None


class NewsLikeItem(BaseModel):
    id: int
    news_hash: str
    title: str
    content: str
    timestamp: str
    liked_at: str
    source_tags: List[Dict]
    tweet_ids: List[str]


class NewsLikesResponse(BaseModel):
    likes: List[NewsLikeItem]
    total: int


class NewsThoughtResponse(BaseModel):
    thought: Optional[str] = None


class LikedStatusResponse(BaseModel):
    liked_hashes: List[str]


class NewsThoughtItem(BaseModel):
    id: int
    news_hash: str
    thought: str
    created_at: str
    updated_at: str
    title: str
    content: str
    timestamp: str
    source_tags: List[Dict]
    tweet_ids: List[str]


class NewsThoughtsResponse(BaseModel):
    thoughts: List[NewsThoughtItem]
    total: int


def fetch_user_info(handle: str) -> Optional[Dict]:
    """
    Fetch user profile information from twitterapi.io API.
    Returns user info dict with 'name' (username) field, or None if not found.
    """
    if not TWITTER_API_KEY:
        return None
    
    # Try to get user info by fetching a single tweet and extracting author info
    # This is a workaround since we don't have a direct user profile endpoint
    url = f"{TWITTER_API_BASE}/twitter/user/last_tweets"
    headers = {
        "x-api-key": TWITTER_API_KEY
    }
    
    params = {
        "userName": handle.lstrip('@'),
        "includeReplies": False
    }
    
    try:
        with httpx.Client() as client:
            response = client.get(url, headers=headers, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            # Extract user info from the first tweet's author
            response_data = data.get("data", {})
            tweets = response_data.get("tweets", [])
            
            if tweets and len(tweets) > 0:
                first_tweet = tweets[0]
                author = first_tweet.get("author", {})
                if author:
                    return {
                        "handle": handle.lower(),
                        "username": author.get("name", None)
                    }
    except Exception as e:
        print(f"Error fetching user info for {handle}: {e}", file=sys.stderr, flush=True)
    
    return None


def fetch_tweets_advanced_search(handle: str, since_timestamp_utc: Optional[str] = None) -> List[Dict]:
    """
    Fetch tweets using Advanced Search API with timestamp-based queries.
    This is more efficient for sparse accounts as it only fetches tweets in the time window.
    
    Args:
        handle: Twitter handle (without @)
        since_timestamp_utc: ISO format UTC timestamp (e.g., "2025-12-02T14:00:00Z")
    
    Returns:
        List of tweet dictionaries
    """
    import sys
    print(f"[DEBUG] fetch_tweets_advanced_search called for handle: {handle}, since_timestamp: {since_timestamp_utc}", file=sys.stderr, flush=True)
    
    if not TWITTER_API_KEY:
        raise HTTPException(status_code=500, detail="Twitter API key not configured")
    
    # Format timestamps for Advanced Search API
    # Format: YYYY-MM-DD_HH:MM:SS_UTC
    if since_timestamp_utc:
        # Parse ISO format and convert to Advanced Search format
        try:
            dt = datetime.fromisoformat(since_timestamp_utc.replace('Z', '+00:00'))
            since_str = dt.strftime("%Y-%m-%d_%H:%M:%S_UTC")
        except Exception as e:
            print(f"[ERROR] Failed to parse since_timestamp: {e}", file=sys.stderr, flush=True)
            return []
    else:
        # Default: last hour
        dt = datetime.now(pytz.UTC) - timedelta(hours=1)
        since_str = dt.strftime("%Y-%m-%d_%H:%M:%S_UTC")
    
    # Current time (use API server time, not local clock)
    until_dt = datetime.now(pytz.UTC)
    until_str = until_dt.strftime("%Y-%m-%d_%H:%M:%S_UTC")
    
    # Construct query: from:handle since:timestamp until:timestamp include:nativeretweets include:replies
    # Include replies to catch all tweets from the account
    query = f"from:{handle.lstrip('@')} since:{since_str} until:{until_str} include:nativeretweets include:replies"
    
    print(f"[DEBUG] Advanced Search query: {query}", file=sys.stderr, flush=True)
    print(f"[DEBUG] Time window: {since_str} to {until_str} ({(until_dt - dt).total_seconds():.1f} seconds)", file=sys.stderr, flush=True)
    
    # API endpoint for Advanced Search
    url = f"{TWITTER_API_BASE}/twitter/tweet/advanced_search"
    headers = {
        "X-API-Key": TWITTER_API_KEY  # Note: Advanced Search uses X-API-Key, not x-api-key
    }
    
    params = {
        "query": query,
        "queryType": "Latest"
    }
    
    all_tweets = []
    next_cursor = None
    
    try:
        with httpx.Client() as client:
            while True:
                if next_cursor:
                    params["cursor"] = next_cursor
                else:
                    params.pop("cursor", None)
                
                response = client.get(url, headers=headers, params=params, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                
                # Check response status
                if data.get("status") == "error":
                    error_msg = data.get("msg", data.get("message", "Unknown error"))
                    print(f"[ERROR] Advanced Search API error for {handle}: {error_msg}", file=sys.stderr, flush=True)
                    break
                
                # Extract tweets
                tweets = data.get("tweets", [])
                if tweets:
                    all_tweets.extend(tweets)
                    print(f"[DEBUG] Advanced Search fetched {len(tweets)} tweets for {handle} (total: {len(all_tweets)})", file=sys.stderr, flush=True)
                
                # Check pagination
                if not data.get("has_next_page", False) or not data.get("next_cursor", ""):
                    break
                
                next_cursor = data.get("next_cursor", "")
                
    except Exception as e:
        print(f"[ERROR] Advanced Search API error for {handle}: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return []
    
    print(f"[DEBUG] Advanced Search returned {len(all_tweets)} total tweets for {handle}", file=sys.stderr, flush=True)
    return all_tweets


def fetch_tweets_hybrid(handle: str, since_id: Optional[str] = None, 
                       last_fetch_timestamp_utc: Optional[str] = None) -> List[Dict]:
    """
    Hybrid fetch: Uses timestamp-based Advanced Search as primary method,
    falls back to since_id-based fetch if Advanced Search fails.
    
    Args:
        handle: Twitter handle
        since_id: Tweet ID for fallback method
        last_fetch_timestamp_utc: UTC timestamp for primary method
    
    Returns:
        List of tweet dictionaries
    """
    import sys
    
    # Primary: Try Advanced Search with timestamp
    tweets = []
    if last_fetch_timestamp_utc:
        try:
            print(f"[DEBUG] Attempting Advanced Search (primary) for {handle} since {last_fetch_timestamp_utc}", file=sys.stderr, flush=True)
            tweets = fetch_tweets_advanced_search(handle, last_fetch_timestamp_utc)
            
            if tweets:
                print(f"[DEBUG] Advanced Search succeeded: {len(tweets)} tweets", file=sys.stderr, flush=True)
                return tweets
            else:
                # Advanced Search returned 0 tweets - might be because:
                # 1. No new tweets after the timestamp (correct)
                # 2. Advanced Search doesn't include replies/retweets properly
                # Try fallback to regular fetch if we have since_id
                print(f"[DEBUG] Advanced Search returned 0 tweets - no new tweets after {last_fetch_timestamp_utc}", file=sys.stderr, flush=True)
                if since_id:
                    print(f"[DEBUG] Trying fallback fetch with since_id: {since_id} (Advanced Search might miss replies/retweets)", file=sys.stderr, flush=True)
                    try:
                        fallback_tweets = fetch_tweets(handle, since_id)
                        if fallback_tweets:
                            print(f"[DEBUG] Fallback fetch found {len(fallback_tweets)} tweets that Advanced Search missed", file=sys.stderr, flush=True)
                            return fallback_tweets
                    except Exception as e:
                        print(f"[DEBUG] Fallback fetch also returned 0 tweets: {e}", file=sys.stderr, flush=True)
                return []
        except Exception as e:
            # Only fall back if Advanced Search throws an error (not if it returns 0 results)
            print(f"[WARNING] Advanced Search failed for {handle}: {e}, trying fallback", file=sys.stderr, flush=True)
    
    # Fallback: Use since_id method (only if Advanced Search failed with an error, or no timestamp provided)
    if since_id:
        try:
            print(f"[DEBUG] Using since_id fallback for {handle} with since_id: {since_id}", file=sys.stderr, flush=True)
            tweets = fetch_tweets(handle, since_id)
            print(f"[DEBUG] Fallback succeeded: {len(tweets)} tweets", file=sys.stderr, flush=True)
            return tweets
        except Exception as e:
            print(f"[ERROR] Fallback also failed for {handle}: {e}", file=sys.stderr, flush=True)
            return []
    else:
        # No since_id, try Advanced Search with default (last hour)
        try:
            print(f"[DEBUG] No since_id, trying Advanced Search with default time window", file=sys.stderr, flush=True)
            tweets = fetch_tweets_advanced_search(handle, None)
            return tweets
        except Exception as e:
            print(f"[ERROR] Advanced Search with default failed: {e}", file=sys.stderr, flush=True)
            # Last resort: fetch all tweets
            return fetch_tweets(handle, None)


def fetch_tweets(handle: str, since_id: Optional[str] = None) -> List[Dict]:
    """
    Fetch tweets from twitterapi.io API using the /twitter/user/last_tweets endpoint.
    Returns list of tweet dictionaries.
    Documentation: https://docs.twitterapi.io/api-reference/endpoint/
    """
    import sys
    print(f"[DEBUG] fetch_tweets called for handle: {handle}, since_id: {since_id}", file=sys.stderr, flush=True)
    
    if not TWITTER_API_KEY:
        raise HTTPException(status_code=500, detail="Twitter API key not configured")
    
    # Using twitterapi.io endpoint: GET /twitter/user/last_tweets
    # Documentation: https://docs.twitterapi.io/api-reference/endpoint/
    # Authentication: https://docs.twitterapi.io/authentication
    url = f"{TWITTER_API_BASE}/twitter/user/last_tweets"
    headers = {
        "x-api-key": TWITTER_API_KEY
    }
    
    params = {
        "userName": handle.lstrip('@'),
        "includeReplies": False  # Focus on main tweets, not replies
    }
    
    all_tweets = []
    cursor = ""  # Start with empty cursor for first page
    max_pages = 5 if since_id is None else 10  # Limit pages on first run
    
    # Store raw API response for saving
    raw_api_responses = []
    
    try:
        with httpx.Client() as client:
            page_count = 0
            # Fetch pages until we find tweets older than since_id or run out of pages
            while page_count < max_pages:
                page_count += 1
                if cursor:
                    params["cursor"] = cursor
                else:
                    params.pop("cursor", None)  # Remove cursor param for first page
                
                response = client.get(url, headers=headers, params=params, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                
                # Store raw response for saving
                raw_api_responses.append(data)
                
                # Debug: Print full response structure
                import sys
                print(f"[DEBUG] API response for {handle}:", file=sys.stderr, flush=True)
                print(f"[DEBUG]   Status: {data.get('status')}", file=sys.stderr, flush=True)
                print(f"[DEBUG]   Keys in response: {list(data.keys())}", file=sys.stderr, flush=True)
                
                # The API returns tweets nested in data.data.tweets, not data.tweets
                response_data = data.get("data", {})
                print(f"[DEBUG]   data key exists: {'data' in data}", file=sys.stderr, flush=True)
                print(f"[DEBUG]   data keys: {list(response_data.keys()) if response_data else 'N/A'}", file=sys.stderr, flush=True)
                
                # Check response status
                if data.get("status") == "error":
                    error_msg = data.get("msg", data.get("message", "Unknown error"))
                    print(f"[ERROR] API error for {handle}: {error_msg}", file=sys.stderr, flush=True)
                    break
                
                # Extract tweets from nested data structure: data.data.tweets
                tweets = response_data.get("tweets", [])
                print(f"[DEBUG]   tweets_count: {len(tweets)}", file=sys.stderr, flush=True)
                if tweets:
                    print(f"[DEBUG]   First tweet keys: {list(tweets[0].keys())}", file=sys.stderr, flush=True)
                
                if not tweets:
                    print(f"[DEBUG] No tweets returned for {handle} on page {page_count}", file=sys.stderr, flush=True)
                    print(f"[DEBUG] Response message: {data.get('msg', 'N/A')}", file=sys.stderr, flush=True)
                    # Check if there are more pages (also nested in data.data)
                    if not response_data.get("has_next_page", False):
                        print(f"[DEBUG] No more pages available", file=sys.stderr, flush=True)
                    break
                
                # Get pagination cursor from nested data
                cursor = response_data.get("next_cursor", "")
                
                print(f"Fetched {len(tweets)} tweets for {handle} (page {page_count})")
                
                # Filter tweets: if since_id is provided, only include tweets newer than it
                # Tweets are sorted by created_at (newest first)
                # Twitter IDs are snowflake IDs - higher ID = newer tweet
                # On first fetch (since_id is None), include all tweets
                if since_id:
                    filtered_tweets = []
                    found_since_id = False
                    since_id_str = str(since_id)
                    since_id_int = int(since_id_str)  # Convert to int for numerical comparison
                    
                    print(f"[DEBUG] Filtering tweets with since_id: {since_id_str}", file=sys.stderr, flush=True)
                    
                    for tweet in tweets:
                        tweet_id_str = str(tweet.get("id_str") or tweet.get("id"))
                        tweet_id_int = int(tweet_id_str)  # Convert to int for numerical comparison
                        
                        # If this tweet matches since_id, skip it (already processed)
                        if tweet_id_int == since_id_int:
                            found_since_id = True
                            print(f"[DEBUG] Skipping tweet {tweet_id_str} (matches since_id - already processed)", file=sys.stderr, flush=True)
                            # Continue to next tweet instead of breaking
                            # This handles cases where API might return the same tweet
                            continue
                        
                        # Only include tweets that are NEWER than since_id (higher ID)
                        if tweet_id_int > since_id_int:
                            filtered_tweets.append(tweet)
                            print(f"[DEBUG] Including tweet {tweet_id_str} (NEWER: {tweet_id_int} > {since_id_int})", file=sys.stderr, flush=True)
                        else:
                            # Since tweets are sorted newest first, once we hit an older tweet,
                            # all remaining tweets in this page will also be older
                            print(f"[DEBUG] Skipping tweet {tweet_id_str} (OLDER: {tweet_id_int} < {since_id_int}) - stopping page processing", file=sys.stderr, flush=True)
                            # Don't break here - continue to check if since_id appears later
                            # (in case of duplicates or out-of-order tweets)
                    
                    if filtered_tweets:
                        print(f"[DEBUG] Adding {len(filtered_tweets)} new tweets (filtered from {len(tweets)} total)", file=sys.stderr, flush=True)
                        all_tweets.extend(filtered_tweets)
                    else:
                        print(f"[DEBUG] No new tweets found (all tweets already processed or older than since_id)", file=sys.stderr, flush=True)
                    
                    # If we found the since_id AND have no new tweets, we don't need to fetch more pages
                    # (all remaining pages would be older tweets)
                    if found_since_id and not filtered_tweets:
                        print(f"[DEBUG] Found since_id and no new tweets, no need to fetch more pages", file=sys.stderr, flush=True)
                        break
                else:
                    # First time fetching - include all tweets
                    print(f"[DEBUG] First fetch (no since_id), including all {len(tweets)} tweets", file=sys.stderr, flush=True)
                    all_tweets.extend(tweets)
                
                # Check if there are more pages (from nested data.data)
                if not response_data.get("has_next_page", False):
                    print(f"[DEBUG] No more pages for {handle}", file=sys.stderr, flush=True)
                    break
                
                # Cursor is already set above from response_data
                if not cursor:
                    print(f"[DEBUG] No cursor for next page for {handle}", file=sys.stderr, flush=True)
                    break
        
        # ALWAYS save raw API response data BEFORE filtering, so we capture everything
        test_data_file = "test_tweets_data.json"
        try:
            # Collect all raw tweets from API (before filtering)
            raw_tweets_before_filter = []
            for resp in raw_api_responses:
                raw_tweets_before_filter.extend(resp.get("data", {}).get("tweets", []))
            
            with open(test_data_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "handle": handle,
                    "fetch_timestamp": datetime.now().isoformat(),
                    "since_id": since_id,
                    "raw_tweets_count": len(raw_tweets_before_filter),
                    "processed_tweets_count": len(all_tweets),
                    "raw_tweets": raw_tweets_before_filter,
                    "processed_tweets": all_tweets,
                    "raw_api_responses": raw_api_responses
                }, f, indent=2, ensure_ascii=False)
            print(f"[DEBUG] Saved raw API data: {len(raw_tweets_before_filter)} raw tweets, {len(all_tweets)} processed tweets to {test_data_file}", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[ERROR] Failed to save test data: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
        
        return all_tweets
    except httpx.HTTPError as e:
        print(f"HTTP error fetching tweets for {handle}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"Error response: {error_data}")
            except:
                print(f"Error response text: {e.response.text}")
        return []
    except Exception as e:
        print(f"Unexpected error fetching tweets for {handle}: {e}")
        return []


def extract_tickers(text: str) -> List[str]:
    """Extract ticker symbols (format: $SYMBOL) from text.
    Filters out placeholder tickers like $1, $2, $SYMBOL.
    """
    import re
    if not text:
        return []
    # Match $ followed by 1-5 uppercase letters, word boundary ensures we don't match partial words
    tickers = re.findall(r'\$[A-Z]{1,5}\b', text)
    
    # Filter out placeholder tickers
    placeholders = {'$1', '$2', '$3', '$4', '$5', '$SYMBOL', '$SYMBO'}  # $SYMBO is partial match of $SYMBOL
    real_tickers = [t for t in tickers if t not in placeholders]
    
    return list(set(real_tickers))  # Return unique tickers


def _call_llm_sync(prompt: str, section_name: str) -> str:
    """
    Helper function to call LLM API (synchronous).
    """
    import sys
    if not openai_client:
        raise HTTPException(status_code=500, detail="AI Builder API key not configured")
    
    model_name = "grok-4-fast"
    print(f"[DEBUG] Calling LLM for {section_name} using model: {model_name}", file=sys.stderr, flush=True)
    
    try:
        request_params = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "You are a financial analyst specializing in extracting actionable insights from social media posts."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000  # Reduced since we're splitting into two calls
        }
        print(f"[DEBUG] {section_name} prompt length: {len(prompt)} characters ({len(prompt)/1000:.1f}K)", file=sys.stderr, flush=True)
        
        response = openai_client.chat.completions.create(**request_params)
        
        if response.choices:
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            if content is None:
                raise Exception(f"{section_name} API returned empty content (None)")
            result = content.strip() if content else ""
            print(f"[DEBUG] {section_name} summary length: {len(result)} characters", file=sys.stderr, flush=True)
            
            if not result:
                if finish_reason == "length":
                    raise Exception(f"{section_name} API response was truncated (hit max_tokens limit)")
            return result
        else:
            raise Exception(f"No choices returned from {section_name} API")
    except Exception as e:
        import sys
        print(f"[ERROR] Error generating {section_name} summary: {e}", file=sys.stderr, flush=True)
        raise


async def generate_summary(previous_summary: str, new_tweets: List[Dict], account_handles: List[str], account_tweet_map: Optional[Dict[str, List[Dict]]] = None) -> str:
    """
    Generate financial summary using AI Builder API.
    Splits into two parallel calls: one for News, one for Trades.
    
    Args:
        previous_summary: Previous summary text for context
        new_tweets: List of all new tweets (flat list)
        account_handles: List of monitored account handles
        account_tweet_map: Optional dict mapping account handle -> list of tweets fetched from that account
    """
    import sys
    print(f"[DEBUG] generate_summary called with {len(new_tweets)} tweets", file=sys.stderr, flush=True)
    
    # Group tweets by monitored account handle (not by tweet author)
    # This ensures retweets/replies are associated with the account they were fetched from
    tweets_by_account = {}
    if account_tweet_map:
        # Use the account_tweet_map if provided (more accurate)
        for handle in account_handles:
            handle_lower = handle.lower()
            tweets_from_account = account_tweet_map.get(handle_lower, [])
            if tweets_from_account:
                tweets_by_account[handle_lower] = tweets_from_account
    else:
        # Fallback: group by tweet author (less accurate for retweets/replies)
        for tweet in new_tweets:
            # Extract account handle from tweet author
            username = "unknown"
            if "author" in tweet and isinstance(tweet["author"], dict):
                username = tweet["author"].get("userName") or tweet["author"].get("screen_name") or tweet["author"].get("username", "unknown")
            elif "user" in tweet and isinstance(tweet["user"], dict):
                username = tweet["user"].get("screen_name") or tweet["user"].get("userName") or tweet["user"].get("username", "unknown")
            elif "screen_name" in tweet:
                username = tweet["screen_name"]
            elif "userName" in tweet:
                username = tweet["userName"]
            
            username_lower = username.lower()
            if username_lower not in tweets_by_account:
                tweets_by_account[username_lower] = []
            tweets_by_account[username_lower].append(tweet)
    
    print(f"[DEBUG] Tweets grouped by account: {[(k, len(v)) for k, v in tweets_by_account.items()]}", file=sys.stderr, flush=True)
    # Filter replies and count main tweets
    main_tweets_count = len([t for t in new_tweets if not t.get("isReply", False)]) if new_tweets else 0
    print(f"[DEBUG] Main tweets (non-replies): {main_tweets_count} out of {len(new_tweets)}", file=sys.stderr, flush=True)
    print(f"[DEBUG] openai_client exists: {openai_client is not None}", file=sys.stderr, flush=True)
    
    if not new_tweets and not previous_summary:
        return "No tweets found and no previous summary available. This could mean:\n- The monitored accounts haven't posted any tweets recently\n- This is the first time checking these accounts (no previous summary)\n- The accounts may be private or have no public tweets"
    
    # Prioritize and format tweets for prompt
    tweets_text = ""
    if new_tweets:
        # First, prioritize tweets from each account separately to ensure representation
        account_prioritized_tweets = {}
        for account_handle in account_handles:
            account_tweets = tweets_by_account.get(account_handle.lower(), [])
            if not account_tweets:
                continue
            
            # Categorize tweets by type and engagement for this account
            original_tweets = []
            retweets = []
            quote_tweets = []
            high_engagement_replies = []
            
            for tweet in account_tweets:
                is_reply = tweet.get("isReply", False)
                has_retweet = tweet.get("retweeted_tweet") is not None
                has_quote = tweet.get("quoted_tweet") is not None
                
                likes = tweet.get("likeCount", 0)
                retweet_count = tweet.get("retweetCount", 0)
                
                if is_reply:
                    # Only include replies with high engagement
                    if likes > 50 or retweet_count > 10:
                        high_engagement_replies.append(tweet)
                elif has_retweet:
                    retweets.append(tweet)
                elif has_quote:
                    quote_tweets.append(tweet)
                else:
                    original_tweets.append(tweet)
            
            # Prioritize for this account: original > retweets > quote tweets > high-engagement replies
            account_prioritized = original_tweets + retweets + quote_tweets + high_engagement_replies
            # Take top 8 tweets per account to ensure representation
            account_prioritized_tweets[account_handle.lower()] = account_prioritized[:8]
        
        # Combine all prioritized tweets from all accounts, ensuring representation
        # Strategy: Take at least 2 tweets from each account first, then fill remaining slots
        prioritized_tweets = []
        MAX_TWEETS_TOTAL = 35  # Increased from 25 to 35 for better coverage
        tweets_per_account = max(2, MAX_TWEETS_TOTAL // max(len(account_handles), 1))  # At least 2 per account, distribute evenly
        
        # First pass: ensure at least tweets_per_account from each account
        for account_handle in account_handles:
            account_tweets = account_prioritized_tweets.get(account_handle.lower(), [])
            prioritized_tweets.extend(account_tweets[:tweets_per_account])
        
        # Second pass: add remaining tweets from all accounts up to limit of MAX_TWEETS_TOTAL
        remaining_slots = MAX_TWEETS_TOTAL - len(prioritized_tweets)
        if remaining_slots > 0:
            remaining_tweets = []
            for account_handle in account_handles:
                account_tweets = account_prioritized_tweets.get(account_handle.lower(), [])
                # Add tweets beyond the ones we already took
                remaining_tweets.extend(account_tweets[tweets_per_account:])
            # Sort by engagement (likes + retweets) and take top remaining slots
            remaining_tweets.sort(key=lambda t: (t.get("likeCount", 0) + t.get("retweetCount", 0)), reverse=True)
            prioritized_tweets.extend(remaining_tweets[:remaining_slots])
        
        # Final limit to MAX_TWEETS_TOTAL tweets total
        prioritized_tweets = prioritized_tweets[:MAX_TWEETS_TOTAL]
        
        print(f"[DEBUG] Prioritized {len(prioritized_tweets)} tweets from {len(account_handles)} accounts (max: {MAX_TWEETS_TOTAL})", file=sys.stderr, flush=True)
        
        formatted_tweets = []
        for tweet in prioritized_tweets:
            # Extract username
            username = "unknown"
            if "author" in tweet and isinstance(tweet["author"], dict):
                username = tweet["author"].get("userName") or tweet["author"].get("screen_name") or tweet["author"].get("username", "unknown")
            elif "user" in tweet and isinstance(tweet["user"], dict):
                username = tweet["user"].get("screen_name") or tweet["user"].get("userName") or tweet["user"].get("username", "unknown")
            elif "screen_name" in tweet:
                username = tweet["screen_name"]
            elif "userName" in tweet:
                username = tweet["userName"]
            
            # Determine tweet type
            is_reply = tweet.get("isReply", False)
            has_retweet = tweet.get("retweeted_tweet") is not None
            has_quote = tweet.get("quoted_tweet") is not None
            
            # Get engagement metrics
            likes = tweet.get("likeCount", 0)
            retweet_count = tweet.get("retweetCount", 0)
            
            # Extract tweet text
            tweet_text = tweet.get("text") or tweet.get("full_text") or tweet.get("content") or tweet.get("tweet", "")
            
            # Extract tweet URL
            tweet_url = tweet.get("url") or tweet.get("twitterUrl") or ""
            
            # Handle retweets - extract full original content
            if has_retweet:
                retweeted_tweet = tweet.get("retweeted_tweet", {})
                original_text = retweeted_tweet.get("text", "")
                original_author = retweeted_tweet.get("author", {})
                original_username = original_author.get("userName") or original_author.get("screen_name", "unknown")
                
                if original_text:
                    formatted_tweets.append(f"[RETWEET] @{username} retweeted @{original_username}: {original_text} (Likes: {likes}, RTs: {retweet_count}) [TWEET_URL:{tweet_url}]")
                else:
                    # Fallback to RT prefix text if original not available
                    formatted_tweets.append(f"[RETWEET] @{username}: {tweet_text} (Likes: {likes}, RTs: {retweet_count}) [TWEET_URL:{tweet_url}]")
            elif has_quote:
                quoted_tweet = tweet.get("quoted_tweet", {})
                quoted_text = quoted_tweet.get("text", "")
                quoted_author = quoted_tweet.get("author", {})
                quoted_username = quoted_author.get("userName") or quoted_author.get("screen_name", "unknown")
                
                if quoted_text:
                    formatted_tweets.append(f"[QUOTE] @{username}: {tweet_text} | Quoted @{quoted_username}: {quoted_text[:200]}... (Likes: {likes}, RTs: {retweet_count}) [TWEET_URL:{tweet_url}]")
                else:
                    formatted_tweets.append(f"[QUOTE] @{username}: {tweet_text} (Likes: {likes}, RTs: {retweet_count}) [TWEET_URL:{tweet_url}]")
            elif is_reply:
                in_reply_to = tweet.get("inReplyToUsername", "unknown")
                formatted_tweets.append(f"[REPLY] @{username} replying to @{in_reply_to}: {tweet_text} (Likes: {likes}, RTs: {retweet_count}) [TWEET_URL:{tweet_url}]")
            else:
                formatted_tweets.append(f"[ORIGINAL] @{username}: {tweet_text} (Likes: {likes}, RTs: {retweet_count}) [TWEET_URL:{tweet_url}]")
        
        tweets_text = "\n\n".join(formatted_tweets)
    
    # Common prompt components
    common_context = f"""You are a financial analyst creating actionable market intelligence summaries from social media posts.

Monitored Accounts: {', '.join([f'@{h}' for h in account_handles])}

New Tweets (each tweet includes [TWEET_URL:url] at the end - use this URL for source tags):
{tweets_text if tweets_text else "No new tweets."}

For RETWEETS: Extract the key insight from the original tweet. Focus on:
- The main argument or thesis
- Actionable takeaways (buy/sell signals, price targets, reasoning)
- Key facts and data points

For TICKERS ($SYMBOL): When a ticker is mentioned in tweets:
- CRITICAL: ALWAYS use the EXACT ticker symbol as it appears in the tweets (e.g., $NVDA, $LITE, $COHR, $GOOG)
- ABSOLUTELY FORBIDDEN: Do NOT use placeholders like $1, $2, $SYMBOL, or any generic references
- Extract ticker symbols directly from the tweet text above - use them exactly as written

CRITICAL INSTRUCTIONS:
1. Do NOT mention "no new updates", "no new tweets", "prior insights remain unchanged", "opinion holds", "sentiment holds", or any similar phrases indicating lack of updates.
2. Extract ticker symbols directly from the tweets - use them exactly as they appear (e.g., $NVDA, $TSLA). Do NOT use placeholders.
3. Only include information from the new tweets provided. If there are no new insights, omit the section entirely rather than saying "no updates".
"""

    # Create separate prompts for News and Trades
    news_prompt = f"""{common_context}

Your task: Generate ONLY the News section from the tweets above.

Focus on:
- Market insights and analysis (NOT specific trade actions)
- Key market events or catalysts
- Price targets or valuation insights
- Risk factors or concerns
- Market sentiment and trends
- CRITICAL: When multiple tweets discuss the same ticker, company, or related theme, COMBINE them into a single news item. Do not create separate news items for related topics. Synthesize the information into one comprehensive insight.
- CRITICAL: Headline format - Use concise news-style headlines (8-12 words, 60-80 characters). Headlines should be SHORT and PUNCHY like real news headlines. Include WHAT (ticker/company) + WHAT HAPPENED (key news). Save detailed facts, numbers, price targets, percentages, and reasoning for the content section AFTER the colon.

Format your response as:

## News
- CRITICAL: Combine related insights about the same topic, ticker, or theme into a SINGLE news item.
- Each insight must start with a clear, concise headline written like a news headline (8-12 words).
- BAD examples (too vague): "Market Wisdom", "2026 Global Allocation", "Google AI Ascendancy"
- BAD examples (too long): "**$TSLA** remains undervalued as Burry's critique misses AI-energy paradigm shift - maintain long-term holds"
- GOOD examples: "**$TSLA** undervalued as AI shifts to energy paradigm", "**$CRDO** revenue jumps 40% YoY, targets $75", "**$GOOG** leads AI race with TPU economics"
- Format: **Headline (8-12 words)**: Detailed explanation with specific facts, numbers, price targets, percentages, reasoning, and context
- Use bold (**text**) for tickers in headlines and content
- IMPORTANT: At the end of each insight, add source tags: [Source: @handle](tweet_url) for ALL tweets that contributed
- Use tweet URLs from [TWEET_URL:url] at the end of each tweet above
- If multiple tweets contribute, list all sources: [Source: @handle1](url1) [Source: @handle2](url2)

If there are no news insights in the tweets, respond with only: "## News" (no content)."""

    trades_prompt = f"""{common_context}

Your task: Generate ONLY the Trades section from the tweets above.

CRITICAL REQUIREMENTS:
- ONLY include concrete, specific trade actions explicitly mentioned in tweets
- Include ONLY actual trades: buy/sell orders, options positions, specific entry/exit prices, position sizes, strike prices, expiration dates
- EVERY trade entry MUST include:
  1. **Trade Description** (what action): Specific action with ticker (e.g., "Buy **$GOOG** at $300", "Sell **$NVDA** calls", "Long **$MDB**", "Butterfly spread on **$TSLA**")
  2. **Details**: Entry price, target price, stop loss, strike prices, expiration dates, position size - include ALL details mentioned in the tweet
  3. **Reasoning**: Why the trade was made (if mentioned in tweet)
  4. **Results**: Outcomes if the trade was executed and results were shared (if mentioned)
  5. **Source tag**: [Source: @handle](tweet_url) - THIS IS REQUIRED FOR EVERY TRADE

Format requirements:
- Use bold (**$TICKER**) for tickers in description and details
- Format: **Trade Description**: Detailed explanation with all specifics (entry price, target, stop loss, strikes, expiration, position size, reasoning, results). [Source: @handle](tweet_url)
- CRITICAL: Do NOT just write "long $MDB" or "buy $GOOG" - you MUST include details, explanation, and source tag
- Use tweet URLs from [TWEET_URL:url] at the end of each tweet above
- If multiple tweets contribute to one trade, include multiple source tags: [Source: @handle1](url1) [Source: @handle2](url2)
- Be fact-checked: Only include trades explicitly mentioned - do NOT infer or assume

BAD examples (too brief, missing details/source):
- "long $MDB"
- "Buy $GOOG"
- "**$TSLA** calls"

GOOD examples (complete with details and source):
- "**Long $MDB**: Entry at $380, target $450, stop loss $350. Reasoning: Database demand accelerating with AI workloads. Position size: 100 shares. [Source: @hhuang](https://x.com/hhuang/status/123456)"
- "**Buy $GOOG at $300**: Entry at $300, target $350, stop loss $280. Reasoning: TPU system economics undervalued. [Source: @hhuang](https://x.com/hhuang/status/123456)"
- "**Sell $NVDA calls**: Strike $500, expiration 12/15, position: 10 contracts. Reasoning: Overvalued at current levels. [Source: @tig88411109](https://x.com/tig88411109/status/789012)"

Format your response as:

## Trades
- List each trade as: **Trade Description**: Detailed explanation with all specifics (prices, targets, stops, strikes, expiration, reasoning, results). [Source: @handle](url)

If NO specific trades are mentioned in the tweets, respond with only: "## Trades" (no content)."""

    # Call both LLM endpoints in parallel
    import sys
    print(f"[DEBUG] Starting parallel LLM calls for News and Trades", file=sys.stderr, flush=True)
    
    try:
        # Run both synchronous calls in parallel using asyncio.to_thread (Python 3.9+) or run_in_executor
        try:
            # Try asyncio.to_thread first (Python 3.9+)
            news_task = asyncio.to_thread(_call_llm_sync, news_prompt, "News")
            trades_task = asyncio.to_thread(_call_llm_sync, trades_prompt, "Trades")
        except AttributeError:
            # Fallback to run_in_executor for older Python versions
            loop = asyncio.get_event_loop()
            news_task = loop.run_in_executor(None, _call_llm_sync, news_prompt, "News")
            trades_task = loop.run_in_executor(None, _call_llm_sync, trades_prompt, "Trades")
        
        # Wait for both to complete
        news_result, trades_result = await asyncio.gather(
            news_task,
            trades_task,
            return_exceptions=True
        )
        
        # Handle results
        news_section = ""
        trades_section = ""
        
        if isinstance(news_result, Exception):
            print(f"[ERROR] News generation failed: {news_result}", file=sys.stderr, flush=True)
            news_section = "## News\n\n*Error generating news section.*"
        else:
            news_section = news_result.strip()
        
        if isinstance(trades_result, Exception):
            print(f"[ERROR] Trades generation failed: {trades_result}", file=sys.stderr, flush=True)
            trades_section = "## Trades\n\n*Error generating trades section.*"
        else:
            trades_section = trades_result.strip()
        
        # Combine results
        combined_summary = ""
        if news_section and news_section != "## News":
            combined_summary += news_section + "\n\n"
        if trades_section and trades_section != "## Trades":
            combined_summary += trades_section
        
        # If both sections are empty or just headers, return a message
        if not combined_summary.strip() or combined_summary.strip() in ["## News", "## Trades", "## News\n\n## Trades"]:
            return "## News\n\n*No new insights found in recent tweets.*\n\n## Trades\n\n*No specific trades mentioned in recent tweets.*"
        
        print(f"[DEBUG] Combined summary length: {len(combined_summary)} characters", file=sys.stderr, flush=True)
        return combined_summary.strip()
        
    except Exception as e:
        import sys
        error_msg = str(e)
        error_type = type(e).__name__
        print(f"[ERROR] Exception type: {error_type}", file=sys.stderr, flush=True)
        print(f"[ERROR] Error generating summary: {error_msg}", file=sys.stderr, flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {error_msg}")


@app.get("/")
async def root(response: Response):
    """Serve the frontend HTML."""
    # Prevent caching
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), media_type="text/html; charset=utf-8")


@app.get("/favicon.ico")
async def favicon():
    """Handle favicon requests to prevent 404 errors."""
    from fastapi.responses import Response
    return Response(status_code=204)  # No Content


@app.get("/manage-accounts", response_model=AccountResponse)
async def get_accounts():
    """Get list of monitored accounts with handles and usernames."""
    accounts_data = get_monitored_accounts()
    accounts = [AccountInfo(handle=acc["handle"], username=acc.get("username")) for acc in accounts_data]
    return AccountResponse(accounts=accounts)


@app.post("/manage-accounts")
async def manage_accounts(request: AccountRequest, token: str = require_auth):
    """Add a Twitter handle to monitored accounts."""
    handle = request.handle.strip().lstrip('@')
    if not handle:
        raise HTTPException(status_code=400, detail="Handle cannot be empty")
    
    # Fetch user info to get username
    user_info = fetch_user_info(handle)
    username = user_info.get("username") if user_info else None
    
    if add_account(handle, username):
        # If username was fetched, update it
        if username:
            update_account_username(handle, username)
        
        # Fetch initial tweets for new account to:
        # 1. Get username if not already fetched
        # 2. Set proper initial tracking state (won't look "forward" from current time)
        try:
            print(f"[DEBUG] Fetching initial tweets for new account: {handle}", file=sys.stderr, flush=True)
            # Fetch latest tweets (no since_id = fetch recent tweets, limited to first page ~20 tweets)
            initial_tweets = fetch_tweets(handle, since_id=None)
            
            if initial_tweets:
                print(f"[DEBUG] Fetched {len(initial_tweets)} initial tweets for {handle}", file=sys.stderr, flush=True)
                
                # Extract username from tweets if not already fetched
                if not username:
                    first_tweet = initial_tweets[0]
                    author = first_tweet.get("author", {})
                    if author:
                        username = author.get("name")
                        if username:
                            update_account_username(handle, username)
                            print(f"[DEBUG] Extracted username '{username}' from tweets for {handle}", file=sys.stderr, flush=True)
                
                # Set initial tracking state
                latest_tweet = initial_tweets[0]  # Newest first
                oldest_tweet = initial_tweets[-1]  # Oldest
                
                latest_tweet_id = latest_tweet.get("id_str") or latest_tweet.get("id")
                
                # Get timestamp of oldest tweet to set as last_fetch_timestamp_utc
                # This ensures future fetches will only get NEW tweets after this point
                oldest_created_at = oldest_tweet.get("createdAt")
                if oldest_created_at:
                    try:
                        # Parse Twitter date format: "Tue Dec 02 03:56:50 +0000 2025"
                        oldest_dt = datetime.strptime(oldest_created_at, "%a %b %d %H:%M:%S %z %Y")
                        # Convert to UTC ISO format
                        if oldest_dt.tzinfo is None:
                            oldest_dt = pytz.UTC.localize(oldest_dt)
                        last_fetch_timestamp_utc = oldest_dt.astimezone(pytz.UTC).isoformat()
                    except (ValueError, AttributeError):
                        # Fallback: try ISO format
                        try:
                            oldest_dt = datetime.fromisoformat(oldest_created_at.replace('Z', '+00:00'))
                            if oldest_dt.tzinfo is None:
                                oldest_dt = pytz.UTC.localize(oldest_dt)
                            last_fetch_timestamp_utc = oldest_dt.astimezone(pytz.UTC).isoformat()
                        except:
                            # Last resort: use current time
                            last_fetch_timestamp_utc = datetime.now(pytz.UTC).isoformat()
                else:
                    # No timestamp in tweet, use current time
                    last_fetch_timestamp_utc = datetime.now(pytz.UTC).isoformat()
                
                # Update tracking with initial state
                update_account_tracking(
                    handle=handle,
                    last_tweet_id=str(latest_tweet_id) if latest_tweet_id else None,
                    last_fetch_timestamp_utc=last_fetch_timestamp_utc
                )
                print(f"[DEBUG] Set initial tracking for {handle}: last_tweet_id={latest_tweet_id}, timestamp={last_fetch_timestamp_utc}", file=sys.stderr, flush=True)
                
                # Generate summary from initial tweets and save news/trades
                # This ensures the initial tweets are not wasted and appear in the frontend
                try:
                    print(f"[DEBUG] Generating summary from {len(initial_tweets)} initial tweets for {handle}", file=sys.stderr, flush=True)
                    
                    # Prepare tweets data structure for timestamp lookup
                    # Save to test_tweets_data.json so it's available during parsing
                    tweets_data_structure = {
                        "fetch_timestamp": datetime.now().isoformat(),
                        "total_accounts": 1,
                        "accounts": [{
                            "handle": handle,
                            "fetch_timestamp": datetime.now().isoformat(),
                            "tweet_count": len(initial_tweets),
                            "tweets": initial_tweets
                        }]
                    }
                    
                    # Save tweets data to test_tweets_data.json for timestamp lookup
                    # This file is read by save_summary when parsing news/trades
                    with open("test_tweets_data.json", 'w', encoding='utf-8') as f:
                        json.dump(tweets_data_structure, f, indent=2, ensure_ascii=False)
                    
                    # Get existing summary for context (if any)
                    latest_summary_obj = get_latest_summary()
                    previous_summary = latest_summary_obj.get("summary", "") if latest_summary_obj else ""
                    
                    # Generate summary from initial tweets
                    account_handles = [handle]
                    account_tweet_map = {handle.lower(): initial_tweets}
                    initial_summary = await generate_summary(previous_summary, initial_tweets, account_handles, account_tweet_map)
                    
                    if initial_summary and initial_summary.strip():
                        # Extract tweet IDs
                        tweet_ids = []
                        for tweet in initial_tweets:
                            tweet_id = tweet.get("id_str") or tweet.get("id")
                            if tweet_id:
                                tweet_ids.append(str(tweet_id))
                        
                        # Get generation timestamp (use oldest tweet timestamp to preserve chronological order)
                        # This ensures old tweets appear with their actual timestamps, not current time
                        generation_timestamp = last_fetch_timestamp_utc  # Use oldest tweet timestamp
                        
                        # Save summary (this will automatically parse and save news/trades)
                        # The parser will use test_tweets_data.json for timestamp lookup
                        summary_id = save_summary(
                            summary=initial_summary,
                            tweet_ids=tweet_ids,
                            generation_timestamp=generation_timestamp
                        )
                        
                        # Update account tracking with summary ID
                        update_account_tracking(
                            handle=handle,
                            last_tweet_id=str(latest_tweet_id) if latest_tweet_id else None,
                            last_fetch_timestamp_utc=last_fetch_timestamp_utc,
                            last_summary_id=summary_id
                        )
                        
                        print(f"[DEBUG] Generated and saved initial summary (ID: {summary_id}) with {len(tweet_ids)} tweets for {handle}", file=sys.stderr, flush=True)
                    else:
                        print(f"[DEBUG] Generated summary was empty for {handle}, skipping save", file=sys.stderr, flush=True)
                        
                except Exception as e:
                    print(f"[WARNING] Failed to generate summary from initial tweets for {handle}: {e}", file=sys.stderr, flush=True)
                    import traceback
                    traceback.print_exc(file=sys.stderr)
                    # Continue - account is still added successfully
            else:
                # No tweets found, set timestamp to current time
                print(f"[DEBUG] No initial tweets found for {handle}, setting timestamp to current time", file=sys.stderr, flush=True)
                update_account_tracking(
                    handle=handle,
                    last_tweet_id=None,
                    last_fetch_timestamp_utc=datetime.now(pytz.UTC).isoformat()
                )
        except Exception as e:
            print(f"[WARNING] Failed to fetch initial tweets for {handle}: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
            # Still add account, but with no initial state (will be set on first scheduled fetch)
            update_account_tracking(
                handle=handle,
                last_tweet_id=None,
                last_fetch_timestamp_utc=datetime.now(pytz.UTC).isoformat()
            )
        
        accounts_data = get_monitored_accounts()
        accounts = [AccountInfo(handle=acc["handle"], username=acc.get("username")) for acc in accounts_data]
        return {"message": f"Account @{handle} added successfully", "accounts": accounts}
    else:
        raise HTTPException(status_code=400, detail=f"Account @{handle} already exists")


@app.delete("/manage-accounts/{handle}")
async def delete_account(handle: str, token: str = require_auth):
    """Remove a Twitter handle from monitored accounts."""
    if remove_account(handle):
        accounts_data = get_monitored_accounts()
        accounts = [AccountInfo(handle=acc["handle"], username=acc.get("username")) for acc in accounts_data]
        return {"message": f"Account @{handle} removed successfully", "accounts": accounts}
    else:
        raise HTTPException(status_code=404, detail=f"Account @{handle} not found")


@app.get("/test-model")
async def test_model():
    """Test endpoint to verify model name."""
    import sys
    print("[TEST] /test-model endpoint called", file=sys.stderr, flush=True)
    model_name = "gpt-5"
    return {"model": model_name, "message": f"Model is set to: {model_name}"}

@app.post("/reset-state")
async def reset_state():
    """Reset state for all accounts (clears last_tweet_id and previous_summary)."""
    import sys
    from storage import clear_all_contexts
    print("[DEBUG] /reset-state endpoint called", file=sys.stderr, flush=True)
    clear_all_contexts()
    return {"message": "State reset successfully. All accounts will fetch tweets from the beginning."}

async def refresh_brief_logic() -> Optional[Dict]:
    """
    Core refresh logic: Fetch new tweets, generate summary, update state.
    This function can be called by both the API endpoint and the scheduler.
    
    Returns:
        Dict with summary and metadata, or None if error/no tweets
    """
    import sys
    # Also log to file for debugging
    log_file = open("refresh_brief.log", "a", encoding="utf-8")
    def log(msg):
        print(msg, file=sys.stderr, flush=True)
        print(msg, file=log_file, flush=True)
    
    log("[DEBUG] ========== refresh_brief_logic CALLED ==========")
    accounts = get_monitored_account_handles()
    log(f"[DEBUG] Monitored accounts: {accounts}")
    
    if not accounts:
        log_file.close()
        raise HTTPException(status_code=400, detail="No accounts monitored. Please add accounts first.")
    
    all_new_tweets = []
    account_tweet_map = {}
    account_last_tweet_ids = {}
    
    # Store data for all accounts to save to test_tweets_data.json
    all_accounts_data = []
    
    # Fetch new tweets for each account and track the latest tweet IDs
    for idx, handle in enumerate(accounts):
        import sys
        import json
        
        # Add delay between account fetches to avoid rate limiting (free tier: 1 request per 5 seconds)
        if idx > 0:
            log(f"[DEBUG] Waiting 6 seconds before fetching next account (rate limit protection)...")
            await asyncio.sleep(6)  # 6 seconds to be safe (API limit is 5 seconds)
        
        context = get_session_context(handle)
        last_tweet_id = context.get("last_tweet_id")
        last_fetch_timestamp_utc = context.get("last_fetch_timestamp_utc")
        
        # Use hybrid fetch: timestamp primary, since_id fallback
        log(f"[DEBUG] Fetching tweets for {handle}")
        log(f"[DEBUG]   last_tweet_id: {last_tweet_id}")
        log(f"[DEBUG]   last_fetch_timestamp_utc: {last_fetch_timestamp_utc}")
        
        tweets = fetch_tweets_hybrid(handle, since_id=last_tweet_id, last_fetch_timestamp_utc=last_fetch_timestamp_utc)
        log(f"[DEBUG] fetch_tweets returned {len(tweets)} tweets for {handle}")
        
        # Extract and store username from tweets if we have tweets and don't have username stored
        if tweets:
            first_tweet = tweets[0]
            author = first_tweet.get("author", {})
            if author:
                username = author.get("name")
                if username:
                    # Check if we already have username stored
                    accounts_data = get_monitored_accounts()
                    account_info = next((acc for acc in accounts_data if acc["handle"] == handle.lower()), None)
                    if not account_info or not account_info.get("username"):
                        update_account_username(handle, username)
                        log(f"[DEBUG] Stored username '{username}' for account {handle}")
        
        # Calculate the NEW last_tweet_id (latest tweet from fetched tweets)
        new_last_tweet_id = last_tweet_id  # Default to old one if no new tweets
        if tweets:
            latest_tweet = tweets[0]  # Tweets are sorted newest first
            new_last_tweet_id = latest_tweet.get("id_str") or latest_tweet.get("id")
            if new_last_tweet_id:
                new_last_tweet_id = str(new_last_tweet_id)
        
        # Store data for this account (will save all accounts together at the end)
        all_accounts_data.append({
            "handle": handle,
            "fetch_timestamp": datetime.now().isoformat(),
            "since_id_used_for_filtering": last_tweet_id,  # What was actually used to filter (None for first fetch)
            "last_fetch_timestamp_utc": last_fetch_timestamp_utc,  # Timestamp used for Advanced Search
            "last_tweet_id_in_state": last_tweet_id,  # What was in state before fetch
            "last_tweet_id": new_last_tweet_id,  # New: latest tweet ID from fetched tweets (will be saved to state)
            "had_last_tweet_id": bool(last_tweet_id),
            "tweet_count": len(tweets),
            "tweets": tweets
        })
        
        log(f"[DEBUG] Collected {len(tweets)} tweets for {handle} (will save all accounts together)")
        log(f"[DEBUG]   had_last_tweet_id: {bool(last_tweet_id)}")
        log(f"[DEBUG]   last_fetch_timestamp_utc: {last_fetch_timestamp_utc}")
        log(f"[DEBUG]   last_tweet_id_in_state: {last_tweet_id}")
        log(f"[DEBUG]   new_last_tweet_id (latest fetched): {new_last_tweet_id}")
        
        if tweets:
            all_new_tweets.extend(tweets)
            account_tweet_map[handle] = tweets
            # Track the most recent tweet ID for this account
            # Tweets are sorted by created_at (newest first), so first tweet is the latest
            if tweets:
                latest_tweet = tweets[0]
                latest_tweet_id = latest_tweet.get("id_str") or latest_tweet.get("id")
                if latest_tweet_id:
                    account_last_tweet_ids[handle] = str(latest_tweet_id)
                else:
                    account_last_tweet_ids[handle] = last_tweet_id
            else:
                account_last_tweet_ids[handle] = last_tweet_id
        else:
            # No new tweets, keep the existing last_tweet_id
            account_last_tweet_ids[handle] = last_tweet_id
    
    # Save all accounts' tweet data to test_tweets_data.json (after fetching all accounts)
    test_data_file = "test_tweets_data.json"
    try:
        with open(test_data_file, 'w', encoding='utf-8') as f:
            json.dump({
                "fetch_timestamp": datetime.now().isoformat(),
                "total_accounts": len(accounts),
                "accounts": all_accounts_data
            }, f, indent=2, ensure_ascii=False)
        total_tweets = sum(acc["tweet_count"] for acc in all_accounts_data)
        log(f"[DEBUG] Saved data for {len(accounts)} accounts ({total_tweets} total tweets) to {test_data_file}")
    except Exception as e:
        log(f"[ERROR] Failed to save test data: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)
    
    # Get latest summary from database (if exists) for context
    latest_summary_obj = get_latest_summary()
    combined_previous_summary = latest_summary_obj.get("summary", "") if latest_summary_obj else ""
    
    log(f"[DEBUG] latest_summary from database length: {len(combined_previous_summary)}")
    log(f"[DEBUG] Total new tweets collected: {len(all_new_tweets)}")
    
    # Helper function to clean old summary format
    def clean_summary(summary: str) -> str:
        """Remove Market Context section and 'No New Updates' messages from summary."""
        import re
        # Remove Market Context section
        summary = re.sub(r'## Market Context\s*\n.*?(?=\n## |$)', '', summary, flags=re.DOTALL)
        # Remove "No New Updates" or similar messages
        summary = re.sub(r'-?\s*\*\*No New Updates?\*\*:.*?\n', '', summary, flags=re.IGNORECASE)
        summary = re.sub(r'-?\s*No new tweets? from.*?\n', '', summary, flags=re.IGNORECASE)
        summary = re.sub(r'-?\s*No New Updates?:.*?\n', '', summary, flags=re.IGNORECASE)
        # Remove account prefixes like "@hhuang: "
        summary = re.sub(r'^@\w+:\s*', '', summary, flags=re.MULTILINE)
        # Clean up extra blank lines
        summary = re.sub(r'\n{3,}', '\n\n', summary)
        return summary.strip()
    
    # If no new tweets, return the cleaned previous summary without regenerating
    if len(all_new_tweets) == 0:
        log(f"[DEBUG] No new tweets found - returning cleaned previous summary without regeneration")
        
        # Update account tracking timestamps even if no new tweets (to record the fetch attempt)
        current_timestamp_utc = datetime.now(pytz.UTC).isoformat()
        for handle in accounts:
            update_params = {
                "handle": handle,
                "last_tweet_id": account_last_tweet_ids.get(handle),
                "last_fetch_timestamp_utc": current_timestamp_utc
            }
            log(f"[DEBUG] Updating account tracking for {handle}: last_tweet_id={update_params.get('last_tweet_id')}, timestamp={current_timestamp_utc}")
            update_account_tracking(**update_params)
        
        if combined_previous_summary and combined_previous_summary.strip():
            cleaned_summary = clean_summary(combined_previous_summary)
            log_file.close()
            # Return dict for scheduler use (not RefreshResponse)
            return {
                "summary": cleaned_summary,
                "tweet_count": 0,
                "summary_id": None,
                "accounts": accounts
            }
        else:
            log_file.close()
            raise HTTPException(status_code=400, detail="No tweets found and no previous summary available. Please wait for new tweets or check your monitored accounts.")
    
    # Generate new summary only if there are new tweets
    log(f"[DEBUG] About to call generate_summary with {len(all_new_tweets)} tweets")
    try:
        new_summary = await generate_summary(combined_previous_summary, all_new_tweets, accounts, account_tweet_map)
        log(f"[DEBUG] generate_summary returned, length: {len(new_summary) if new_summary else 0}")
        if not new_summary or not new_summary.strip():
            log(f"[WARNING] generate_summary returned empty summary!")
            log(f"[WARNING] all_new_tweets count: {len(all_new_tweets)}")
            log(f"[WARNING] combined_previous_summary: {combined_previous_summary[:100] if combined_previous_summary else 'None'}...")
    except Exception as e:
        log(f"[ERROR] Exception in refresh_brief when calling generate_summary: {e}")
        import traceback
        traceback.print_exc(file=log_file)
        log_file.close()
        raise
    
    # Clean the new summary before saving (remove Market Context, "No New Updates", etc.)
    cleaned_new_summary = clean_summary(new_summary)
    
    # Extract tweet IDs from the fetched tweets
    tweet_ids = []
    for tweet in all_new_tweets:
        tweet_id = tweet.get("id_str") or tweet.get("id")
        if tweet_id:
            tweet_ids.append(str(tweet_id))
    
    # Save summary to database and update account tracking
    summary_id = None
    if cleaned_new_summary and cleaned_new_summary.strip():
        try:
            summary_id = save_summary(
                summary=cleaned_new_summary,
                tweet_ids=tweet_ids,
                generation_timestamp=datetime.now().isoformat()
            )
            log(f"[DEBUG] Saved summary to database with ID: {summary_id}, tweet_ids: {len(tweet_ids)}")
        except Exception as e:
            log(f"[ERROR] Failed to save summary to database: {e}")
            import traceback
            traceback.print_exc(file=log_file)
    
    # Update account tracking for all accounts with latest tweet IDs, timestamp, and summary ID
    # Note: We don't store previous_summary anymore - it's fetched from summaries table
    # IMPORTANT: Update timestamp and tweet IDs even if no summary was generated (as long as we fetched tweets)
    # This ensures we don't re-fetch the same tweets on the next run
    current_timestamp_utc = datetime.now(pytz.UTC).isoformat()
    for handle in accounts:
        update_params = {
            "handle": handle,
            "last_tweet_id": account_last_tweet_ids.get(handle),
            "last_fetch_timestamp_utc": current_timestamp_utc
        }
        if summary_id:
            update_params["last_summary_id"] = summary_id
        log(f"[DEBUG] Updating account tracking for {handle}: last_tweet_id={update_params.get('last_tweet_id')}, timestamp={current_timestamp_utc}")
        update_account_tracking(**update_params)
    
    log(f"[DEBUG] Returning RefreshResponse with summary length: {len(cleaned_new_summary)}")
    
    # Debug: Check if the summary being returned contains $1 placeholders
    if "$1" in cleaned_new_summary or "$2" in cleaned_new_summary:
        log(f"[ERROR] WARNING: Summary being returned to frontend contains $1 or $2 placeholders!")
        import re
        matches = list(re.finditer(r'\$[12](?![0-9.])', new_summary))
        log(f"[ERROR] Found {len(matches)} placeholder occurrences in final summary")
        for i, match in enumerate(matches[:5]):  # Show first 5
            start, end = match.span()
            context_start = max(0, start - 100)
            context_end = min(len(new_summary), end + 100)
            context = new_summary[context_start:context_end]
            log(f"[ERROR]   Placeholder at position {start}: ...{context}...")
    else:
        log(f"[DEBUG] Summary being returned does NOT contain $1 or $2 placeholders - GOOD!")
        # Show sample of what's being returned
        log(f"[DEBUG] First 500 chars of summary being returned: {cleaned_new_summary[:500]}")
    
    log_file.close()
    
    # Return result dict for scheduler use
    return {
        "summary": cleaned_new_summary,
        "tweet_count": len(all_new_tweets),
        "summary_id": summary_id,
        "accounts": accounts
    }


@app.post("/refresh-brief-dev", response_model=RefreshResponse)
async def refresh_brief_dev(response: Response, token: str = Query(...)):
    verify_token(token)
    # Prevent caching
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    """Development endpoint: Use sample data from test_tweets_data.json instead of calling Twitter API."""
    import sys
    import os
    
    log_file = open("refresh_brief.log", "a", encoding="utf-8")
    def log(msg):
        print(msg, file=sys.stderr, flush=True)
        print(msg, file=log_file, flush=True)
    
    log("[DEBUG] ========== /refresh-brief-dev CALLED (USING SAMPLE DATA) ==========")
    
    # Load sample data from test_tweets_data.json
    test_data_file = "test_tweets_data.json"
    if not os.path.exists(test_data_file):
        log_file.close()
        raise HTTPException(status_code=404, detail=f"Sample data file '{test_data_file}' not found. Please run a normal refresh first to generate sample data.")
    
    try:
        with open(test_data_file, 'r', encoding='utf-8') as f:
            sample_data = json.load(f)
    except Exception as e:
        log_file.close()
        raise HTTPException(status_code=500, detail=f"Failed to load sample data: {e}")
    
    log(f"[DEBUG] Loaded sample data with {sample_data.get('total_accounts', 0)} accounts")
    
    # Extract accounts and tweets from sample data
    accounts_data = sample_data.get("accounts", [])
    if not accounts_data:
        log_file.close()
        raise HTTPException(status_code=400, detail="Sample data contains no accounts")
    
    # Get account handles from sample data
    accounts = [acc["handle"] for acc in accounts_data]
    log(f"[DEBUG] Accounts in sample data: {accounts}")
    
    all_new_tweets = []
    account_last_tweet_ids = {}
    
    # Process each account's tweets from sample data
    for account_data in accounts_data:
        handle = account_data["handle"]
        tweets = account_data.get("tweets", [])
        
        log(f"[DEBUG] Processing {len(tweets)} tweets for {handle} from sample data")
        
        # Calculate the latest tweet ID
        new_last_tweet_id = account_data.get("last_tweet_id")
        if tweets:
            latest_tweet = tweets[0]  # Tweets should be sorted newest first
            latest_tweet_id = latest_tweet.get("id_str") or latest_tweet.get("id")
            if latest_tweet_id:
                new_last_tweet_id = str(latest_tweet_id)
        
        if tweets:
            all_new_tweets.extend(tweets)
            account_last_tweet_ids[handle] = new_last_tweet_id
        else:
            # Get existing last_tweet_id from state if no tweets
            context = get_session_context(handle)
            account_last_tweet_ids[handle] = context.get("last_tweet_id")
    
    log(f"[DEBUG] Total tweets from sample data: {len(all_new_tweets)}")
    
    # Get latest summary from database (if exists) for context
    latest_summary_obj = get_latest_summary()
    combined_previous_summary = latest_summary_obj.get("summary", "") if latest_summary_obj else ""
    
    log(f"[DEBUG] latest_summary from database length: {len(combined_previous_summary)}")
    log(f"[DEBUG] Total new tweets collected: {len(all_new_tweets)}")
    
    # Helper function to clean old summary format
    def clean_summary(summary: str) -> str:
        """Remove Market Context section and 'No New Updates' messages from summary."""
        import re
        # Remove Market Context section
        summary = re.sub(r'## Market Context\s*\n.*?(?=\n## |$)', '', summary, flags=re.DOTALL)
        # Remove "No New Updates" or similar messages
        summary = re.sub(r'-?\s*\*\*No New Updates?\*\*:.*?\n', '', summary, flags=re.IGNORECASE)
        summary = re.sub(r'-?\s*No new tweets? from.*?\n', '', summary, flags=re.IGNORECASE)
        summary = re.sub(r'-?\s*No New Updates?:.*?\n', '', summary, flags=re.IGNORECASE)
        # Remove account prefixes like "@hhuang: "
        summary = re.sub(r'^@\w+:\s*', '', summary, flags=re.MULTILINE)
        # Clean up extra blank lines
        summary = re.sub(r'\n{3,}', '\n\n', summary)
        return summary.strip()
    
    # If no new tweets, return the cleaned previous summary without regenerating
    if len(all_new_tweets) == 0:
        log(f"[DEBUG] No new tweets found in sample data - returning cleaned previous summary without regeneration")
        if combined_previous_summary and combined_previous_summary.strip():
            cleaned_summary = clean_summary(combined_previous_summary)
            log_file.close()
            return RefreshResponse(summary=cleaned_summary)
        else:
            log_file.close()
            raise HTTPException(status_code=400, detail="No tweets found in sample data and no previous summary available.")
    
    # Generate new summary using sample tweets
    log(f"[DEBUG] About to call generate_summary with {len(all_new_tweets)} tweets from sample data")
    try:
        new_summary = await generate_summary(combined_previous_summary, all_new_tweets, accounts)
        log(f"[DEBUG] generate_summary returned, length: {len(new_summary) if new_summary else 0}")
        if not new_summary or not new_summary.strip():
            log(f"[WARNING] generate_summary returned empty summary!")
    except Exception as e:
        log(f"[ERROR] Exception in refresh_brief_dev when calling generate_summary: {e}")
        import traceback
        traceback.print_exc(file=log_file)
        log_file.close()
        raise
    
    # Clean the new summary before saving
    cleaned_new_summary = clean_summary(new_summary)
    
    # Extract tweet IDs from the fetched tweets
    tweet_ids = []
    for tweet in all_new_tweets:
        tweet_id = tweet.get("id_str") or tweet.get("id")
        if tweet_id:
            tweet_ids.append(str(tweet_id))
    
    # Save summary to database and update account tracking
    summary_id = None
    if cleaned_new_summary and cleaned_new_summary.strip():
        try:
            summary_id = save_summary(cleaned_new_summary, tweet_ids, datetime.now().isoformat())
            log(f"[DEBUG] Saved summary to database with ID: {summary_id}, tweet_ids: {len(tweet_ids)}")
        except Exception as e:
            log(f"[ERROR] Failed to save summary to database: {e}")
            import traceback
            traceback.print_exc(file=log_file)
    
    # Update account tracking for all accounts with latest tweet IDs, timestamp, and summary ID
    # Note: We don't store previous_summary anymore - it's fetched from summaries table
    if summary_id:
        current_timestamp_utc = datetime.now(pytz.UTC).isoformat()
        for handle in accounts:
            update_account_tracking(
                handle,
                last_tweet_id=account_last_tweet_ids.get(handle),
                last_fetch_timestamp_utc=current_timestamp_utc,
                last_summary_id=summary_id
            )
    
    log(f"[DEBUG] Returning RefreshResponse with summary length: {len(cleaned_new_summary)}")
    log(f"[DEBUG] ========== /refresh-brief-dev COMPLETED ==========")
    
    log_file.close()
    return RefreshResponse(summary=cleaned_new_summary)


@app.post("/refresh-brief-ui-dev", response_model=RefreshResponse)
async def refresh_brief_ui_dev(response: Response, token: str = Query(...)):
    verify_token(token)
    """UI Development endpoint: Returns latest summary from database without any API calls."""
    # Prevent caching
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    import sys
    log_file = open("refresh_brief.log", "a", encoding="utf-8")
    def log(msg):
        print(msg, file=sys.stderr, flush=True)
        print(msg, file=log_file, flush=True)
    
    log("[DEBUG] ========== /refresh-brief-ui-dev CALLED (UI DEV MODE) ==========")
    
    # Get latest summary from database
    latest_summary_obj = get_latest_summary()
    
    if not latest_summary_obj or not latest_summary_obj.get("summary", "").strip():
        log_file.close()
        raise HTTPException(status_code=400, detail="No saved summary found in database. Please run a normal refresh first.")
    
    combined_previous_summary = latest_summary_obj.get("summary", "")
    
    log(f"[DEBUG] Returning saved summary from database (length: {len(combined_previous_summary)})")
    log_file.close()
    
    return RefreshResponse(summary=combined_previous_summary)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, token: str = require_auth):
    """Chat endpoint for asking questions about the financial summary."""
    if not openai_client:
        raise HTTPException(status_code=500, detail="AI Builder API key not configured")
    
    if not request.summary or not request.summary.strip():
        return ChatResponse(answer="I don't have access to a financial summary yet. Please refresh the market intel first to generate a summary, then ask me questions about it.")
    
    try:
        import sys
        model_name = "supermind-agent-v1"
        print(f"[DEBUG] Chat using model: {model_name}", file=sys.stderr, flush=True)
        
        # Construct prompt for chat
        prompt = f"""You are a helpful financial analyst assistant. A user is asking you a question about a financial summary that was generated from Twitter posts by financial influencers.

Financial Summary:
{request.summary}

User Question: {request.question}

Please provide a clear, helpful, and educational answer to the user's question. If the question is about:
- Trading strategies (like butterfly options, 0DTE, etc.), explain how they work, their risks and benefits
- Tickers or stocks, provide context about the company and the insights mentioned
- Market insights, explain the reasoning and implications
- Any other financial concepts, be educational and clear

If the question cannot be answered from the summary, politely say so and suggest what information might be needed.

Keep your answer concise but informative. Use markdown formatting for better readability."""
        
        response = openai_client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful financial analyst assistant specializing in explaining trading strategies, market insights, and financial concepts."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        if response.choices and response.choices[0].message.content:
            answer = response.choices[0].message.content.strip()
            print(f"[DEBUG] Chat response length: {len(answer)} characters", file=sys.stderr, flush=True)
            return ChatResponse(answer=answer)
        else:
            raise Exception("No response from AI API")
    except Exception as e:
        import sys
        error_msg = str(e)
        print(f"[ERROR] Chat error: {error_msg}", file=sys.stderr, flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to get chat response: {error_msg}")


@app.get("/summaries", response_model=SummariesResponse)
async def get_summaries_endpoint(limit: int = 10, offset: int = 0):
    """
    Get paginated summaries from the database.
    
    Args:
        limit: Number of summaries to return (default: 10)
        offset: Number of summaries to skip (default: 0)
    
    Returns:
        SummariesResponse with list of summaries and pagination info
    """
    summaries = get_summaries(limit=limit, offset=offset)
    total = get_summary_count()
    
    return SummariesResponse(
        summaries=[SummaryItem(**s) for s in summaries],
        total=total,
        limit=limit,
        offset=offset
    )


@app.get("/merged-items", response_model=MergedItemsResponse)
async def get_merged_items(
    limit: int = 10, 
    offset: int = 0, 
    item_type: str = "all",
    include_liked_status: bool = Query(False, description="Include liked status for items"),
    include_thoughts: bool = Query(False, description="Include thoughts for items")
):
    """
    Get merged news and trades items from pre-computed parsed items, sorted chronologically.
    This endpoint is fast because it queries pre-parsed items instead of parsing summaries on-the-fly.
    
    Performance optimization: Can batch return liked status and thoughts to reduce HTTP round trips.
    
    Args:
        limit: Number of items to return per type (default: 10)
        offset: Number of items to skip (default: 0)
        item_type: "all", "news", or "trades" (default: "all")
        include_liked_status: If True, include liked status for each item (default: False)
        include_thoughts: If True, include thoughts for each item (default: False)
    
    Returns:
        MergedItemsResponse with chronologically sorted news and trades
    """
    import time
    start_time = time.time()
    
    # Get pre-computed parsed items directly from database (fast!)
    # Duplicates are prevented at the database level via unique index on content_hash
    all_news = get_all_parsed_news_items()
    all_trades = get_all_parsed_trades_items()
    
    # Sort by timestamp (newest first)
    all_news.sort(key=lambda x: x["timestamp"], reverse=True)
    all_trades.sort(key=lambda x: x["timestamp"], reverse=True)
    
    # Apply pagination
    if item_type == "news":
        paginated_news = all_news[offset:offset + limit]
        paginated_trades = []
    elif item_type == "trades":
        paginated_news = []
        paginated_trades = all_trades[offset:offset + limit]
    else:  # "all"
        paginated_news = all_news[offset:offset + limit]
        paginated_trades = all_trades[offset:offset + limit]
    
    # Batch fetch liked status and thoughts if requested
    liked_hashes_set = set()
    thoughts_map = {}
    
    if include_liked_status or include_thoughts:
        from database import generate_news_hash, get_liked_status, get_thoughts_batch
        
        # Generate hashes for all paginated items
        all_items = paginated_news + paginated_trades
        item_hashes = []
        for item in all_items:
            item_hash = generate_news_hash(
                item.get("title", ""),
                item.get("content", ""),
                item.get("timestamp", "")
            )
            item_hashes.append(item_hash)
        
        # Batch fetch liked status
        if include_liked_status and item_hashes:
            liked_hashes = get_liked_status(item_hashes)
            liked_hashes_set = set(liked_hashes)
        
        # Batch fetch thoughts
        if include_thoughts and item_hashes:
            thoughts_map = get_thoughts_batch(item_hashes)
    
    # Build response items with optional liked status and thoughts
    news_items = []
    for item in paginated_news:
        item_dict = dict(item)
        # Always include is_liked and thought fields when batch parameters are requested
        # This allows frontend to detect batch data even if values are None/False
        if include_liked_status:
            item_hash = generate_news_hash(
                item.get("title", ""),
                item.get("content", ""),
                item.get("timestamp", "")
            )
            item_dict["is_liked"] = item_hash in liked_hashes_set
        elif include_liked_status is False:
            # Explicitly set to None so frontend knows batch data is not available
            item_dict["is_liked"] = None
        
        if include_thoughts:
            item_hash = generate_news_hash(
                item.get("title", ""),
                item.get("content", ""),
                item.get("timestamp", "")
            )
            item_dict["thought"] = thoughts_map.get(item_hash)  # Returns None if not found
        elif include_thoughts is False:
            # Explicitly set to None so frontend knows batch data is not available
            item_dict["thought"] = None
        
        news_items.append(NewsTradeItem(**item_dict))
    
    trades_items = []
    for item in paginated_trades:
        item_dict = dict(item)
        # Always include is_liked and thought fields when batch parameters are requested
        if include_liked_status:
            item_hash = generate_news_hash(
                item.get("title", ""),
                item.get("content", ""),
                item.get("timestamp", "")
            )
            item_dict["is_liked"] = item_hash in liked_hashes_set
        elif include_liked_status is False:
            item_dict["is_liked"] = None
        
        if include_thoughts:
            item_hash = generate_news_hash(
                item.get("title", ""),
                item.get("content", ""),
                item.get("timestamp", "")
            )
            item_dict["thought"] = thoughts_map.get(item_hash)  # Returns None if not found
        elif include_thoughts is False:
            item_dict["thought"] = None
        
        trades_items.append(NewsTradeItem(**item_dict))
    
    elapsed_time = time.time() - start_time
    print(f"[PERF] /merged-items: {elapsed_time*1000:.2f}ms (limit={limit}, include_liked={include_liked_status}, include_thoughts={include_thoughts})", file=sys.stderr, flush=True)
    
    return MergedItemsResponse(
        news=news_items,
        trades=trades_items,
        total_news=len(all_news),
        total_trades=len(all_trades)
    )


# ==================== News Likes and Thoughts API Endpoints ====================

@app.post("/api/news/like")
async def like_news(request: NewsLikeRequest):
    """Like a news item."""
    try:
        from database import save_news_like
        success = save_news_like(
            news_hash=request.news_hash,
            title=request.title,
            content=request.content,
            timestamp=request.timestamp,
            source_tags=request.source_tags,
            tweet_ids=request.tweet_ids
        )
        if success:
            return {"status": "success", "message": "News item liked"}
        else:
            return {"status": "already_liked", "message": "News item already liked"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/news/like/{news_hash}")
async def unlike_news(news_hash: str):
    """Unlike a news item."""
    try:
        from database import remove_news_like
        success = remove_news_like(news_hash)
        if success:
            return {"status": "success", "message": "News item unliked"}
        else:
            raise HTTPException(status_code=404, detail="News item not found in likes")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/news/likes", response_model=NewsLikesResponse)
async def get_liked_news(limit: int = 10, offset: int = 0):
    """Get paginated list of liked news items."""
    try:
        from database import get_news_likes, get_news_likes_count
        likes = get_news_likes(limit=limit, offset=offset)
        total = get_news_likes_count()
        
        return NewsLikesResponse(
            likes=[NewsLikeItem(**like) for like in likes],
            total=total
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/news/thought")
async def save_news_thought(request: NewsThoughtRequest):
    """Save or update a thought for a news item."""
    try:
        import sys
        print(f"[DEBUG] Saving thought for hash: {request.news_hash}", file=sys.stderr, flush=True)
        print(f"[DEBUG] Title: {request.title[:50] if request.title else 'None'}", file=sys.stderr, flush=True)
        print(f"[DEBUG] Content length: {len(request.content) if request.content else 0}", file=sys.stderr, flush=True)
        
        from database import save_news_thought
        success = save_news_thought(
            news_hash=request.news_hash,
            thought=request.thought,
            title=request.title,
            content=request.content,
            timestamp=request.timestamp,
            source_tags=request.source_tags,
            tweet_ids=request.tweet_ids
        )
        if success:
            print(f"[DEBUG] Thought saved successfully", file=sys.stderr, flush=True)
            return {"status": "success", "message": "Thought saved"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save thought")
    except HTTPException:
        raise
    except Exception as e:
        import sys
        print(f"[ERROR] Error saving thought: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/news/thought/{news_hash}", response_model=NewsThoughtResponse)
async def get_news_thought(news_hash: str):
    """Get thought for a specific news item."""
    try:
        from database import get_news_thought
        thought = get_news_thought(news_hash)
        return NewsThoughtResponse(thought=thought)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/news/liked-status", response_model=LikedStatusResponse)
async def get_liked_status(news_hashes: str):
    """
    Get which news items are liked.
    
    Args:
        news_hashes: Comma-separated list of news hashes
    """
    try:
        from database import get_liked_status
        hash_list = [h.strip() for h in news_hashes.split(',') if h.strip()]
        liked_hashes = get_liked_status(hash_list)
        return LikedStatusResponse(liked_hashes=liked_hashes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/news/thoughts", response_model=NewsThoughtsResponse)
async def get_all_news_thoughts(limit: int = 20, offset: int = 0):
    """Get paginated list of all thoughts with their associated news items."""
    try:
        from database import get_all_news_thoughts, get_news_thoughts_count
        thoughts = get_all_news_thoughts(limit=limit, offset=offset)
        total = get_news_thoughts_count()
        
        return NewsThoughtsResponse(
            thoughts=[NewsThoughtItem(**thought) for thought in thoughts],
            total=total
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/news/thought/{news_hash}")
async def delete_news_thought_endpoint(news_hash: str):
    """Delete a thought for a news item."""
    try:
        from database import delete_news_thought
        deleted = delete_news_thought(news_hash)
        if deleted:
            return {"status": "success", "message": "Thought deleted"}
        else:
            raise HTTPException(status_code=404, detail="Thought not found")
    except HTTPException:
        raise
    except Exception as e:
        import sys
        print(f"[ERROR] Error deleting thought: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Admin API Endpoints ====================

@app.post("/api/summaries/remove-duplicates")
async def remove_duplicate_summaries_endpoint():
    """Remove duplicate summaries that have the same tweet_ids."""
    try:
        from database import remove_duplicate_summaries
        result = remove_duplicate_summaries()
        return {
            "status": "success",
            "message": f"Removed {result['duplicates_removed']} duplicate summaries",
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/scheduler/status")
async def get_scheduler_status(token: str = require_admin_query):
    """Get scheduler status and configuration."""
    try:
        from scheduler import get_scheduler_manager
        scheduler_manager = get_scheduler_manager()
        status = scheduler_manager.get_status()
        return status
    except Exception as e:
        return {"error": str(e), "enabled": False, "running": False}


@app.post("/api/scheduler/pause")
async def pause_scheduler(token: str = Query(...)):
    verify_token(token)
    """Pause the scheduler."""
    try:
        from scheduler import get_scheduler_manager
        scheduler_manager = get_scheduler_manager()
        scheduler_manager.pause()
        return {"status": "paused", "message": "Scheduler paused successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scheduler/resume")
async def resume_scheduler(token: str = Query(...)):
    verify_token(token)
    """Resume the scheduler."""
    try:
        from scheduler import get_scheduler_manager
        scheduler_manager = get_scheduler_manager()
        scheduler_manager.resume()
        return {"status": "resumed", "message": "Scheduler resumed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scheduler/trigger")
async def trigger_scheduler(token: str = Query(...)):
    verify_token(token)
    """Manually trigger a refresh now."""
    try:
        from scheduler import get_scheduler_manager
        scheduler_manager = get_scheduler_manager()
        scheduler_manager.trigger_now()
        return {"status": "triggered", "message": "Manual refresh triggered"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scheduler/test")
async def test_scheduler(seconds: int = 60, token: str = Query(...)):
    verify_token(token)
    """
    Schedule a test job that will run automatically in X seconds.
    Useful for testing scheduler functionality without waiting for the next scheduled time.
    
    Args:
        seconds: Number of seconds from now to schedule the test job (default: 60, min: 10)
    
    Returns:
        Dict with job info and scheduled time
    """
    if seconds < 10:
        raise HTTPException(status_code=400, detail="Minimum delay is 10 seconds for safety")
    
    if seconds > 3600:
        raise HTTPException(status_code=400, detail="Maximum delay is 3600 seconds (1 hour)")
    
    try:
        from scheduler import get_scheduler_manager
        scheduler_manager = get_scheduler_manager()
        result = scheduler_manager.schedule_test_job(seconds_from_now=seconds)
        return {
            "status": "scheduled",
            **result
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/scheduler/logs")
async def get_scheduler_logs(limit: int = 50, offset: int = 0, token: str = Query(...)):
    """Get scheduler logs."""
    try:
        from database import get_scheduler_logs
        logs = get_scheduler_logs(limit=limit, offset=offset)
        return {"logs": logs, "limit": limit, "offset": offset}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/scheduler/config")
async def get_scheduler_config(token: str = Query(...)):
    """Get scheduler configuration."""
    try:
        from config import load_config
        config = load_config()
        return config.get("scheduler", {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scheduler/config")
async def update_scheduler_config(config_update: Dict, token: str = Query(...)):
    verify_token(token)
    """Update scheduler configuration (currently only supports enabling/disabling)."""
    try:
        import json
        import os
        
        # Load current config
        config_file = "config.json"
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            from config import DEFAULT_CONFIG
            config = DEFAULT_CONFIG.copy()
        
        # Update scheduler enabled status if provided
        if "enabled" in config_update:
            if "scheduler" not in config:
                config["scheduler"] = {}
            config["scheduler"]["enabled"] = bool(config_update["enabled"])
            
            # Save to file
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            
            # If disabling, stop scheduler; if enabling, start it
            from scheduler import get_scheduler_manager
            scheduler_manager = get_scheduler_manager()
            
            if not config_update["enabled"]:
                scheduler_manager.stop()
                return {"status": "disabled", "message": "Scheduler disabled. Restart server to re-enable."}
            else:
                if not scheduler_manager.scheduler or not scheduler_manager.scheduler.running:
                    scheduler_manager.start()
                    return {"status": "enabled", "message": "Scheduler enabled and started."}
                else:
                    return {"status": "enabled", "message": "Scheduler already running."}
        
        return {"status": "updated", "message": "Configuration updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin")
async def admin_page():
    """Serve the admin page. Authentication is handled client-side."""
    try:
        with open("admin.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Admin page not found</h1>", status_code=404)


@app.get("/view-summaries")
async def view_summaries_page():
    """Serve the summaries database viewer page."""
    try:
        with open("view_summaries.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Summaries viewer page not found</h1>", status_code=404)


if __name__ == "__main__":
    import uvicorn
    # Read PORT from environment variable (required for deployment platforms like Koyeb)
    port = int(os.getenv("PORT", "8000"))
    # Increase timeout for long-running AI operations
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        timeout_keep_alive=300,  # 5 minutes
        timeout_graceful_shutdown=300
    )

