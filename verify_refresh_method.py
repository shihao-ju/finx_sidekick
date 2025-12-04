"""
Helper script to:
1. Add timestamps to accounts that don't have them (so they use Advanced Search)
2. Show which method will be used for each account
3. Help verify Advanced Search is working
"""
import sys
import os
from datetime import datetime, timedelta
import pytz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def show_current_status():
    """Show which method each account will use."""
    print("\n=== Current Status ===")
    try:
        from database import get_all_accounts, get_account_tracking
        
        accounts = get_all_accounts()
        print(f"\nFound {len(accounts)} accounts:\n")
        
        for acc in accounts:
            handle = acc['handle']
            tracking = get_account_tracking(handle)
            
            has_timestamp = bool(tracking and tracking.get('last_fetch_timestamp_utc'))
            has_tweet_id = bool(tracking and tracking.get('last_tweet_id'))
            
            if has_timestamp:
                method = "Advanced Search (Primary)"
                timestamp = tracking.get('last_fetch_timestamp_utc')
                print(f"  {handle}:")
                print(f"    Method: {method}")
                print(f"    Timestamp: {timestamp}")
            elif has_tweet_id:
                method = "since_id Fallback"
                tweet_id = tracking.get('last_tweet_id')
                print(f"  {handle}:")
                print(f"    Method: {method}")
                print(f"    Tweet ID: {tweet_id}")
            else:
                method = "First Fetch (Default)"
                print(f"  {handle}:")
                print(f"    Method: {method}")
        
        return accounts
    except Exception as e:
        print(f"[ERROR] Failed to get status: {e}")
        import traceback
        traceback.print_exc()
        return []


def add_timestamps_to_all_accounts():
    """Add timestamps to all accounts so they use Advanced Search."""
    print("\n=== Adding Timestamps to All Accounts ===")
    
    try:
        from database import get_all_accounts, get_account_tracking, update_account_tracking
        
        accounts = get_all_accounts()
        
        # Set timestamp to 1 hour ago (so Advanced Search will fetch recent tweets)
        test_timestamp = (datetime.now(pytz.UTC) - timedelta(hours=1)).isoformat()
        
        updated_count = 0
        for acc in accounts:
            handle = acc['handle']
            tracking = get_account_tracking(handle)
            
            if not tracking or not tracking.get('last_fetch_timestamp_utc'):
                print(f"  Adding timestamp to {handle}...")
                update_account_tracking(
                    handle,
                    last_fetch_timestamp_utc=test_timestamp
                )
                updated_count += 1
            else:
                print(f"  {handle} already has timestamp, skipping")
        
        print(f"\n[SUCCESS] Added timestamps to {updated_count} account(s)")
        print(f"  Timestamp: {test_timestamp}")
        print(f"\nNow ALL accounts will use Advanced Search when you click refresh!")
        
    except Exception as e:
        print(f"[ERROR] Failed to add timestamps: {e}")
        import traceback
        traceback.print_exc()


def show_how_to_verify():
    """Show how to verify Advanced Search is being used."""
    print("\n=== How to Verify Advanced Search is Working ===")
    print("\n1. Click the refresh button in your browser")
    print("\n2. Check the server logs (refresh_brief.log or console output)")
    print("   Look for these messages:")
    print("   - '[DEBUG] Attempting Advanced Search (primary) for ...'")
    print("   - '[DEBUG] Advanced Search fetched X tweets for ...'")
    print("   - '[DEBUG] Advanced Search succeeded: X tweets'")
    print("\n3. If Advanced Search fails, you'll see:")
    print("   - '[WARNING] Advanced Search failed for ..., trying fallback'")
    print("   - '[DEBUG] Using since_id fallback for ...'")
    print("\n4. Check refresh_brief.log file for detailed logs:")
    print("   - Windows: type refresh_brief.log")
    print("   - Or open it in your editor")
    print("\n5. The logs will show:")
    print("   - Which method was used (Advanced Search vs fallback)")
    print("   - How many tweets were fetched")
    print("   - Any errors that occurred")


def main():
    """Main function."""
    print("=" * 70)
    print("Refresh Method Verification Helper")
    print("=" * 70)
    
    # Show current status
    accounts = show_current_status()
    
    # Show how to verify
    show_how_to_verify()
    
    # Ask if user wants to add timestamps
    print("\n" + "=" * 70)
    print("Options:")
    print("=" * 70)
    print("\nTo make ALL accounts use Advanced Search:")
    print("  Run: python verify_refresh_method.py --add-timestamps")
    print("\nCurrent behavior:")
    accounts_with_timestamp = 0
    accounts_without_timestamp = 0
    
    for acc in accounts:
        from database import get_account_tracking
        tracking = get_account_tracking(acc['handle'])
        if tracking and tracking.get('last_fetch_timestamp_utc'):
            accounts_with_timestamp += 1
        else:
            accounts_without_timestamp += 1
    
    print(f"  - {accounts_with_timestamp} account(s) will use Advanced Search")
    print(f"  - {accounts_without_timestamp} account(s) will use since_id fallback")
    
    if "--add-timestamps" in sys.argv:
        add_timestamps_to_all_accounts()
        print("\n" + "=" * 70)
        print("Updated Status:")
        print("=" * 70)
        show_current_status()


if __name__ == "__main__":
    main()

