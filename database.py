"""
SQLite database for storing summaries with timestamps and tweet metadata.
"""
import sqlite3
import json
from typing import List, Dict, Optional
from datetime import datetime
import os

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
    
    # Create index on timestamp for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp ON summaries(timestamp)
    """)
    
    conn.commit()
    conn.close()


def save_summary(summary: str, tweet_ids: List[str], generation_timestamp: Optional[str] = None) -> int:
    """
    Save a summary to the database.
    
    Args:
        summary: The markdown summary text
        tweet_ids: List of tweet IDs used in this summary
        generation_timestamp: ISO format timestamp (defaults to now)
    
    Returns:
        The ID of the saved summary
    """
    if generation_timestamp is None:
        generation_timestamp = datetime.now().isoformat()
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO summaries (timestamp, summary, tweet_ids)
        VALUES (?, ?, ?)
    """, (generation_timestamp, summary, json.dumps(tweet_ids)))
    
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

