"""
SQLite database for storing summaries with timestamps and tweet metadata.
"""
import sqlite3
import json
from typing import List, Dict, Optional
from datetime import datetime
import os
import hashlib

DB_FILE = "summaries.db"


def init_database():
    """Initialize the database with required tables."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create summaries table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            summary TEXT NOT NULL,
            tweet_ids TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create accounts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            handle TEXT PRIMARY KEY,
            username TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create account_tracking table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS account_tracking (
            handle TEXT PRIMARY KEY,
            last_tweet_id TEXT,
            last_fetch_timestamp_utc TEXT,
            last_summary_id INTEGER,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (handle) REFERENCES accounts(handle),
            FOREIGN KEY (last_summary_id) REFERENCES summaries(id)
        )
    """)
    
    # Create scheduler_logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduler_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            account_handle TEXT,
            fetch_type TEXT,
            status TEXT NOT NULL,
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            tweets_fetched INTEGER,
            summary_generated BOOLEAN,
            FOREIGN KEY (account_handle) REFERENCES accounts(handle)
        )
    """)
    
    # Create news_likes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_hash TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            liked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            source_tags TEXT,
            tweet_ids TEXT
        )
    """)
    
    # Create news_thoughts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news_thoughts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_hash TEXT NOT NULL,
            thought TEXT NOT NULL,
            title TEXT,
            content TEXT,
            timestamp TEXT,
            source_tags TEXT,
            tweet_ids TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Migrate existing news_thoughts table if it doesn't have new columns
    try:
        cursor.execute("ALTER TABLE news_thoughts ADD COLUMN title TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE news_thoughts ADD COLUMN content TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE news_thoughts ADD COLUMN timestamp TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE news_thoughts ADD COLUMN source_tags TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE news_thoughts ADD COLUMN tweet_ids TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Create indexes for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp ON summaries(timestamp)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_scheduler_logs_timestamp ON scheduler_logs(timestamp)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_scheduler_logs_account ON scheduler_logs(account_handle)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_news_likes_hash ON news_likes(news_hash)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_news_thoughts_hash ON news_thoughts(news_hash)
    """)
    
    conn.commit()
    conn.close()


def save_summary(summary: str, tweet_ids: List[str], generation_timestamp: Optional[str] = None) -> int:
    """
    Save a summary to the database.
    If a summary with the same tweet_ids already exists, updates it instead of creating a duplicate.
    
    Args:
        summary: The markdown summary text
        tweet_ids: List of tweet IDs used in this summary
        generation_timestamp: ISO format timestamp (defaults to now)
    
    Returns:
        The ID of the saved/updated summary
    """
    if generation_timestamp is None:
        generation_timestamp = datetime.now().isoformat()
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Normalize tweet_ids for comparison (sort and convert to set then back to list for consistent comparison)
    normalized_tweet_ids = sorted(set(str(tid) for tid in tweet_ids))
    tweet_ids_json = json.dumps(normalized_tweet_ids)
    
    # Check if a summary with the same tweet_ids already exists
    cursor.execute("""
        SELECT id FROM summaries
        WHERE tweet_ids = ?
        ORDER BY timestamp DESC
        LIMIT 1
    """, (tweet_ids_json,))
    
    existing = cursor.fetchone()
    
    if existing:
        # Update existing summary instead of creating duplicate
        # IMPORTANT: Preserve the original timestamp to maintain chronological accuracy
        # Only update the summary content, not the timestamp
        summary_id = existing[0]
        cursor.execute("""
            UPDATE summaries
            SET summary = ?
            WHERE id = ?
        """, (summary, summary_id))
        print(f"[INFO] Updated existing summary {summary_id} with same tweet_ids (avoiding duplicate, preserving original timestamp)")
    else:
        # Create new summary
        cursor.execute("""
            INSERT INTO summaries (timestamp, summary, tweet_ids)
            VALUES (?, ?, ?)
        """, (generation_timestamp, summary, tweet_ids_json))
        summary_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return summary_id


def get_latest_summary() -> Optional[Dict]:
    """Get the most recent summary."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, timestamp, summary, tweet_ids, created_at
        FROM summaries
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "timestamp": row[1],
            "summary": row[2],
            "tweet_ids": json.loads(row[3]),
            "created_at": row[4]
        }
    return None


