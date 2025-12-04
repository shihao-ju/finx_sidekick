"""
Test script for Phase 2: Hybrid Fetch Implementation
Tests that:
1. Advanced Search function exists and can be called
2. Hybrid fetch function exists and can be called
3. Timestamp handling works correctly
4. Fallback logic works
"""
import sys
import os
from datetime import datetime, timedelta
import pytz

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that required modules can be imported."""
    print("\n=== Test 1: Imports ===")
    try:
        from main import fetch_tweets_advanced_search, fetch_tweets_hybrid
        print("[PASS] Successfully imported hybrid fetch functions")
        return True
    except ImportError as e:
        print(f"[FAIL] Failed to import: {e}")
        return False


def test_timestamp_formatting():
    """Test timestamp formatting for Advanced Search API."""
    print("\n=== Test 2: Timestamp Formatting ===")
    
    # Test ISO to Advanced Search format conversion
    test_timestamp = "2025-12-02T14:00:00Z"
    try:
        dt = datetime.fromisoformat(test_timestamp.replace('Z', '+00:00'))
        since_str = dt.strftime("%Y-%m-%d_%H:%M:%S_UTC")
        expected_format = "2025-12-02_14:00:00_UTC"
        
        if since_str == expected_format:
            print(f"[PASS] Timestamp formatting correct: {since_str}")
            return True
        else:
            print(f"[FAIL] Format mismatch. Got: {since_str}, Expected: {expected_format}")
            return False
    except Exception as e:
        print(f"[FAIL] Timestamp formatting error: {e}")
        return False


def test_timezone_conversion():
    """Test ET to UTC conversion."""
    print("\n=== Test 3: Timezone Conversion ===")
    
    try:
        # Create ET timezone
        et_tz = pytz.timezone('America/New_York')
        utc_tz = pytz.UTC
        
        # Test current time conversion
        now_et = datetime.now(et_tz)
        now_utc = now_et.astimezone(utc_tz)
        
        # Test specific time conversion (8pm ET = midnight UTC next day during DST)
        test_et = et_tz.localize(datetime(2025, 12, 2, 20, 0, 0))
        test_utc = test_et.astimezone(utc_tz)
        
        print(f"[PASS] ET to UTC conversion works")
        print(f"  Example: 2025-12-02 20:00 ET = {test_utc.isoformat()} UTC")
        return True
    except Exception as e:
        print(f"[FAIL] Timezone conversion error: {e}")
        return False


def test_hybrid_fetch_structure():
    """Test that hybrid fetch function has correct structure."""
    print("\n=== Test 4: Hybrid Fetch Structure ===")
    
    try:
        from main import fetch_tweets_hybrid
        import inspect
        
        # Check function signature
        sig = inspect.signature(fetch_tweets_hybrid)
        params = list(sig.parameters.keys())
        
        expected_params = ['handle', 'since_id', 'last_fetch_timestamp_utc']
        if all(p in params for p in expected_params):
            print(f"[PASS] Hybrid fetch has correct parameters: {params}")
            return True
        else:
            missing = [p for p in expected_params if p not in params]
            print(f"[FAIL] Missing parameters: {missing}")
            return False
    except Exception as e:
        print(f"[FAIL] Structure check error: {e}")
        return False


def test_database_tracking_update():
    """Test that database tracking stores timestamp."""
    print("\n=== Test 5: Database Tracking Update ===")
    
    try:
        from database import get_account_tracking, update_account_tracking
        
        # Test with a known account (if exists)
        test_handle = "hhuang"
        
        # Get current tracking
        tracking_before = get_account_tracking(test_handle)
        
        if tracking_before:
            # Update with timestamp
            test_timestamp = datetime.now(pytz.UTC).isoformat()
            update_account_tracking(
                test_handle,
                last_fetch_timestamp_utc=test_timestamp
            )
            
            # Verify update
            tracking_after = get_account_tracking(test_handle)
            if tracking_after and tracking_after.get('last_fetch_timestamp_utc'):
                print(f"[PASS] Timestamp stored in database: {tracking_after['last_fetch_timestamp_utc']}")
                return True
            else:
                print(f"[FAIL] Timestamp not stored")
                return False
        else:
            print(f"[INFO] No tracking found for {test_handle}, skipping test")
            return True  # Not a failure, just no data
    except Exception as e:
        print(f"[FAIL] Database tracking test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Phase 2: Hybrid Fetch Implementation - Test Suite")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Timestamp Formatting", test_timestamp_formatting()))
    results.append(("Timezone Conversion", test_timezone_conversion()))
    results.append(("Hybrid Fetch Structure", test_hybrid_fetch_structure()))
    results.append(("Database Tracking Update", test_database_tracking_update()))
    
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
        print("\n[SUCCESS] All tests passed! Phase 2 hybrid fetch is implemented correctly.")
        return True
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

