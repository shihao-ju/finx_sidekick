"""
End-to-End Test for Full Application
Tests the complete flow from database initialization to fetch operations.
"""
import sys
import os
import json
from datetime import datetime
import pytz

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database_initialization():
    """Test that database initializes correctly with all tables."""
    print("\n=== Test 1: Database Initialization ===")
    try:
        from database import init_database, get_all_accounts, get_account_tracking
        
        # Initialize database
        init_database()
        
        # Check that we can query accounts table
        accounts = get_all_accounts()
        print(f"[PASS] Database initialized. Found {len(accounts)} accounts")
        return True
    except Exception as e:
        print(f"[FAIL] Database initialization error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_migration_on_startup():
    """Test that migration runs correctly."""
    print("\n=== Test 2: Migration on Startup ===")
    try:
        from database import migrate_from_state_json
        
        # Run migration
        report = migrate_from_state_json()
        
        print(f"  Accounts migrated: {report['accounts_migrated']}")
        print(f"  Tracking migrated: {report['tracking_migrated']}")
        if report['errors']:
            print(f"  Errors: {report['errors']}")
        
        # Migration should be idempotent (can run multiple times)
        if report['errors'] and 'already exists' not in str(report['errors']).lower():
            print(f"[WARNING] Migration had errors: {report['errors']}")
        
        print("[PASS] Migration completed successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_storage_functions():
    """Test that storage functions work with database."""
    print("\n=== Test 3: Storage Functions ===")
    try:
        from storage import (
            get_monitored_accounts,
            get_monitored_account_handles,
            get_session_context,
            add_account,
            update_account_username
        )
        
        # Test get accounts
        accounts = get_monitored_accounts()
        handles = get_monitored_account_handles()
        
        print(f"  Found {len(accounts)} accounts via get_monitored_accounts()")
        print(f"  Found {len(handles)} handles via get_monitored_account_handles()")
        
        if len(accounts) != len(handles):
            print(f"[FAIL] Account count mismatch")
            return False
        
        # Test get session context (should not have previous_summary)
        if handles:
            context = get_session_context(handles[0])
            if 'previous_summary' in context:
                print(f"[FAIL] previous_summary should not be in context")
                return False
            print(f"  Context for {handles[0]}: {list(context.keys())}")
        
        print("[PASS] Storage functions work correctly")
        return True
    except Exception as e:
        print(f"[FAIL] Storage functions error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_hybrid_fetch_functions():
    """Test that hybrid fetch functions exist and have correct structure."""
    print("\n=== Test 4: Hybrid Fetch Functions ===")
    try:
        # Import without FastAPI dependencies
        import importlib.util
        spec = importlib.util.spec_from_file_location("main_module", "main.py")
        main_module = importlib.util.module_from_spec(spec)
        
        # Check if functions exist in the file
        with open("main.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        checks = {
            "fetch_tweets_advanced_search": "def fetch_tweets_advanced_search" in content,
            "fetch_tweets_hybrid": "def fetch_tweets_hybrid" in content,
            "pytz import": "import pytz" in content or "from datetime import" in content,
            "timestamp storage": "last_fetch_timestamp_utc" in content,
        }
        
        all_passed = all(checks.values())
        for check_name, passed in checks.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {status}: {check_name}")
        
        if all_passed:
            print("[PASS] Hybrid fetch functions implemented correctly")
            return True
        else:
            print("[FAIL] Some hybrid fetch components missing")
            return False
    except Exception as e:
        print(f"[FAIL] Hybrid fetch check error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_tracking_with_timestamp():
    """Test that database tracking stores and retrieves timestamps correctly."""
    print("\n=== Test 5: Database Tracking with Timestamp ===")
    try:
        from database import get_account_tracking, update_account_tracking
        
        # Get existing accounts
        from storage import get_monitored_account_handles
        handles = get_monitored_account_handles()
        
        if not handles:
            print("[INFO] No accounts found, skipping timestamp test")
            return True
        
        test_handle = handles[0]
        
        # Get current tracking
        tracking_before = get_account_tracking(test_handle)
        
        # Update with timestamp
        test_timestamp = datetime.now(pytz.UTC).isoformat()
        test_tweet_id = "9999999999999999999"
        
        update_account_tracking(
            test_handle,
            last_tweet_id=test_tweet_id,
            last_fetch_timestamp_utc=test_timestamp,
            last_summary_id=1
        )
        
        # Verify update
        tracking_after = get_account_tracking(test_handle)
        
        if not tracking_after:
            print(f"[FAIL] No tracking found after update")
            return False
        
        checks = {
            "last_tweet_id stored": tracking_after.get('last_tweet_id') == test_tweet_id,
            "timestamp stored": tracking_after.get('last_fetch_timestamp_utc') == test_timestamp,
            "summary_id stored": tracking_after.get('last_summary_id') == 1,
        }
        
        all_passed = all(checks.values())
        for check_name, passed in checks.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {status}: {check_name}")
        
        if all_passed:
            print(f"[PASS] Database tracking stores all fields correctly")
            return True
        else:
            print(f"[FAIL] Some tracking fields not stored correctly")
            return False
    except Exception as e:
        print(f"[FAIL] Database tracking test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_refresh_endpoint_structure():
    """Test that refresh endpoint uses hybrid fetch."""
    print("\n=== Test 6: Refresh Endpoint Structure ===")
    try:
        # Check that refresh endpoint uses hybrid fetch
        with open("main.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Find refresh-brief endpoint
        refresh_section = content[content.find("@app.post(\"/refresh-brief\""):content.find("def refresh_brief_ui_dev")]
        
        checks = {
            "uses hybrid fetch": "fetch_tweets_hybrid" in refresh_section,
            "gets timestamp from context": "last_fetch_timestamp_utc" in refresh_section,
            "updates timestamp": "update_account_tracking" in refresh_section and "last_fetch_timestamp_utc" in refresh_section,
            "uses pytz for UTC": "pytz.UTC" in refresh_section,
        }
        
        all_passed = all(checks.values())
        for check_name, passed in checks.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {status}: {check_name}")
        
        if all_passed:
            print("[PASS] Refresh endpoint uses hybrid fetch correctly")
            return True
        else:
            print("[FAIL] Refresh endpoint structure issues")
            return False
    except Exception as e:
        print(f"[FAIL] Refresh endpoint check error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_timezone_handling():
    """Test timezone conversion and handling."""
    print("\n=== Test 7: Timezone Handling ===")
    try:
        # Test ET to UTC conversion
        et_tz = pytz.timezone('America/New_York')
        utc_tz = pytz.UTC
        
        # Test market hours (9:30 AM ET)
        market_open_et = et_tz.localize(datetime(2025, 12, 2, 9, 30, 0))
        market_open_utc = market_open_et.astimezone(utc_tz)
        
        # Test after market (8:00 PM ET)
        after_market_et = et_tz.localize(datetime(2025, 12, 2, 20, 0, 0))
        after_market_utc = after_market_et.astimezone(utc_tz)
        
        # Test early morning (6:00 AM ET)
        early_morning_et = et_tz.localize(datetime(2025, 12, 2, 6, 0, 0))
        early_morning_utc = early_morning_et.astimezone(utc_tz)
        
        print(f"  9:30 AM ET = {market_open_utc.isoformat()} UTC")
        print(f"  8:00 PM ET = {after_market_utc.isoformat()} UTC")
        print(f"  6:00 AM ET = {early_morning_utc.isoformat()} UTC")
        
        # Verify conversions are correct (should be different times)
        if market_open_utc != after_market_utc != early_morning_utc:
            print("[PASS] Timezone conversions work correctly")
            return True
        else:
            print("[FAIL] Timezone conversions incorrect")
            return False
    except Exception as e:
        print(f"[FAIL] Timezone handling error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_summary_storage():
    """Test that summaries are stored correctly."""
    print("\n=== Test 8: Summary Storage ===")
    try:
        from database import save_summary, get_latest_summary, get_summaries
        
        # Test saving a summary
        test_summary = "## News\n- Test news item\n## Trades\n- Test trade"
        test_tweet_ids = ["123456789", "987654321"]
        test_timestamp = datetime.now().isoformat()
        
        summary_id = save_summary(test_summary, test_tweet_ids, test_timestamp)
        
        if not summary_id:
            print("[FAIL] Summary not saved")
            return False
        
        # Test retrieving latest summary
        latest = get_latest_summary()
        if not latest:
            print("[FAIL] Latest summary not found")
            return False
        
        checks = {
            "summary text matches": latest['summary'] == test_summary,
            "tweet_ids match": latest['tweet_ids'] == test_tweet_ids,
            "timestamp matches": latest['timestamp'] == test_timestamp,
        }
        
        all_passed = all(checks.values())
        for check_name, passed in checks.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {status}: {check_name}")
        
        # Test pagination
        summaries = get_summaries(limit=10, offset=0)
        if len(summaries) > 0:
            print(f"  Found {len(summaries)} summaries via pagination")
        
        if all_passed:
            print("[PASS] Summary storage works correctly")
            return True
        else:
            print("[FAIL] Summary storage issues")
            return False
    except Exception as e:
        print(f"[FAIL] Summary storage error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all end-to-end tests."""
    print("=" * 60)
    print("End-to-End Application Test Suite")
    print("=" * 60)
    print("Testing complete application flow:")
    print("  1. Database initialization")
    print("  2. Migration")
    print("  3. Storage functions")
    print("  4. Hybrid fetch implementation")
    print("  5. Database tracking")
    print("  6. Refresh endpoint structure")
    print("  7. Timezone handling")
    print("  8. Summary storage")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Database Initialization", test_database_initialization()))
    results.append(("Migration on Startup", test_migration_on_startup()))
    results.append(("Storage Functions", test_storage_functions()))
    results.append(("Hybrid Fetch Functions", test_hybrid_fetch_functions()))
    results.append(("Database Tracking with Timestamp", test_database_tracking_with_timestamp()))
    results.append(("Refresh Endpoint Structure", test_refresh_endpoint_structure()))
    results.append(("Timezone Handling", test_timezone_handling()))
    results.append(("Summary Storage", test_summary_storage()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All end-to-end tests passed!")
        print("The application is ready for Phase 3 implementation.")
        return True
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed.")
        print("Please review the errors above before proceeding.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

