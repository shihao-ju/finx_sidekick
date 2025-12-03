"""
Test script for Phase 1: Database Migration
Tests that:
1. Database tables are created correctly
2. Migration from state.json works
3. Storage functions work with database
4. Accounts and tracking data are accessible
"""
import sqlite3
import json
import os
from database import (
    init_database,
    get_all_accounts,
    get_account_tracking,
    migrate_from_state_json,
    add_account_to_db,
    update_account_tracking
)
from storage import (
    get_monitored_accounts,
    get_monitored_account_handles,
    add_account,
    get_session_context,
    update_session_context
)

def test_database_tables():
    """Test that all required tables exist."""
    print("\n=== Test 1: Database Tables ===")
    conn = sqlite3.connect("summaries.db")
    cursor = conn.cursor()
    
    # Check if tables exist
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name IN ('accounts', 'account_tracking', 'scheduler_logs', 'summaries')
    """)
    tables = [row[0] for row in cursor.fetchall()]
    
    expected_tables = {'accounts', 'account_tracking', 'scheduler_logs', 'summaries'}
    found_tables = set(tables)
    
    if found_tables == expected_tables:
        print("[PASS] All required tables exist")
        return True
    else:
        missing = expected_tables - found_tables
        extra = found_tables - expected_tables
        print(f"[FAIL] Table mismatch. Missing: {missing}, Extra: {extra}")
        return False
    conn.close()


def test_migration():
    """Test migration from state.json."""
    print("\n=== Test 2: Migration from state.json ===")
    
    if not os.path.exists("state.json"):
        print("[INFO] state.json not found, skipping migration test")
        return True
    
    # Run migration
    report = migrate_from_state_json()
    
    print(f"Migration report:")
    print(f"  Accounts migrated: {report['accounts_migrated']}")
    print(f"  Tracking migrated: {report['tracking_migrated']}")
    if report['errors']:
        print(f"  Errors: {report['errors']}")
    
    # Verify accounts were migrated
    accounts = get_all_accounts()
    print(f"\nAccounts in database: {len(accounts)}")
    for acc in accounts:
        username = acc['username'] or '(no username)'
        try:
            print(f"  - {acc['handle']}: {username}")
        except UnicodeEncodeError:
            print(f"  - {acc['handle']}: [username contains special characters]")
    
    # Verify tracking was migrated
    tracking_count = 0
    for acc in accounts:
        tracking = get_account_tracking(acc['handle'])
        if tracking and tracking.get('last_tweet_id'):
            tracking_count += 1
            print(f"  Tracking for {acc['handle']}: last_tweet_id = {tracking['last_tweet_id']}")
    
    if report['accounts_migrated'] > 0 or len(accounts) > 0:
        print("[PASS] Migration completed")
        return True
    else:
        print("[FAIL] No accounts migrated")
        return False


def test_storage_functions():
    """Test that storage functions work with database."""
    print("\n=== Test 3: Storage Functions ===")
    
    # Test get_monitored_accounts
    accounts = get_monitored_accounts()
    print(f"get_monitored_accounts(): {len(accounts)} accounts")
    for acc in accounts:
        username = acc['username'] or '(no username)'
        try:
            print(f"  - {acc['handle']}: {username}")
        except UnicodeEncodeError:
            print(f"  - {acc['handle']}: [username contains special characters]")
    
    # Test get_monitored_account_handles
    handles = get_monitored_account_handles()
    print(f"\nget_monitored_account_handles(): {handles}")
    
    # Test get_session_context (should not have previous_summary)
    if handles:
        context = get_session_context(handles[0])
        print(f"\nget_session_context('{handles[0]}'):")
        print(f"  last_tweet_id: {context.get('last_tweet_id')}")
        print(f"  last_fetch_timestamp_utc: {context.get('last_fetch_timestamp_utc')}")
        print(f"  last_summary_id: {context.get('last_summary_id')}")
        if 'previous_summary' in context:
            print("  [ERROR] previous_summary should not be in context!")
            return False
        else:
            print("  [OK] previous_summary correctly removed")
    
    print("[PASS] Storage functions work correctly")
    return True


def test_add_account():
    """Test adding a new account."""
    print("\n=== Test 4: Add Account ===")
    
    test_handle = "test_account_123"
    
    # Try to add account
    result = add_account(test_handle, "Test User")
    if result:
        print(f"[PASS] Added test account: {test_handle}")
    else:
        print(f"[INFO] Account {test_handle} already exists (OK if previously added)")
    
    # Verify it's in database
    accounts = get_all_accounts()
    test_account = [a for a in accounts if a['handle'] == test_handle]
    if test_account:
        print(f"[PASS] Test account found in database: {test_account[0]}")
        return True
    else:
        print(f"[FAIL] Test account not found in database")
        return False


def test_update_tracking():
    """Test updating account tracking."""
    print("\n=== Test 5: Update Tracking ===")
    
    handles = get_monitored_account_handles()
    if not handles:
        print("[INFO] No accounts to test tracking update")
        return True
    
    test_handle = handles[0]
    test_tweet_id = "9999999999999999999"
    test_timestamp = "2025-12-02T20:00:00Z"
    
    # Update tracking
    update_account_tracking(test_handle, 
                           last_tweet_id=test_tweet_id,
                           last_fetch_timestamp_utc=test_timestamp,
                           last_summary_id=1)
    
    # Verify update
    tracking = get_account_tracking(test_handle)
    if tracking:
        if tracking.get('last_tweet_id') == test_tweet_id:
            print(f"[PASS] Tracking updated correctly for {test_handle}")
            print(f"  last_tweet_id: {tracking.get('last_tweet_id')}")
            print(f"  last_fetch_timestamp_utc: {tracking.get('last_fetch_timestamp_utc')}")
            return True
        else:
            print(f"[FAIL] Tracking not updated correctly")
            return False
    else:
        print(f"[FAIL] No tracking found for {test_handle}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Phase 1: Database Migration - Test Suite")
    print("=" * 60)
    
    # Initialize database
    init_database()
    
    results = []
    
    # Run tests
    results.append(("Database Tables", test_database_tables()))
    results.append(("Migration", test_migration()))
    results.append(("Storage Functions", test_storage_functions()))
    results.append(("Add Account", test_add_account()))
    results.append(("Update Tracking", test_update_tracking()))
    
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
        print("\n[SUCCESS] All tests passed! Phase 1 migration is working correctly.")
        return True
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