def get_summaries(limit: int = 10, offset: int = 0) -> List[Dict]:
    """
    Get paginated summaries, ordered by timestamp (newest first).
    
    Args:
        limit: Number of summaries to return
        offset: Number of summaries to skip
    
    Returns:
        List of summary dictionaries
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, timestamp, summary, tweet_ids, created_at
        FROM summaries
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": row[0],
            "timestamp": row[1],
            "summary": row[2],
            "tweet_ids": json.loads(row[3]),
            "created_at": row[4]
        }
        for row in rows
    ]


def get_summary_count() -> int:
    """Get total number of summaries in database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM summaries")
    count = cursor.fetchone()[0]
    conn.close()
    
    return count


# ============================================================================
# Accounts Management Functions
# ============================================================================

def get_all_accounts() -> List[Dict]:
    """Get all accounts from database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT handle, username, created_at, updated_at
        FROM accounts
        ORDER BY created_at ASC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "handle": row[0],
            "username": row[1],
            "created_at": row[2],
            "updated_at": row[3]
        }
        for row in rows
    ]


def add_account_to_db(handle: str, username: Optional[str] = None) -> bool:
    """
    Add an account to the database.
    Returns True if added, False if already exists.
    """
    handle = handle.strip().lstrip('@').lower()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO accounts (handle, username)
            VALUES (?, ?)
        """, (handle, username))
        
        # Initialize tracking for new account
        cursor.execute("""
            INSERT INTO account_tracking (handle)
            VALUES (?)
        """, (handle,))
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Account already exists
        conn.close()
        return False


def update_account_username_in_db(handle: str, username: str) -> None:
    """Update username for an account."""
    handle = handle.strip().lstrip('@').lower()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE accounts
        SET username = ?, updated_at = CURRENT_TIMESTAMP
        WHERE handle = ?
    """, (username, handle))
    
    conn.commit()
    conn.close()


def remove_account_from_db(handle: str) -> bool:
    """
    Remove an account from database.
    Returns True if removed, False if not found.
    """
    handle = handle.strip().lstrip('@').lower()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM account_tracking WHERE handle = ?", (handle,))
    cursor.execute("DELETE FROM accounts WHERE handle = ?", (handle,))
    
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return deleted


# ============================================================================
# Account Tracking Functions
# ============================================================================

def get_account_tracking(handle: str) -> Optional[Dict]:
    """Get tracking information for an account."""
    handle = handle.strip().lstrip('@').lower()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT handle, last_tweet_id, last_fetch_timestamp_utc, last_summary_id, updated_at
        FROM account_tracking
        WHERE handle = ?
    """, (handle,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "handle": row[0],
            "last_tweet_id": row[1],
            "last_fetch_timestamp_utc": row[2],
            "last_summary_id": row[3],
            "updated_at": row[4]
        }
    return None


def update_account_tracking(handle: str, last_tweet_id: Optional[str] = None, 
                           last_fetch_timestamp_utc: Optional[str] = None,
                           last_summary_id: Optional[int] = None) -> None:
    """Update tracking information for an account."""
    handle = handle.strip().lstrip('@').lower()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Build update query dynamically based on provided values
    updates = []
    params = []
    
    if last_tweet_id is not None:
        updates.append("last_tweet_id = ?")
        params.append(last_tweet_id)
    
    if last_fetch_timestamp_utc is not None:
        updates.append("last_fetch_timestamp_utc = ?")
        params.append(last_fetch_timestamp_utc)
    
    if last_summary_id is not None:
        updates.append("last_summary_id = ?")
        params.append(last_summary_id)
    
    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(handle)
        
        query = f"UPDATE account_tracking SET {', '.join(updates)} WHERE handle = ?"
        cursor.execute(query, params)
        
        # If no tracking record exists, create one
        if cursor.rowcount == 0:
            cursor.execute("""
                INSERT INTO account_tracking (handle, last_tweet_id, last_fetch_timestamp_utc, last_summary_id)
                VALUES (?, ?, ?, ?)
            """, (handle, last_tweet_id, last_fetch_timestamp_utc, last_summary_id))
    
    conn.commit()
    conn.close()


