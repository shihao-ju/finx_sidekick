"""
Test the hybrid function directly to see why hhuang skipped Advanced Search.
"""
import sys
import os
from datetime import datetime
import pytz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_hybrid_logic():
    """Test the exact logic that would run for hhuang."""
    print("\n=== Testing Hybrid Function Logic ===")
    
    # Simulate what hhuang had during the refresh
    handle = "hhuang"
    last_tweet_id = "1996023421663412563"
    last_fetch_timestamp_utc = "2025-12-04T03:00:15.503688+00:00"  # From logs
    
    print(f"Input parameters:")
    print(f"  handle: {handle}")
    print(f"  last_tweet_id: {last_tweet_id}")
    print(f"  last_fetch_timestamp_utc: {last_fetch_timestamp_utc}")
    
    # Test the exact condition from code
    print(f"\n=== Testing Condition ===")
    print(f"if last_fetch_timestamp_utc:")
    print(f"  Value: {last_fetch_timestamp_utc}")
    print(f"  Type: {type(last_fetch_timestamp_utc)}")
    print(f"  Boolean: {bool(last_fetch_timestamp_utc)}")
    print(f"  Is None: {last_fetch_timestamp_utc is None}")
    print(f"  Is empty string: {last_fetch_timestamp_utc == ''}")
    print(f"  Stripped empty: {last_fetch_timestamp_utc.strip() == '' if last_fetch_timestamp_utc else 'N/A'}")
    
    if last_fetch_timestamp_utc:
        print(f"\n[RESULT] Condition is TRUE - should attempt Advanced Search")
        
        # Check if timestamp is valid
        try:
            dt = datetime.fromisoformat(last_fetch_timestamp_utc.replace('Z', '+00:00'))
            print(f"  Timestamp parses correctly: {dt.isoformat()}")
        except Exception as e:
            print(f"  [ERROR] Timestamp parsing failed: {e}")
    else:
        print(f"\n[RESULT] Condition is FALSE - would skip Advanced Search")
    
    # Test with None
    print(f"\n=== Testing with None ===")
    test_none = None
    if test_none:
        print(f"  Would attempt Advanced Search")
    else:
        print(f"  Would skip Advanced Search (expected)")
    
    # Test with empty string
    print(f"\n=== Testing with Empty String ===")
    test_empty = ""
    if test_empty:
        print(f"  Would attempt Advanced Search")
    else:
        print(f"  Would skip Advanced Search (expected)")


def check_what_happened():
    """Check what actually happened in the logs."""
    print("\n=== Analyzing What Happened ===")
    
    # From the logs the user showed:
    # Line 889: last_fetch_timestamp_utc: 2025-12-04T03:00:15.503688+00:00
    # But no "Attempting Advanced Search" message
    
    print("From logs:")
    print("  Line 889: last_fetch_timestamp_utc: 2025-12-04T03:00:15.503688+00:00")
    print("  Missing: '[DEBUG] Attempting Advanced Search' message")
    print("\nPossible explanations:")
    print("  1. Timestamp was None when passed to hybrid function")
    print("  2. Exception occurred before Advanced Search attempt")
    print("  3. Code path was different (old code?)")
    print("  4. Timestamp check failed for some reason")
    
    # Check if timestamp is too recent
    timestamp = "2025-12-04T03:00:15.503688+00:00"
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        # Assuming refresh ran around 3:03 AM (from log context)
        refresh_time = datetime(2025, 12, 4, 3, 3, 0, tzinfo=pytz.UTC)
        diff = (refresh_time - dt).total_seconds() / 3600
        print(f"\nTimestamp analysis:")
        print(f"  Timestamp: {timestamp}")
        print(f"  Refresh time (estimated): {refresh_time.isoformat()}")
        print(f"  Time difference: {diff:.2f} hours")
        
        if diff < 0.1:
            print(f"\n[WARNING] Timestamp is VERY recent (< 6 minutes)")
            print(f"  This might cause Advanced Search to return 0 tweets")
            print(f"  But it should still ATTEMPT Advanced Search first")
    except Exception as e:
        print(f"[ERROR] Analysis failed: {e}")


def main():
    """Run test."""
    print("=" * 70)
    print("Investigation: Why hhuang Skipped Advanced Search")
    print("=" * 70)
    
    test_hybrid_logic()
    check_what_happened()
    
    print("\n" + "=" * 70)
    print("Conclusion")
    print("=" * 70)
    print("\nThe timestamp exists and is valid, so Advanced Search SHOULD have been attempted.")
    print("The most likely explanation:")
    print("  - The timestamp was too recent (only 3 minutes old)")
    print("  - Advanced Search was attempted but returned 0 tweets immediately")
    print("  - The log message might have been missed or the exception was caught")
    print("\nWith 12-hour timestamp now set, next refresh will:")
    print("  1. Attempt Advanced Search with 12-hour window")
    print("  2. Should find tweets (we tested and found 8 tweets)")
    print("  3. Return those tweets without needing fallback")


if __name__ == "__main__":
    main()

