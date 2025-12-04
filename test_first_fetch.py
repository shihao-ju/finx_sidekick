"""
Test to simulate a first fetch scenario
"""
import json
import os
import sys

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def test_first_fetch_scenario():
    """Simulate what should happen on first fetch"""
    print("="*70)
    print("Simulating First Fetch Scenario")
    print("="*70 + "\n")
    
    # Load test data
    with open("test_tweets_data.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    tweets = data.get("tweets", [])
    since_id_used = data.get("since_id_used_for_filtering") or data.get("last_tweet_id")  # Fallback for old format
    last_tweet_id_in_file = data.get("last_tweet_id")
    
    print(f"Test Data Analysis:")
    print(f"  Handle: {data.get('handle')}")
    print(f"  Total tweets fetched: {len(tweets)}")
    print(f"  since_id_used_for_filtering: {since_id_used}")
    print(f"  last_tweet_id in file: {last_tweet_id_in_file}")
    print()
    
    if tweets:
        newest_tweet_id = str(tweets[0].get("id_str") or tweets[0].get("id"))
        oldest_tweet_id = str(tweets[-1].get("id_str") or tweets[-1].get("id"))
        print(f"  Newest tweet ID (first in list): {newest_tweet_id}")
        print(f"  Oldest tweet ID (last in list): {oldest_tweet_id}")
        print()
    
    # Check state.json
    if os.path.exists("state.json"):
        with open("state.json", 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        handle = data.get("handle")
        state_last_tweet_id = None
        if handle in state.get("session_context", {}):
            state_last_tweet_id = state["session_context"][handle].get("last_tweet_id")
        
        print(f"State Analysis:")
        print(f"  last_tweet_id in state.json: {state_last_tweet_id}")
        print()
        
        # Compare
        print("="*70)
        print("Analysis:")
        print("="*70)
        
        if since_id_used is None:
            print("[OK] This WAS a first fetch (since_id was None)")
        else:
            print(f"[INFO] This was NOT a first fetch (since_id was {since_id_used})")
            print(f"  This means tweets were filtered using this since_id")
        
        if tweets:
            newest_id_int = int(newest_tweet_id)
            since_id_int = int(since_id_used) if since_id_used else None
            
            if since_id_int and newest_id_int < since_id_int:
                print(f"\n[OK] Filtering worked correctly:")
                print(f"  All {len(tweets)} fetched tweets are OLDER than since_id")
                print(f"  This means these tweets were already processed before")
            elif since_id_int and newest_id_int > since_id_int:
                print(f"\n[OK] Filtering worked correctly:")
                print(f"  Fetched {len(tweets)} NEW tweets (newer than since_id)")
            elif since_id_int == newest_id_int:
                print(f"\n[OK] Filtering worked correctly:")
                print(f"  since_id matches newest tweet (boundary case)")
        
        if state_last_tweet_id:
            state_id_int = int(state_last_tweet_id)
            newest_id_int = int(newest_tweet_id)
            
            if state_id_int == newest_id_int:
                print(f"\n[OK] State was updated correctly:")
                print(f"  State has newest tweet ID: {state_last_tweet_id}")
            else:
                print(f"\n[ERROR] State mismatch:")
                print(f"  State has: {state_last_tweet_id}")
                print(f"  Should be: {newest_tweet_id}")
        
        if last_tweet_id_in_file:
            file_id_int = int(last_tweet_id_in_file)
            newest_id_int = int(newest_tweet_id)
            
            if file_id_int == newest_id_int:
                print(f"\n[OK] test_tweets_data.json has correct last_tweet_id")
            else:
                print(f"\n[ERROR] test_tweets_data.json has WRONG last_tweet_id:")
                print(f"  File has: {last_tweet_id_in_file}")
                print(f"  Should be: {newest_tweet_id}")
                print(f"  (This was the bug - file was saving old since_id instead of new last_tweet_id)")

if __name__ == "__main__":
    test_first_fetch_scenario()