def get_latest_summary_for_account(handle: str) -> Optional[str]:
    """
    Get the latest summary text for an account by finding the most recent summary
    that contains tweets from this account.
    """
    handle = handle.strip().lstrip('@').lower()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get all summaries and check which ones contain tweets from this account
    cursor.execute("""
        SELECT id, timestamp, summary, tweet_ids
        FROM summaries
        ORDER BY timestamp DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    # Check each summary's tweet_ids to see if any belong to this account
    # Note: We'd need tweet data to check account ownership, but for now,
    # we'll return the most recent summary. This can be improved later.
    if rows:
        # Return the most recent summary
        # In a real implementation, we'd filter by account handle in tweet metadata
        return rows[0][2]  # Return summary text
    
    return None


# ============================================================================
# Scheduler Logs Functions
# ============================================================================

def log_scheduler_event(account_handle: Optional[str], fetch_type: Optional[str],
                       status: str, error_message: Optional[str] = None,
                       retry_count: int = 0, tweets_fetched: Optional[int] = None,
                       summary_generated: Optional[bool] = None) -> int:
    """Log a scheduler event to the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO scheduler_logs 
        (account_handle, fetch_type, status, error_message, retry_count, tweets_fetched, summary_generated)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (account_handle, fetch_type, status, error_message, retry_count, tweets_fetched, summary_generated))
    
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return log_id


