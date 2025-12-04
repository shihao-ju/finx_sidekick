"""
Investigate why hhuang skipped Advanced Search.
Check if there's a condition that would cause this.
"""
import sys
import os
from datetime import datetime
import pytz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_hhuang_context():
    """Check what context hhuang would have had during refresh."""
    print("\n=== Checking hhuang Context ===")
    
    try:
        from storage import get_session_context
        from database import get_account_tracking
        
        handle = "hhuang"
        
        # Get current tracking (what database has)
        tracking = get_account_tracking(handle)
        print(f"Database tracking:")
        print(f"  last_tweet_id: {tracking.get('last_tweet_id') if tracking else 'None'}")
        print(f"  last_fetch_timestamp_utc: {tracking.get('last_fetch_timestamp_utc') if tracking else 'None'}")
        
        # Get session context (what refresh endpoint would get)
        context = get_session_context(handle)
        print(f"\nSession context (what refresh would get):")
        print(f"  last_tweet_id: {context.get('last_tweet_id')}")
        print(f"  last_fetch_timestamp_utc: {context.get('last_fetch_timestamp_utc')}")
        
        # Check if timestamp would trigger Advanced Search
        timestamp = context.get('last_fetch_timestamp_utc')
        if timestamp:
            print(f"\n[INFO] Timestamp exists: {timestamp}")
            print(f"  This SHOULD trigger Advanced Search")
            
            # Check if timestamp is valid
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                print(f"  Timestamp is valid: {dt.isoformat()}")
                
                # Check time difference
                now = datetime.now(pytz.UTC)
                diff = now - dt
                hours_ago = diff.total_seconds() / 3600
                print(f"  Time difference: {hours_ago:.2f} hours ago")
                
                if hours_ago < 0.1:
                    print(f"\n[WARNING] Timestamp is very recent (< 6 minutes ago)")
                    print(f"  This might cause Advanced Search to return 0 tweets")
                    print(f"  But it should still ATTEMPT Advanced Search first")
                
            except Exception as e:
                print(f"  [ERROR] Timestamp parsing failed: {e}")
        else:
            print(f"\n[INFO] No timestamp in context")
            print(f"  This would skip Advanced Search and go to fallback")
        
        # Simulate the hybrid fetch logic
        print(f"\n=== Simulating Hybrid Fetch Logic ===")
        last_tweet_id = context.get('last_tweet_id')
        last_fetch_timestamp_utc = context.get('last_fetch_timestamp_utc')
        
        print(f"if last_fetch_timestamp_utc: {bool(last_fetch_timestamp_utc)}")
        
        if last_fetch_timestamp_utc:
            print(f"  → Should attempt Advanced Search")
        else:
            print(f"  → Would skip Advanced Search, go to fallback")
        
        if since_id := last_tweet_id:
            print(f"if since_id: {bool(since_id)}")
            print(f"  → Would use since_id fallback if Advanced Search fails")
        
    except Exception as e:
        print(f"[ERROR] Check failed: {e}")
        import traceback
        traceback.print_exc()


def check_log_timing():
    """Check if there's a timing issue."""
    print("\n=== Checking Log Timing ===")
    
    try:
        # Read the log file to see the exact sequence
        with open("refresh_brief.log", "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Find hhuang entries
        hhuang_lines = []
        for i, line in enumerate(lines):
            if "hhuang" in line.lower():
                hhuang_lines.append((i+1, line.strip()))
        
        print(f"Found {len(hhuang_lines)} log entries mentioning hhuang:")
        for line_num, line in hhuang_lines[:10]:  # Show first 10
            print(f"  Line {line_num}: {line[:100]}...")
        
        # Check if there's an "Attempting Advanced Search" message
        has_advanced_search = any("Attempting Advanced Search" in line for _, line in hhuang_lines)
        
        if has_advanced_search:
            print(f"\n[INFO] Found 'Attempting Advanced Search' message for hhuang")
        else:
            print(f"\n[WARNING] NO 'Attempting Advanced Search' message found for hhuang")
            print(f"  This confirms Advanced Search was skipped")
        
    except FileNotFoundError:
        print("[INFO] refresh_brief.log not found, skipping log analysis")
    except Exception as e:
        print(f"[ERROR] Log check failed: {e}")


def main():
    """Run investigation."""
    print("=" * 70)
    print("Investigation: Why hhuang Skipped Advanced Search")
    print("=" * 70)
    
    check_hhuang_context()
    check_log_timing()
    
    print("\n" + "=" * 70)
    print("Investigation Summary")
    print("=" * 70)
    print("\nPossible reasons hhuang skipped Advanced Search:")
    print("  1. Timestamp was None/empty when refresh ran")
    print("  2. Exception was caught silently")
    print("  3. Code path bug (timestamp check failed)")
    print("  4. Timestamp was set AFTER refresh started")
    print("\n[NOTE] With 12-hour timestamp now set, next refresh should use Advanced Search")


if __name__ == "__main__":
    main()

