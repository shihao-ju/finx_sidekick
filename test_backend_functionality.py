"""
Test backend functionality using saved tweet data.
This file loads test data and tests the generate_summary function.
"""
import json
import os
import sys
from dotenv import load_dotenv
from main import generate_summary

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv(dotenv_path=".env", override=True)

def load_test_tweets():
    """Load saved tweet data from test_tweets_data.json"""
    test_data_file = "test_tweets_data.json"
    
    if not os.path.exists(test_data_file):
        print(f"[ERROR] Test data file not found: {test_data_file}")
        print("Please run 'Refresh Market Intel' first to generate test data.")
        return None
    
    try:
        with open(test_data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"[OK] Loaded test data:")
        print(f"  Handle: {data.get('handle')}")
        print(f"  Tweet count: {data.get('tweet_count')}")
        print(f"  Fetch timestamp: {data.get('fetch_timestamp')}")
        print(f"  Last tweet ID: {data.get('last_tweet_id')}")
        return data
    except Exception as e:
        print(f"[ERROR] Failed to load test data: {e}")
        return None

def test_generate_summary():
    """Test the generate_summary function with saved tweet data"""
    print("\n" + "="*60)
    print("Testing generate_summary function")
    print("="*60 + "\n")
    
    # Load test data
    test_data = load_test_tweets()
    if not test_data:
        return
    
    tweets = test_data.get("tweets", [])
    handle = test_data.get("handle", "unknown")
    
    if not tweets:
        print("[ERROR] No tweets in test data!")
        return
    
    print(f"[TEST] Testing with {len(tweets)} tweets from @{handle}\n")
    
    # Test with no previous summary (first time)
    print("-" * 60)
    print("Test 1: Generate summary with no previous summary")
    print("-" * 60)
    try:
        summary = generate_summary(
            previous_summary="",
            new_tweets=tweets,
            account_handles=[handle]
        )
        print("\n[OK] Summary generated successfully!")
        print("\nGenerated Summary:")
        print("=" * 60)
        print(summary)
        print("=" * 60)
    except Exception as e:
        print(f"\n[ERROR] Failed to generate summary: {e}")
        import traceback
        traceback.print_exc()
    
    # Test with a previous summary (update scenario)
    print("\n\n" + "-" * 60)
    print("Test 2: Update existing summary with new tweets")
    print("-" * 60)
    previous_summary = """@lord_fed: Previous summary from last check.
    
Buy/Sell Signals: None
Key Events: Market analysis ongoing
Market Sentiment: Neutral"""
    
    try:
        updated_summary = generate_summary(
            previous_summary=previous_summary,
            new_tweets=tweets[:5],  # Use first 5 tweets for update test
            account_handles=[handle]
        )
        print("\n[OK] Updated summary generated successfully!")
        print("\nUpdated Summary:")
        print("=" * 60)
        print(updated_summary)
        print("=" * 60)
    except Exception as e:
        print(f"\n[ERROR] Failed to generate updated summary: {e}")
        import traceback
        traceback.print_exc()
    
    # Test with empty tweets (no new tweets scenario)
    print("\n\n" + "-" * 60)
    print("Test 3: Generate summary with no new tweets")
    print("-" * 60)
    try:
        no_tweets_summary = generate_summary(
            previous_summary=previous_summary,
            new_tweets=[],
            account_handles=[handle]
        )
        print("\n[OK] Summary generated successfully (no new tweets)!")
        print("\nSummary:")
        print("=" * 60)
        print(no_tweets_summary)
        print("=" * 60)
    except Exception as e:
        print(f"\n[ERROR] Failed to generate summary: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_generate_summary()