def remove_duplicate_summaries() -> Dict:
    """
    Remove duplicate summaries that have the same tweet_ids.
    Keeps the newest summary for each unique set of tweet_ids.
    
    Returns:
        Dict with counts of duplicates removed
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get all summaries grouped by tweet_ids
    cursor.execute("""
        SELECT id, tweet_ids, timestamp
        FROM summaries
        ORDER BY timestamp DESC
    """)
    
    all_summaries = cursor.fetchall()
    
    # Track seen tweet_ids sets and duplicates to remove
    seen_tweet_ids = {}
    duplicates_to_remove = []
    
    for summary_id, tweet_ids_json, timestamp in all_summaries:
        # Normalize tweet_ids for comparison
        try:
            tweet_ids = json.loads(tweet_ids_json)
            normalized_tweet_ids = tuple(sorted(set(str(tid) for tid in tweet_ids)))
        except:
            # Skip if can't parse
            continue
        
        if normalized_tweet_ids in seen_tweet_ids:
            # This is a duplicate - mark for removal
            duplicates_to_remove.append(summary_id)
        else:
            # First time seeing this set of tweet_ids - keep it
            seen_tweet_ids[normalized_tweet_ids] = summary_id
    
    # Remove duplicates
    removed_count = 0
    for summary_id in duplicates_to_remove:
        cursor.execute("DELETE FROM summaries WHERE id = ?", (summary_id,))
        removed_count += 1
    
    conn.commit()
    conn.close()
    
    return {
        "duplicates_removed": removed_count,
        "unique_summaries": len(seen_tweet_ids),
        "total_before": len(all_summaries)
    }


def get_scheduler_logs(limit: int = 50, offset: int = 0, 
                       account_handle: Optional[str] = None) -> List[Dict]:
    """Get scheduler logs, optionally filtered by account."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if account_handle:
        cursor.execute("""
            SELECT id, timestamp, account_handle, fetch_type, status, error_message,
                   retry_count, tweets_fetched, summary_generated
            FROM scheduler_logs
            WHERE account_handle = ?
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """, (account_handle, limit, offset))
    else:
        cursor.execute("""
            SELECT id, timestamp, account_handle, fetch_type, status, error_message,
                   retry_count, tweets_fetched, summary_generated
            FROM scheduler_logs
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": row[0],
            "timestamp": row[1],
            "account_handle": row[2],
            "fetch_type": row[3],
            "status": row[4],
            "error_message": row[5],
            "retry_count": row[6],
            "tweets_fetched": row[7],
            "summary_generated": row[8]
        }
        for row in rows
    ]


# ============================================================================
# Migration Functions
# ============================================================================

def migrate_from_state_json() -> Dict:
    """
    Migrate data from state.json to database.
    Returns migration report with counts of migrated items.
    """
    import json
    import os
    
    report = {
        "accounts_migrated": 0,
        "tracking_migrated": 0,
        "errors": []
    }
    
    state_file = "state.json"
    if not os.path.exists(state_file):
        report["errors"].append("state.json not found, nothing to migrate")
        return report
    
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
    except Exception as e:
        report["errors"].append(f"Failed to load state.json: {e}")
        return report
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Migrate accounts
    monitored_accounts = state.get("monitored_accounts", [])
    account_info = state.get("account_info", {})
    
    for handle in monitored_accounts:
        handle_lower = handle.strip().lstrip('@').lower()
        username = account_info.get(handle_lower, {}).get("username") if account_info.get(handle_lower) else None
        
        try:
            # Add account
            cursor.execute("""
                INSERT OR IGNORE INTO accounts (handle, username)
                VALUES (?, ?)
            """, (handle_lower, username))
            
            if cursor.rowcount > 0:
                report["accounts_migrated"] += 1
            
            # Initialize tracking if doesn't exist
            cursor.execute("""
                INSERT OR IGNORE INTO account_tracking (handle)
                VALUES (?)
            """, (handle_lower,))
            
        except Exception as e:
            report["errors"].append(f"Error migrating account {handle}: {e}")
    
    # Migrate session context (tracking data)
    session_context = state.get("session_context", {})
    for handle, context in session_context.items():
        handle_lower = handle.strip().lstrip('@').lower()
        last_tweet_id = context.get("last_tweet_id")
        
        # Note: We're NOT migrating previous_summary as per requirements
        # It will be fetched from summaries table when needed
        
        try:
            cursor.execute("""
                UPDATE account_tracking
                SET last_tweet_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE handle = ?
            """, (last_tweet_id, handle_lower))
            
            if cursor.rowcount > 0:
                report["tracking_migrated"] += 1
            else:
                # Create tracking record if it doesn't exist
                cursor.execute("""
                    INSERT INTO account_tracking (handle, last_tweet_id)
                    VALUES (?, ?)
                """, (handle_lower, last_tweet_id))
                report["tracking_migrated"] += 1
                
        except Exception as e:
            report["errors"].append(f"Error migrating tracking for {handle}: {e}")
    
    conn.commit()
    conn.close()
    
    return report


# ============================================================================
# News Likes and Thoughts Functions
# ============================================================================

def generate_news_hash(title: str, content: str, timestamp: str) -> str:
    """
    Generate unique hash for a news item based on title, content, and timestamp.
    
    Args:
        title: News item title
        content: News item content
        timestamp: News item timestamp
    
    Returns:
        SHA256 hash as hex string
    """
    combined = f"{title}|{content}|{timestamp}"
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()


def save_news_like(news_hash: str, title: str, content: str, timestamp: str, 
                   source_tags: List[Dict], tweet_ids: List[str]) -> bool:
    """
    Save a liked news item to the database.
    
    Args:
        news_hash: Unique hash for the news item
        title: News item title
        content: News item content
        timestamp: Original news timestamp
        source_tags: List of source tag dictionaries
        tweet_ids: List of tweet IDs
    
    Returns:
        True if saved successfully, False if already exists
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    source_tags_json = json.dumps(source_tags) if source_tags else None
    tweet_ids_json = json.dumps(tweet_ids) if tweet_ids else None
    
    try:
        cursor.execute("""
            INSERT INTO news_likes (news_hash, title, content, timestamp, source_tags, tweet_ids)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (news_hash, title, content, timestamp, source_tags_json, tweet_ids_json))
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Already liked
        conn.close()
        return False


def remove_news_like(news_hash: str) -> bool:
    """
    Remove a liked news item from the database.
    
    Args:
        news_hash: Unique hash for the news item
    
    Returns:
        True if removed, False if not found
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM news_likes WHERE news_hash = ?", (news_hash,))
    deleted = cursor.rowcount > 0
    
    conn.commit()
    conn.close()
    
    return deleted


def get_news_likes(limit: int = 10, offset: int = 0) -> List[Dict]:
    """
    Get paginated liked news items, ordered by liked_at (newest first).
    
    Args:
        limit: Number of items to return
        offset: Number of items to skip
    
    Returns:
        List of liked news item dictionaries
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, news_hash, title, content, timestamp, liked_at, source_tags, tweet_ids
        FROM news_likes
        ORDER BY liked_at DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": row[0],
            "news_hash": row[1],
            "title": row[2],
            "content": row[3],
            "timestamp": row[4],
            "liked_at": row[5],
            "source_tags": json.loads(row[6]) if row[6] else [],
            "tweet_ids": json.loads(row[7]) if row[7] else []
        }
        for row in rows
    ]


def get_news_likes_count() -> int:
    """Get total number of liked news items."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM news_likes")
    count = cursor.fetchone()[0]
    conn.close()
    
    return count


def save_news_thought(news_hash: str, thought: str, title: Optional[str] = None, 
                     content: Optional[str] = None, timestamp: Optional[str] = None,
                     source_tags: Optional[List[Dict]] = None, tweet_ids: Optional[List[str]] = None) -> bool:
    """
    Save or update a thought for a news item.
    
    Args:
        news_hash: Unique hash for the news item
        thought: Thought text
        title: News item title (optional, stored for display)
        content: News item content (optional, stored for display)
        timestamp: News item timestamp (optional, stored for display)
        source_tags: List of source tag dictionaries (optional)
        tweet_ids: List of tweet IDs (optional)
    
    Returns:
        True if saved successfully
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    source_tags_json = json.dumps(source_tags) if source_tags else None
    tweet_ids_json = json.dumps(tweet_ids) if tweet_ids else None
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(news_thoughts)")
    columns = [col[1] for col in cursor.fetchall()]
    has_title_column = 'title' in columns
    
    # Check if thought already exists
    cursor.execute("SELECT id FROM news_thoughts WHERE news_hash = ?", (news_hash,))
    existing = cursor.fetchone()
    
    print(f"[DEBUG] save_news_thought: hash={news_hash[:16]}..., title={title[:50] if title else 'None'}, has_title_column={has_title_column}, existing={existing is not None}", flush=True)
    
    if existing:
        # Update existing thought
        if has_title_column:
            # Always update title/content if provided (even if empty string)
            # Use the provided values, or keep existing if not provided
            if title is not None or content is not None or timestamp is not None:
                # Update with new data - use provided values or keep existing
                cursor.execute("""
                    UPDATE news_thoughts
                    SET thought = ?, 
                        title = CASE WHEN ? IS NOT NULL THEN ? ELSE title END,
                        content = CASE WHEN ? IS NOT NULL THEN ? ELSE content END,
                        timestamp = CASE WHEN ? IS NOT NULL THEN ? ELSE timestamp END,
                        source_tags = CASE WHEN ? IS NOT NULL THEN ? ELSE source_tags END,
                        tweet_ids = CASE WHEN ? IS NOT NULL THEN ? ELSE tweet_ids END,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE news_hash = ?
                """, (thought, title, title, content, content, timestamp, timestamp, 
                      source_tags_json, source_tags_json, tweet_ids_json, tweet_ids_json, news_hash))
            else:
                # Just update thought text
                cursor.execute("""
                    UPDATE news_thoughts
                    SET thought = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE news_hash = ?
                """, (thought, news_hash))
        else:
            # Old schema - just update thought
            cursor.execute("""
                UPDATE news_thoughts
                SET thought = ?, updated_at = CURRENT_TIMESTAMP
                WHERE news_hash = ?
            """, (thought, news_hash))
    else:
        # Create new thought
        if has_title_column:
            cursor.execute("""
                INSERT INTO news_thoughts (news_hash, thought, title, content, timestamp, source_tags, tweet_ids)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (news_hash, thought, title, content, timestamp, source_tags_json, tweet_ids_json))
        else:
            # Old schema - just insert thought
            cursor.execute("""
                INSERT INTO news_thoughts (news_hash, thought)
                VALUES (?, ?)
            """, (news_hash, thought))
    
    conn.commit()
    conn.close()
    
    return True


