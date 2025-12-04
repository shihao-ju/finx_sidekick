"""
Test script to:
1. Set timestamp to 12 hours ago for hhuang
2. Test Advanced Search with 12-hour window
3. Compare results with since_id method
"""
import sys
import os
from datetime import datetime, timedelta
import pytz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def set_timestamp_12h_ago():
    """Set timestamp to 12 hours ago for hhuang."""
    print("\n=== Setting Timestamp to 12 Hours Ago ===")
    
    try:
        from database import update_account_tracking, get_account_tracking
        
        handle = "hhuang"
        
        # Get current tracking
        tracking_before = get_account_tracking(handle)
        print(f"Current timestamp: {tracking_before.get('last_fetch_timestamp_utc') if tracking_before else 'None'}")
        
        # Set timestamp to 12 hours ago
        timestamp_12h_ago = (datetime.now(pytz.UTC) - timedelta(hours=12)).isoformat()
        
        print(f"\nSetting timestamp to: {timestamp_12h_ago}")
        print(f"  (12 hours ago from now)")
        
        # Update tracking
        update_account_tracking(
            handle,
            last_fetch_timestamp_utc=timestamp_12h_ago
        )
        
        # Verify update
        tracking_after = get_account_tracking(handle)
        if tracking_after and tracking_after.get('last_fetch_timestamp_utc') == timestamp_12h_ago:
            print(f"[SUCCESS] Timestamp updated successfully")
            return timestamp_12h_ago
        else:
            print(f"[ERROR] Timestamp not updated correctly")
            return None
            
    except Exception as e:
        print(f"[ERROR] Failed to set timestamp: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_advanced_search_with_timestamp(timestamp_utc):
    """Test Advanced Search API with the given timestamp."""
    print("\n=== Testing Advanced Search with 12-Hour Window ===")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
    TWITTER_API_BASE = "https://api.twitterapi.io"
    
    if not TWITTER_API_KEY:
        print("[ERROR] TWITTER_API_KEY not found in environment")
        return None
    
    handle = "hhuang"
    
    # Parse timestamp
    dt = datetime.fromisoformat(timestamp_utc.replace('Z', '+00:00'))
    since_str = dt.strftime("%Y-%m-%d_%H:%M:%S_UTC")
    
    until_dt = datetime.now(pytz.UTC)
    until_str = until_dt.strftime("%Y-%m-%d_%H:%M:%S_UTC")
    
    query = f"from:{handle} since:{since_str} until:{until_str} include:nativeretweets"
    
    print(f"Query: {query}")
    print(f"Time window: {since_str} to {until_str}")
    
    # Calculate window size
    window_hours = (until_dt - dt).total_seconds() / 3600
    print(f"Window size: {window_hours:.2f} hours")
    
    import httpx
    
    url = f"{TWITTER_API_BASE}/twitter/tweet/advanced_search"
    headers = {
        "X-API-Key": TWITTER_API_KEY
    }
    
    params = {
        "query": query,
        "queryType": "Latest"
    }
    
    try:
        with httpx.Client() as client:
            print("\nMaking API request...")
            response = client.get(url, headers=headers, params=params, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            
            print(f"Response status: {response.status_code}")
            print(f"API status: {data.get('status', 'unknown')}")
            
            if data.get("status") == "error":
                error_msg = data.get("msg", data.get("message", "Unknown error"))
                print(f"[ERROR] API returned error: {error_msg}")
                return None
            
            tweets = data.get("tweets", [])
            print(f"\n[RESULT] Advanced Search found {len(tweets)} tweets")
            
            if tweets:
                print(f"\nSample tweets:")
                for i, tweet in enumerate(tweets[:5], 1):
                    tweet_id = tweet.get('id_str', tweet.get('id'))
                    created = tweet.get('createdAt', 'N/A')
                    text_preview = tweet.get('text', '')[:80] + '...' if len(tweet.get('text', '')) > 80 else tweet.get('text', '')
                    print(f"  {i}. ID: {tweet_id}, Created: {created}")
                    print(f"     Text: {text_preview}")
            else:
                print("\n[INFO] No tweets found in 12-hour window")
                print("This could mean:")
                print("  - Account didn't post in last 12 hours")
                print("  - API indexing delay")
                print("  - Time window issue")
            
            return {
                'success': True,
                'tweet_count': len(tweets),
                'tweets': tweets,
                'query': query,
                'window_hours': window_hours
            }
    except Exception as e:
        print(f"[ERROR] API call failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def compare_with_since_id():
    """Compare Advanced Search results with since_id method."""
    print("\n=== Comparing with since_id Method ===")
    
    try:
        from database import get_account_tracking
        from main import fetch_tweets
        
        handle = "hhuang"
        tracking = get_account_tracking(handle)
        last_tweet_id = tracking.get('last_tweet_id') if tracking else None
        
        if not last_tweet_id:
            print("[INFO] No last_tweet_id found, skipping comparison")
            return
        
        print(f"Using since_id: {last_tweet_id}")
        print("Fetching tweets via since_id method...")
        
        tweets = fetch_tweets(handle, last_tweet_id)
        
        print(f"[RESULT] since_id method found {len(tweets)} tweets")
        
        if tweets:
            print(f"\nSample tweets:")
            for i, tweet in enumerate(tweets[:5], 1):
                tweet_id = tweet.get('id_str', tweet.get('id'))
                created = tweet.get('createdAt', 'N/A')
                text_preview = tweet.get('text', '')[:80] + '...' if len(tweet.get('text', '')) > 80 else tweet.get('text', '')
                print(f"  {i}. ID: {tweet_id}, Created: {created}")
                print(f"     Text: {text_preview}")
        
    except Exception as e:
        print(f"[ERROR] Comparison failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run test."""
    print("=" * 70)
    print("Advanced Search 12-Hour Window Test")
    print("=" * 70)
    
    # Step 1: Set timestamp to 12 hours ago
    timestamp_12h = set_timestamp_12h_ago()
    
    if not timestamp_12h:
        print("\n[ERROR] Failed to set timestamp, aborting test")
        return
    
    # Step 2: Test Advanced Search
    result = test_advanced_search_with_timestamp(timestamp_12h)
    
    # Step 3: Compare with since_id method
    compare_with_since_id()
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    if result and result.get('success'):
        print(f"[SUCCESS] Advanced Search API is working!")
        print(f"  Found {result['tweet_count']} tweets in {result['window_hours']:.2f}-hour window")
        
        if result['tweet_count'] > 0:
            print("\n[CONCLUSION] Advanced Search works with 12-hour window!")
            print("The issue was likely the 1-hour window being too narrow.")
        else:
            print("\n[INFO] Advanced Search returned 0 tweets even with 12-hour window")
            print("This suggests:")
            print("  - Account may not have posted in last 12 hours")
            print("  - Or API indexing delay")
            print("  - Check since_id method results above for comparison")
    else:
        print("[ERROR] Advanced Search test failed")
    
    print("\n[NOTE] Timestamp has been updated to 12 hours ago.")
    print("Next refresh will use Advanced Search with this 12-hour window.")


if __name__ == "__main__":
    main()

