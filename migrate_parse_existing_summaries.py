"""
Migration script to parse existing summaries and populate parsed_news_items and parsed_trades_items tables.
This script should be run once after adding the pre-computed parsed items feature.
"""
import os
import json
from database import get_summaries, save_parsed_news_items, save_parsed_trades_items
from summary_parser import parse_news_items, parse_trades_items

def migrate_existing_summaries():
    """Parse all existing summaries and save parsed items to database."""
    print("[INFO] Starting migration: parsing existing summaries...")
    
    # Load tweets data for timestamp lookup (optional)
    tweets_data = None
    if os.path.exists("test_tweets_data.json"):
        try:
            with open("test_tweets_data.json", "r", encoding="utf-8") as f:
                tweets_data = json.load(f)
            print("[INFO] Loaded tweets_data.json for timestamp lookup")
        except Exception as e:
            print(f"[WARNING] Could not load tweets_data.json: {e}")
    
    # Get all summaries
    all_summaries = get_summaries(limit=10000, offset=0)  # Get all summaries
    total = len(all_summaries)
    
    print(f"[INFO] Found {total} summaries to parse")
    
    success_count = 0
    error_count = 0
    
    for i, summary in enumerate(all_summaries, 1):
        summary_id = summary["id"]
        summary_text = summary["summary"]
        tweet_ids = summary["tweet_ids"]
        timestamp = summary["timestamp"]
        
        try:
            # Parse news items
            news_items = parse_news_items(summary_text, tweet_ids, timestamp, tweets_data)
            if news_items:
                save_parsed_news_items(summary_id, news_items)
            
            # Parse trades items
            trades_items = parse_trades_items(summary_text, tweet_ids, timestamp, tweets_data)
            if trades_items:
                save_parsed_trades_items(summary_id, trades_items)
            
            success_count += 1
            
            if i % 10 == 0:
                print(f"[INFO] Progress: {i}/{total} summaries processed ({success_count} success, {error_count} errors)")
        
        except Exception as e:
            error_count += 1
            print(f"[ERROR] Failed to parse summary {summary_id}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"[INFO] Migration complete!")
    print(f"[INFO] Successfully parsed: {success_count}/{total}")
    print(f"[INFO] Errors: {error_count}/{total}")

if __name__ == "__main__":
    migrate_existing_summaries()

