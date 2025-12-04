# Why Some Accounts Don't Have Timestamps

## The Issue

Two accounts (`tig88411109` and `lord_fed`) don't have `last_fetch_timestamp_utc` in the database, while `hhuang` does.

## Root Cause

### 1. Migration Only Migrated Existing Data

The migration function (`migrate_from_state_json`) only migrated data that existed in `state.json`:
- ✅ `last_tweet_id` - existed in state.json → migrated
- ❌ `last_fetch_timestamp_utc` - **NEW feature** in Phase 2 → didn't exist in state.json → not migrated

### 2. Timestamps Are Only Added During Refresh

Timestamps are added when:
- A refresh is performed AFTER Phase 2 was implemented
- The refresh endpoint calls `update_account_tracking()` with `last_fetch_timestamp_utc`

Looking at the code in `main.py` (lines 1115-1124), timestamps are updated here:
```python
if summary_id:
    current_timestamp_utc = datetime.now(pytz.UTC).isoformat()
    for handle in accounts:
        update_account_tracking(
            handle,
            last_tweet_id=account_last_tweet_ids.get(handle),
            last_fetch_timestamp_utc=current_timestamp_utc,  # <-- Timestamp added here
            last_summary_id=summary_id
        )
```

### 3. Only `hhuang` Was Refreshed After Phase 2

- `hhuang` has timestamp: `2025-12-04T03:00:15.503688+00:00` 
  - This means it was refreshed after Phase 2 was implemented
- `tig88411109` and `lord_fed` don't have timestamps
  - They haven't been refreshed since Phase 2 was implemented
  - They still have their old `last_tweet_id` from migration

## Solution

To add timestamps to all accounts, you have two options:

### Option 1: Run Refresh (Recommended)
Click the refresh button - this will:
1. Fetch tweets for all accounts
2. Generate a summary
3. Update ALL accounts with timestamps automatically

### Option 2: Add Timestamps Manually
Run the helper script:
```bash
python verify_refresh_method.py --add-timestamps
```

This will add a timestamp (1 hour ago) to accounts that don't have one, so they'll use Advanced Search on the next refresh.

## Why This Happened

This is expected behavior:
- Migration preserves existing data (`last_tweet_id`)
- New features (timestamps) are added incrementally as accounts are refreshed
- This ensures backward compatibility and gradual migration