def get_news_thought(news_hash: str) -> Optional[str]:
    """
    Get thought for a specific news item.
    
    Args:
        news_hash: Unique hash for the news item
    
    Returns:
        Thought text if exists, None otherwise
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT thought FROM news_thoughts WHERE news_hash = ?", (news_hash,))
    row = cursor.fetchone()
    conn.close()
    
    return row[0] if row else None


def get_liked_status(news_hashes: List[str]) -> List[str]:
    """
    Get list of news hashes that are liked.
    
    Args:
        news_hashes: List of news hashes to check
    
    Returns:
        List of news hashes that are liked
    """
    if not news_hashes:
        return []
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create placeholders for IN clause
    placeholders = ','.join(['?'] * len(news_hashes))
    cursor.execute(f"""
        SELECT news_hash FROM news_likes
        WHERE news_hash IN ({placeholders})
    """, news_hashes)
    
    rows = cursor.fetchall()
    conn.close()
    
    return [row[0] for row in rows]


def get_all_news_thoughts(limit: int = 20, offset: int = 0) -> List[Dict]:
    """
    Get all thoughts with their associated news item information.
    Uses stored title/content in news_thoughts table, falls back to news_likes if not stored.
    If still not found, tries to look up from merged items.
    
    Args:
        limit: Number of thoughts to return
        offset: Number of thoughts to skip
    
    Returns:
        List of thought dictionaries with news item info
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # First, check if the new columns exist
    cursor.execute("PRAGMA table_info(news_thoughts)")
    columns = [col[1] for col in cursor.fetchall()]
    has_title_column = 'title' in columns
    
    if has_title_column:
        # Get thoughts with stored title/content, fallback to news_likes if not stored
        cursor.execute("""
            SELECT 
                nt.id,
                nt.news_hash,
                nt.thought,
                nt.created_at,
                nt.updated_at,
                COALESCE(NULLIF(nt.title, ''), NULLIF(nl.title, ''), 'Unknown') as title,
                COALESCE(NULLIF(nt.content, ''), NULLIF(nl.content, ''), '') as content,
                COALESCE(NULLIF(nt.timestamp, ''), NULLIF(nl.timestamp, ''), '') as timestamp,
                COALESCE(NULLIF(nt.source_tags, ''), NULLIF(nl.source_tags, ''), '[]') as source_tags,
                COALESCE(NULLIF(nt.tweet_ids, ''), NULLIF(nl.tweet_ids, ''), '[]') as tweet_ids
            FROM news_thoughts nt
            LEFT JOIN news_likes nl ON nt.news_hash = nl.news_hash
            ORDER BY nt.updated_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
    else:
        # Fallback for old schema - only join with news_likes
        cursor.execute("""
            SELECT 
                nt.id,
                nt.news_hash,
                nt.thought,
                nt.created_at,
                nt.updated_at,
                COALESCE(nl.title, 'Unknown') as title,
                COALESCE(nl.content, '') as content,
                COALESCE(nl.timestamp, '') as timestamp,
                COALESCE(nl.source_tags, '[]') as source_tags,
                COALESCE(nl.tweet_ids, '[]') as tweet_ids
            FROM news_thoughts nt
            LEFT JOIN news_likes nl ON nt.news_hash = nl.news_hash
            ORDER BY nt.updated_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
    
    rows = cursor.fetchall()
    conn.close()
    
    print(f"[DEBUG] get_all_news_thoughts: Found {len(rows)} thoughts, has_title_column={has_title_column}", flush=True)
    
    result = []
    for row in rows:
        title = row[5] if len(row) > 5 and row[5] and row[5] != 'Unknown' else None
        content = row[6] if len(row) > 6 and row[6] else None
        timestamp = row[7] if len(row) > 7 and row[7] else None
        
        print(f"[DEBUG] get_all_news_thoughts: Processing thought hash={row[1][:16]}..., title from DB={title[:50] if title else 'None'}", flush=True)
        
        # If title is still Unknown or None, try to look it up from merged items
        if not title or title == 'Unknown':
            print(f"[DEBUG] Title is Unknown/None, looking up from merged items for hash {row[1][:16]}...", flush=True)
            # Try to find the news item by hash from merged items
            # This requires importing the summary parser
            try:
                from summary_parser import parse_news_items, parse_trades_items
                from database import get_summaries
                import os
                
                # Get all summaries and parse to find matching hash
                all_summaries = get_summaries(limit=1000, offset=0)
                tweets_data = None
                if os.path.exists("test_tweets_data.json"):
                    try:
                        with open("test_tweets_data.json", "r", encoding="utf-8") as f:
                            import json
                            tweets_data = json.load(f)
                    except:
                        pass
                
                news_hash_to_find = row[1]
                found_item = None
                
                for summary in all_summaries:
                    news_items = parse_news_items(
                        summary["summary"],
                        summary["tweet_ids"],
                        summary["timestamp"],
                        tweets_data
                    )
                    trades_items = parse_trades_items(
                        summary["summary"],
                        summary["tweet_ids"],
                        summary["timestamp"],
                        tweets_data
                    )
                    
                    # Check if any item matches the hash
                    from database import generate_news_hash
                    for item in news_items + trades_items:
                        item_hash = generate_news_hash(
                            item.get("title", ""),
                            item.get("content", ""),
                            item.get("timestamp", "")
                        )
                        if item_hash == news_hash_to_find:
                            found_item = item
                            break
                    
                    if found_item:
                        break
                
                if found_item:
                    title = found_item.get("title", "Unknown")
                    content = found_item.get("content", "")
                    timestamp = found_item.get("timestamp", "")
                    source_tags = found_item.get("source_tags", [])
                    tweet_ids = found_item.get("tweet_ids", [])
                else:
                    title = title or "Unknown"
                    source_tags = []
                    tweet_ids = []
            except Exception as e:
                print(f"[DEBUG] Error looking up news item for hash {row[1]}: {e}", flush=True)
                import traceback
                traceback.print_exc()
                title = title or "Unknown"
                source_tags = []
                tweet_ids = []
        else:
            try:
                source_tags = json.loads(row[8]) if len(row) > 8 and row[8] else []
                tweet_ids = json.loads(row[9]) if len(row) > 9 and row[9] else []
            except Exception as e:
                print(f"[DEBUG] Error parsing source_tags/tweet_ids: {e}", flush=True)
                source_tags = []
                tweet_ids = []
        
        final_title = title or "Unknown"
        print(f"[DEBUG] Final result for thought {row[0]}: title={final_title[:50]}", flush=True)
        
        result.append({
            "id": row[0],
            "news_hash": row[1],
            "thought": row[2],
            "created_at": row[3],
            "updated_at": row[4],
            "title": final_title,
            "content": content or "",
            "timestamp": timestamp or "",
            "source_tags": source_tags,
            "tweet_ids": tweet_ids
        })
    
    print(f"[DEBUG] get_all_news_thoughts: Returning {len(result)} thoughts", flush=True)
    return result


def get_news_thoughts_count() -> int:
    """Get total number of thoughts in database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM news_thoughts")
    count = cursor.fetchone()[0]
    conn.close()
    
    return count

