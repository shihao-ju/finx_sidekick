# Why Timestamps Are Different

## Current Timestamps

- **hhuang**: `2025-12-03T15:10:52` (12 hours ago)
- **tig88411109**: `2025-12-04T02:04:43` (~1 hour ago)
- **lord_fed**: `2025-12-04T02:04:43` (~1 hour ago)

## Why They're Different

### 1. **hhuang** - 12 Hours Ago
- **Reason**: We manually set this to 12 hours ago for testing Advanced Search
- **When**: Just now, via `test_advanced_search_12h.py`
- **Purpose**: To test if Advanced Search works with a wider time window

### 2. **tig88411109** and **lord_fed** - ~1 Hour Ago
- **Reason**: These were set during the last refresh
- **When**: During the refresh that ran around 2:04 AM UTC
- **How**: The refresh endpoint automatically sets timestamps when it saves summaries

## How Timestamps Are Set

Timestamps are set in `main.py` (lines 1115-1124) when:
1. A refresh is performed
2. Tweets are fetched successfully
3. A summary is generated and saved
4. `update_account_tracking()` is called with `current_timestamp_utc`

```python
current_timestamp_utc = datetime.now(pytz.UTC).isoformat()
update_account_tracking(
    handle,
    last_tweet_id=account_last_tweet_ids.get(handle),
    last_fetch_timestamp_utc=current_timestamp_utc,  # <-- Set here
    last_summary_id=summary_id
)
```

## Why This Happens

1. **Different Refresh Times**: If accounts are refreshed at different times, they get different timestamps
2. **Manual Testing**: We manually changed hhuang's timestamp for testing
3. **Normal Behavior**: Each account's timestamp reflects when it was last successfully refreshed

## Impact on Advanced Search

- **hhuang**: Will use 12-hour window → Should find tweets ✅
- **tig88411109**: Will use ~1-hour window → Might return 0 tweets, fallback to since_id
- **lord_fed**: Will use ~1-hour window → Might return 0 tweets, fallback to since_id

## Options

### Option 1: Keep Current Timestamps (Recommended)
- Let timestamps update naturally during refreshes
- Each account will have its own timestamp based on last refresh
- This is the normal, expected behavior

### Option 2: Set All to Same Timestamp
- Update all accounts to have the same timestamp (e.g., 12 hours ago)
- This ensures all accounts use the same Advanced Search window
- Useful for testing, but not necessary for normal operation

### Option 3: Set All to 12 Hours Ago
- Update all accounts to 12 hours ago
- Ensures Advanced Search works for all accounts
- Can be done via script

## Recommendation

**Keep current timestamps** - they'll update automatically during the next refresh. The different timestamps are expected and don't cause problems. The hybrid system will:
- Try Advanced Search first (with each account's timestamp)
- Fall back to since_id if Advanced Search returns 0 tweets
- Update timestamps after successful refresh

This is working as designed!

