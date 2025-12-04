"""
Test script to verify Advanced Search API works correctly.
This script will:
1. Check if accounts have timestamps in database
2. Test Advanced Search API call directly
3. Compare results with since_id method
"""
import sys
import os
from datetime import datetime, timedelta
import pytz
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_account_tracking():
    """Check what tracking data exists for accounts."""
    print("\n=== Step 1: Check Account Tracking ===")
    try:
        from database import get_all_accounts, get_account_tracking
        from storage import get_monitored_account_handles
        
        handles = get_monitored_account_handles()
        print(f"Found {len(handles)} monitored accounts")
        
        tracking_info = []
        for handle in handles:
            tracking = get_account_tracking(handle)
            if tracking:
                has_timestamp = bool(tracking.get('last_fetch_timestamp_utc'))
                has_tweet_id = bool(tracking.get('last_tweet_id'))
                tracking_info.append({
                    'handle': handle,
                    'has_timestamp': has_timestamp,
                    'has_tweet_id': has_tweet_id,
                    'timestamp': tracking.get('last_fetch_timestamp_utc'),
                    'tweet_id': tracking.get('last_tweet_id')
                })
                print(f"  {handle}:")
                print(f"    - Has timestamp: {has_timestamp}")
                print(f"    - Has tweet_id: {has_tweet_id}")
                if has_timestamp:
                    print(f"    - Timestamp: {tracking.get('last_fetch_timestamp_utc')}")
                if has_tweet_id:
                    print(f"    - Tweet ID: {tracking.get('last_tweet_id')}")
        
        return tracking_info
    except Exception as e:
        print(f"[ERROR] Failed to check tracking: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_advanced_search_directly():
    """Test Advanced Search API directly."""
    print("\n=== Step 2: Test Advanced Search API Directly ===")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
    TWITTER_API_BASE = "https://api.twitterapi.io"
    
    if not TWITTER_API_KEY:
        print("[ERROR] TWITTER_API_KEY not found in environment")
        return None
    
    # Test with a known account
    test_handle = "hhuang"
    
    # Use timestamp from 1 hour ago
    since_dt = datetime.now(pytz.UTC) - timedelta(hours=1)
    since_str = since_dt.strftime("%Y-%m-%d_%H:%M:%S_UTC")
    
    until_dt = datetime.now(pytz.UTC)
    until_str = until_dt.strftime("%Y-%m-%d_%H:%M:%S_UTC")
    
    query = f"from:{test_handle} since:{since_str} until:{until_str} include:nativeretweets"
    
    print(f"Testing Advanced Search API:")
    print(f"  Handle: {test_handle}")
    print(f"  Query: {query}")
    print(f"  Time window: {since_str} to {until_str}")
    
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
            print("\n  Making API request...")
            response = client.get(url, headers=headers, params=params, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            
            print(f"  Response status: {response.status_code}")
            print(f"  API status: {data.get('status', 'unknown')}")
            
            if data.get("status") == "error":
                error_msg = data.get("msg", data.get("message", "Unknown error"))
                print(f"  [ERROR] API returned error: {error_msg}")
                return None
            
            tweets = data.get("tweets", [])
            print(f"  [SUCCESS] Found {len(tweets)} tweets")
            
            if tweets:
                print(f"\n  Sample tweet:")
                sample = tweets[0]
                print(f"    ID: {sample.get('id_str', sample.get('id'))}")
                print(f"    Text: {sample.get('text', '')[:100]}...")
                print(f"    Created: {sample.get('createdAt', 'N/A')}")
            
            return {
                'success': True,
                'tweet_count': len(tweets),
                'tweets': tweets,
                'response': data
            }
    except Exception as e:
        print(f"  [ERROR] API call failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def simulate_refresh_flow():
    """Simulate what happens when refresh button is clicked."""
    print("\n=== Step 3: Simulate Refresh Flow ===")
    
    try:
        from storage import get_monitored_account_handles, get_session_context
        from main import fetch_tweets_hybrid
        
        handles = get_monitored_account_handles()
        if not handles:
            print("[ERROR] No accounts found")
            return
        
        test_handle = handles[0]
        print(f"Testing with account: {test_handle}")
        
        # Get context (what refresh endpoint would get)
        context = get_session_context(test_handle)
        last_tweet_id = context.get("last_tweet_id")
        last_fetch_timestamp_utc = context.get("last_fetch_timestamp_utc")
        
        print(f"\nContext retrieved:")
        print(f"  last_tweet_id: {last_tweet_id}")
        print(f"  last_fetch_timestamp_utc: {last_fetch_timestamp_utc}")
        
        if last_fetch_timestamp_utc:
            print(f"\n[INFO] Advanced Search will be attempted first (primary method)")
            print(f"  Using timestamp: {last_fetch_timestamp_utc}")
        elif last_tweet_id:
            print(f"\n[INFO] Fallback method will be used (since_id)")
            print(f"  Using tweet_id: {last_tweet_id}")
        else:
            print(f"\n[INFO] First fetch - will use default time window")
        
        print(f"\n[NOTE] To actually test the fetch, you would need:")
        print(f"  1. A valid TWITTER_API_KEY")
        print(f"  2. API credits available")
        print(f"  3. Run: python -c \"from main import fetch_tweets_hybrid; print(fetch_tweets_hybrid('{test_handle}', '{last_tweet_id}', '{last_fetch_timestamp_utc}'))\"")
        
    except Exception as e:
        print(f"[ERROR] Simulation failed: {e}")
        import traceback
        traceback.print_exc()


def add_test_timestamp():
    """Add a test timestamp to an account for testing."""
    print("\n=== Step 4: Add Test Timestamp (Optional) ===")
    
    try:
        from database import update_account_tracking
        from storage import get_monitored_account_handles
        
        handles = get_monitored_account_handles()
        if not handles:
            print("[ERROR] No accounts found")
            return
        
        test_handle = handles[0]
        
        # Set timestamp to 1 hour ago (so Advanced Search will fetch recent tweets)
        test_timestamp = (datetime.now(pytz.UTC) - timedelta(hours=1)).isoformat()
        
        print(f"Adding test timestamp to {test_handle}:")
        print(f"  Timestamp: {test_timestamp}")
        
        update_account_tracking(
            test_handle,
            last_fetch_timestamp_utc=test_timestamp
        )
        
        print(f"[SUCCESS] Test timestamp added")
        print(f"\nNow when you click refresh, Advanced Search will be used!")
        
    except Exception as e:
        print(f"[ERROR] Failed to add timestamp: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests."""
    print("=" * 70)
    print("Advanced Search API Test Script")
    print("=" * 70)
    print("\nThis script will help you verify Advanced Search API works.")
    print("It checks your current setup and can test the API directly.\n")
    
    # Step 1: Check tracking
    tracking_info = check_account_tracking()
    
    # Step 2: Test Advanced Search API (if API key available)
    print("\n" + "=" * 70)
    api_result = test_advanced_search_directly()
    
    # Step 3: Simulate refresh flow
    print("\n" + "=" * 70)
    simulate_refresh_flow()
    
    # Step 4: Offer to add test timestamp
    print("\n" + "=" * 70)
    if tracking_info:
        accounts_without_timestamp = [t for t in tracking_info if not t['has_timestamp']]
        if accounts_without_timestamp:
            print(f"\n[INFO] Found {len(accounts_without_timestamp)} accounts without timestamps")
            print("These accounts will use fallback (since_id) method.")
            print("\nTo test Advanced Search, you can:")
            print("  1. Run this script with --add-timestamp flag")
            print("  2. Or manually add timestamp via database")
    
    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    
    if api_result and api_result.get('success'):
        print("[SUCCESS] Advanced Search API is working!")
        print(f"  Found {api_result['tweet_count']} tweets")
    else:
        print("[INFO] Advanced Search API test skipped or failed")
        print("  This could be due to:")
        print("    - Missing API key")
        print("    - No API credits")
        print("    - Network issues")
    
    print("\n[INFO] When you click refresh button:")
    if tracking_info:
        accounts_with_timestamp = [t for t in tracking_info if t['has_timestamp']]
        if accounts_with_timestamp:
            print(f"  - {len(accounts_with_timestamp)} account(s) will use Advanced Search (primary)")
        accounts_without_timestamp = [t for t in tracking_info if not t['has_timestamp']]
        if accounts_without_timestamp:
            print(f"  - {len(accounts_without_timestamp)} account(s) will use since_id fallback")
    else:
        print("  - All accounts will use since_id method (no timestamps found)")
    
    print("\n[RECOMMENDATION] To fully test Advanced Search:")
    print("  1. Ensure accounts have last_fetch_timestamp_utc in database")
    print("  2. Click refresh button")
    print("  3. Check logs for 'Advanced Search' messages")
    print("  4. Verify tweets are fetched correctly")


if __name__ == "__main__":
    import sys
    if "--add-timestamp" in sys.argv:
        add_test_timestamp()
    else:
        main()

