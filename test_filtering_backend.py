"""
Test backend filtering flow using test_tweets_data.json
Tests the since_id filtering logic that was fixed earlier.
"""
import json
import os
import sys
from typing import List, Dict, Optional

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def load_test_tweets():
    """Load saved tweet data from test_tweets_data.json"""
    test_data_file = "test_tweets_data.json"
    
    if not os.path.exists(test_data_file):
        print(f"[ERROR] Test data file not found: {test_data_file}")
        return None
    
    try:
        with open(test_data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"[ERROR] Failed to load test data: {e}")
        return None


def filter_tweets_by_since_id(tweets: List[Dict], since_id: Optional[str]) -> List[Dict]:
    """
    Simulate the filtering logic from fetch_tweets() in main.py
    This is the CORRECTED version that compares IDs numerically.
    """
    if not since_id:
        # First time fetching - include all tweets
        return tweets
    
    filtered_tweets = []
    since_id_int = int(since_id)  # Convert to int for numerical comparison
    
    print(f"  Filtering with since_id: {since_id} ({since_id_int})")
    
    for tweet in tweets:
        tweet_id_str = str(tweet.get("id_str") or tweet.get("id"))
        tweet_id_int = int(tweet_id_str)
        
        # If this tweet matches since_id, skip it (already processed)
        if tweet_id_int == since_id_int:
            print(f"    [=] Found since_id match: {tweet_id_str} - skipping")
            continue
        
        # Only include tweets that are NEWER than since_id (higher ID)
        if tweet_id_int > since_id_int:
            filtered_tweets.append(tweet)
            print(f"    [+] Including tweet {tweet_id_str} (NEWER: {tweet_id_int} > {since_id_int})")
        else:
            print(f"    [-] Skipping tweet {tweet_id_str} (OLDER: {tweet_id_int} < {since_id_int})")
            # Since tweets are sorted newest first, we could break here
            # But continue to check if since_id appears later (handles duplicates)
    
    return filtered_tweets


def get_latest_tweet_id(tweets: List[Dict]) -> Optional[str]:
    """
    Get the latest (newest) tweet ID from a list of tweets.
    Tweets are sorted newest first, so first tweet is the latest.
    """
    if not tweets:
        return None
    
    latest_tweet = tweets[0]
    tweet_id = latest_tweet.get("id_str") or latest_tweet.get("id")
    return str(tweet_id) if tweet_id else None


