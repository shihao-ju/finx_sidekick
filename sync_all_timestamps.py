"""
Script to set all accounts to the same timestamp (12 hours ago).
Useful for testing Advanced Search with consistent time windows.
"""
import sys
import os
from datetime import datetime, timedelta
import pytz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def sync_all_timestamps(hours_ago=12):
    """Set all accounts to the same timestamp."""
    print(f"\n=== Syncing All Timestamps to {hours_ago} Hours Ago ===")
    
    try:
        from database import get_all_accounts, update_account_tracking, get_account_tracking
        
        accounts = get_all_accounts()
        timestamp = (datetime.now(pytz.UTC) - timedelta(hours=hours_ago)).isoformat()
        
        print(f"Setting all {len(accounts)} accounts to: {timestamp}")
        print(f"  ({hours_ago} hours ago)\n")
        
        updated = []
        for acc in accounts:
            handle = acc['handle']
            tracking_before = get_account_tracking(handle)
            old_timestamp = tracking_before.get('last_fetch_timestamp_utc') if tracking_before else None
            
            update_account_tracking(
                handle,
                last_fetch_timestamp_utc=timestamp
            )
            
            updated.append({
                'handle': handle,
                'old_timestamp': old_timestamp,
                'new_timestamp': timestamp
            })
            
            print(f"  {handle}: Updated")
            if old_timestamp:
                print(f"    Old: {old_timestamp}")
            print(f"    New: {timestamp}")
        
        print(f"\n[SUCCESS] Updated {len(updated)} accounts")
        print(f"\nAll accounts will now use Advanced Search with {hours_ago}-hour window")
        
        return updated
        
    except Exception as e:
        print(f"[ERROR] Failed to sync timestamps: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main function."""
    print("=" * 70)
    print("Sync All Account Timestamps")
    print("=" * 70)
    
    import sys
    hours = 12
    if len(sys.argv) > 1:
        try:
            hours = int(sys.argv[1])
        except ValueError:
            print(f"[ERROR] Invalid hours: {sys.argv[1]}")
            return
    
    print(f"\nThis will set all accounts to {hours} hours ago.")
    print("This ensures all accounts use the same Advanced Search window.")
    print("\nPress Ctrl+C to cancel, or wait 3 seconds to continue...")
    
    import time
    try:
        time.sleep(3)
    except KeyboardInterrupt:
        print("\n[CANCELLED]")
        return
    
    sync_all_timestamps(hours)
    
    print("\n" + "=" * 70)
    print("Next Steps")
    print("=" * 70)
    print("\nWhen you click refresh:")
    print(f"  - All accounts will use Advanced Search with {hours}-hour window")
    print("  - Should find tweets successfully")
    print("  - Timestamps will update to current time after refresh")


if __name__ == "__main__":
    main()