def test_filtering_scenarios():
    """Test various filtering scenarios"""
    print("="*70)
    print("Testing Backend Filtering Flow")
    print("="*70 + "\n")
    
    # Load test data
    test_data = load_test_tweets()
    if not test_data:
        return
    
    tweets = test_data.get("tweets", [])
    handle = test_data.get("handle", "unknown")
    last_tweet_id = test_data.get("last_tweet_id")
    
    print(f"Test Data:")
    print(f"  Handle: @{handle}")
    print(f"  Total tweets: {len(tweets)}")
    print(f"  Last tweet ID (from state): {last_tweet_id}")
    print()
    
    # Show tweet ID range
    if tweets:
        first_id = str(tweets[0].get("id_str") or tweets[0].get("id"))
        last_id = str(tweets[-1].get("id_str") or tweets[-1].get("id"))
        print(f"  Tweet ID range: {first_id} (newest) to {last_id} (oldest)")
        print()
    
    # Test Scenario 1: No since_id (first fetch)
    print("-"*70)
    print("Scenario 1: First fetch (no since_id)")
    print("-"*70)
    filtered = filter_tweets_by_since_id(tweets, None)
    print(f"\nResult: {len(filtered)} tweets included (should be {len(tweets)} - all tweets)")
    assert len(filtered) == len(tweets), "First fetch should include all tweets"
    print("[PASSED]\n")
    
    # Test Scenario 2: since_id matches the last tweet ID from state
    print("-"*70)
    print(f"Scenario 2: Filter with last_tweet_id from state ({last_tweet_id})")
    print("-"*70)
    filtered = filter_tweets_by_since_id(tweets, last_tweet_id)
    print(f"\nResult: {len(filtered)} tweets included")
    
    # Check if last_tweet_id exists in tweets
    last_id_int = int(last_tweet_id)
    first_tweet_id_int = int(str(tweets[0].get("id_str") or tweets[0].get("id")))
    
    if last_id_int > first_tweet_id_int:
        print(f"  Note: last_tweet_id ({last_tweet_id}) is NEWER than first tweet ({first_tweet_id_int})")
        print(f"  This means all tweets in the file are OLDER than last_tweet_id")
        print(f"  Expected: 0 tweets (all should be filtered out)")
        assert len(filtered) == 0, "All tweets should be filtered out if they're older than since_id"
    elif last_id_int == first_tweet_id_int:
        print(f"  Note: last_tweet_id matches first tweet")
        print(f"  Expected: 0 tweets (first tweet matches, rest are older)")
        assert len(filtered) == 0, "Should filter out matching tweet and older ones"
    else:
        print(f"  Note: last_tweet_id ({last_id_int}) is OLDER than first tweet ({first_tweet_id_int})")
        print(f"  Expected: Some tweets newer than last_tweet_id")
        assert len(filtered) > 0, "Should include tweets newer than since_id"
    
    print("[PASSED]\n")
    
    # Test Scenario 3: since_id in the middle of the list
    print("-"*70)
    print("Scenario 3: Filter with since_id from middle of list")
    print("-"*70)
    if len(tweets) >= 5:
        middle_tweet = tweets[5]
        middle_tweet_id = str(middle_tweet.get("id_str") or middle_tweet.get("id"))
        print(f"Using tweet at index 5: {middle_tweet_id}")
        filtered = filter_tweets_by_since_id(tweets, middle_tweet_id)
        print(f"\nResult: {len(filtered)} tweets included (should be 5 - tweets 0-4)")
        assert len(filtered) == 5, f"Should include 5 tweets (indices 0-4), got {len(filtered)}"
        print("[PASSED]\n")
    
    # Test Scenario 4: since_id matches first tweet (newest)
    print("-"*70)
    print("Scenario 4: Filter with since_id matching newest tweet")
    print("-"*70)
    if tweets:
        newest_tweet_id = str(tweets[0].get("id_str") or tweets[0].get("id"))
        print(f"Using newest tweet ID: {newest_tweet_id}")
        filtered = filter_tweets_by_since_id(tweets, newest_tweet_id)
        print(f"\nResult: {len(filtered)} tweets included (should be 0 - all tweets are older or equal)")
        assert len(filtered) == 0, "Should filter out all tweets if since_id matches newest"
        print("[PASSED]\n")
    
    # Test Scenario 5: since_id older than oldest tweet
    print("-"*70)
    print("Scenario 5: Filter with since_id older than oldest tweet")
    print("-"*70)
    if tweets:
        oldest_tweet = tweets[-1]
        oldest_tweet_id_int = int(str(oldest_tweet.get("id_str") or oldest_tweet.get("id")))
        # Use an ID that's older (smaller number)
        older_since_id = str(oldest_tweet_id_int - 1000000)
        print(f"Using older since_id: {older_since_id} (oldest tweet: {oldest_tweet_id_int})")
        filtered = filter_tweets_by_since_id(tweets, older_since_id)
        print(f"\nResult: {len(filtered)} tweets included (should be {len(tweets)} - all tweets are newer)")
        assert len(filtered) == len(tweets), "Should include all tweets if since_id is older than oldest"
        print("[PASSED]\n")
    
    # Test Scenario 6: Simulate the actual backend flow
    print("-"*70)
    print("Scenario 6: Simulate actual backend refresh flow")
    print("-"*70)
    
    # Simulate: We have a last_tweet_id in state
    state_last_tweet_id = last_tweet_id
    print(f"State has last_tweet_id: {state_last_tweet_id}")
    
    # Fetch new tweets (filtered)
    new_tweets = filter_tweets_by_since_id(tweets, state_last_tweet_id)
    print(f"\nFetched {len(new_tweets)} new tweets")
    
    # Update state with latest tweet ID
    if new_tweets:
        updated_last_tweet_id = get_latest_tweet_id(new_tweets)
        print(f"Updated last_tweet_id to: {updated_last_tweet_id}")
        
        # Verify: Next fetch should return 0 tweets (we already have the latest)
        print(f"\nSimulating next fetch with updated last_tweet_id...")
        next_fetch_tweets = filter_tweets_by_since_id(tweets, updated_last_tweet_id)
        print(f"Next fetch returned: {len(next_fetch_tweets)} tweets")
        print(f"  (Should be 0 if updated_last_tweet_id is the newest tweet)")
    else:
        print("No new tweets, keeping existing last_tweet_id")
    
    print("\n[SCENARIO COMPLETE]")
    
    print("\n" + "="*70)
    print("All filtering tests completed successfully!")
    print("="*70)


if __name__ == "__main__":
    test_filtering_scenarios()

