# Implementation To-Do List

## Phase 1: Database Migration

### Database Schema
- [ ] **db-1**: Create `accounts` table in `database.py`
- [ ] **db-2**: Create `account_tracking` table in `database.py`
- [ ] **db-3**: Create `scheduler_logs` table in `database.py`
- [ ] **db-4**: Update `init_database()` to create all new tables

### Migration Functions
- [ ] **db-5**: Create `migrate_from_state_json()` function
- [ ] **db-6**: Migrate `monitored_accounts` → `accounts` table
- [ ] **db-7**: Migrate `account_info` → `accounts.username`
- [ ] **db-8**: Migrate `session_context` → `account_tracking` table

### Update Storage Layer
- [ ] **db-9**: Update `storage.py` functions to use database instead of state.json
- [ ] **db-10**: Update `get_monitored_accounts()` to read from database
- [ ] **db-11**: Update `add_account()` to write to database
- [ ] **db-12**: Update `update_account_username()` to write to database
- [ ] **db-13**: Update `get_session_context()` to read from database
- [ ] **db-14**: Update `update_session_context()` to write to database
- [ ] **db-15**: Remove `previous_summary` storage logic

### Update Application
- [ ] **db-16**: Update `main.py` to use database functions
- [ ] **db-17**: Remove `previous_summary` from session context logic
- [ ] **db-18**: Fetch latest summary from `summaries` table when needed
- [ ] **db-19**: Run migration on startup (one-time check)

### Testing
- [ ] **db-20**: Test migration with existing state.json data
- [ ] **db-21**: Verify all data migrated correctly
- [ ] **db-22**: Test backward compatibility

## Phase 2: Hybrid Fetch Implementation

### Dependencies
- [ ] **fetch-1**: Install `pytz` library: `pip install pytz`

### Advanced Search API
- [ ] **fetch-2**: Create `fetch_tweets_advanced_search()` function
- [ ] **fetch-3**: Implement timestamp-based query: `from:handle since:timestamp until:now`
- [ ] **fetch-4**: Handle pagination for Advanced Search API
- [ ] **fetch-5**: Parse Advanced Search API response format

### Hybrid Fetch Function
- [ ] **fetch-6**: Create `fetch_tweets_hybrid()` function
- [ ] **fetch-7**: Implement timestamp primary approach
- [ ] **fetch-8**: Implement since_id fallback approach
- [ ] **fetch-9**: Store both `last_tweet_id` and `last_fetch_timestamp_utc`

### Timestamp Handling
- [ ] **fetch-10**: Implement UTC timestamp storage
- [ ] **fetch-11**: Implement ET→UTC conversion using pytz
- [ ] **fetch-12**: Fix timestamp boundary issues (add 1-second buffer)
- [ ] **fetch-13**: Use API server time, not local clock
- [ ] **fetch-14**: Handle timezone conversion correctly (DST aware)

### Integration
- [ ] **fetch-15**: Update `/refresh-brief` endpoint to use hybrid fetch
- [ ] **fetch-16**: Update all `fetch_tweets()` calls to use `fetch_tweets_hybrid()`
- [ ] **fetch-17**: Store `last_fetch_timestamp_utc` in `account_tracking` table

### Testing
- [ ] **fetch-18**: Test hybrid fetch with timestamp queries
- [ ] **fetch-19**: Test fallback to since_id when timestamp query fails
- [ ] **fetch-20**: Test timezone conversion accuracy
- [ ] **fetch-21**: Test boundary conditions

## Phase 3: Scheduler Implementation

### Dependencies
- [ ] **sched-1**: Install `apscheduler` library: `pip install apscheduler`

### Configuration
- [ ] **sched-2**: Create `config.json` with scheduler configuration
- [ ] **sched-3**: Create `config.py` module to load configuration
- [ ] **sched-4**: Implement `load_config()` function
- [ ] **sched-5**: Implement `get_scheduler_config()` helper function
- [ ] **sched-6**: Handle missing config gracefully with defaults

### Holiday Detection
- [ ] **sched-7**: Create `holidays.py` with hardcoded US market holidays list
- [ ] **sched-8**: Create `is_market_holiday(date)` function
- [ ] **sched-9**: Create `is_weekend(date)` function
- [ ] **sched-10**: Create `should_fetch_today()` function

### Scheduler Module
- [ ] **sched-11**: Create `scheduler.py` module
- [ ] **sched-12**: Create `SchedulerManager` class
- [ ] **sched-13**: Initialize APScheduler with timezone support
- [ ] **sched-14**: Create `scheduled_refresh()` async function
- [ ] **sched-15**: Implement error handling with retry logic
- [ ] **sched-16**: Implement exponential backoff for retries
- [ ] **sched-17**: Log all events to `scheduler_logs` table

### Schedule Jobs
- [ ] **sched-18**: Create market hours schedule jobs (dynamic based on config interval)
- [ ] **sched-19**: Create after-market schedule job (8pm ET → UTC)
- [ ] **sched-20**: Create after-market schedule job (6am ET → UTC)
- [ ] **sched-21**: Create weekend schedule job (8pm ET once per day)
- [ ] **sched-22**: Handle weekend/holiday logic in schedule

### Integration
- [ ] **sched-23**: Import scheduler module in `main.py`
- [ ] **sched-24**: Initialize scheduler in `@app.on_event("startup")`
- [ ] **sched-25**: Shutdown scheduler in `@app.on_event("shutdown")`
- [ ] **sched-26**: Add scheduler status tracking

### Testing
- [ ] **sched-27**: Test scheduler with shorter intervals (5 minutes for testing)
- [ ] **sched-28**: Test timezone conversion and schedule timing
- [ ] **sched-29**: Test market hours schedule
- [ ] **sched-30**: Test after-market schedule
- [ ] **sched-31**: Test weekend schedule
- [ ] **sched-32**: Test holiday detection

## Phase 4: Admin Page & API

### API Endpoints
- [ ] **admin-1**: Create `/api/scheduler/status` endpoint
- [ ] **admin-2**: Create `/api/scheduler/pause` endpoint
- [ ] **admin-3**: Create `/api/scheduler/resume` endpoint
- [ ] **admin-4**: Create `/api/scheduler/trigger` endpoint (manual trigger)
- [ ] **admin-5**: Create `/api/scheduler/logs` endpoint
- [ ] **admin-6**: Create `/api/scheduler/config` endpoint (get/update)

### Admin HTML Page
- [ ] **admin-7**: Create `admin.html` page
- [ ] **admin-8**: Add scheduler status display (enabled/disabled)
- [ ] **admin-9**: Add next fetch times display
- [ ] **admin-10**: Add last fetch status and times
- [ ] **admin-11**: Add Pause/Resume buttons
- [ ] **admin-12**: Add Manual trigger button
- [ ] **admin-13**: Add Recent logs table
- [ ] **admin-14**: Add Configuration display
- [ ] **admin-15**: Style consistent with main app
- [ ] **admin-16**: Add JavaScript to call API endpoints
- [ ] **admin-17**: Add auto-refresh status every 30 seconds

### Routes
- [ ] **admin-18**: Add route in `main.py` to serve `admin.html`
- [ ] **admin-19**: Ensure same access as main app (no separate auth)

### Testing
- [ ] **admin-20**: Test admin page functionality
- [ ] **admin-21**: Test pause/resume functionality
- [ ] **admin-22**: Test manual trigger
- [ ] **admin-23**: Test logs display

## Phase 5: Error Handling & Logging

### Logging Functions
- [ ] **error-1**: Create `log_scheduler_event()` function
- [ ] **error-2**: Log success events to `scheduler_logs` table
- [ ] **error-3**: Log failure events with error messages
- [ ] **error-4**: Log retry events with retry counts
- [ ] **error-5**: Include tweet counts and summary generation status

### Error Handling
- [ ] **error-6**: Implement retry logic with max attempts
- [ ] **error-7**: Implement exponential backoff for retries
- [ ] **error-8**: Handle API rate limit errors gracefully
- [ ] **error-9**: Continue schedule even if one account fetch fails
- [ ] **error-10**: Handle network errors
- [ ] **error-11**: Handle API errors

### Testing
- [ ] **error-12**: Test error scenarios (API failure, network error)
- [ ] **error-13**: Test retry logic
- [ ] **error-14**: Test error logging

## Phase 6: Final Testing & Validation

- [ ] **test-1**: Test database migration with existing data
- [ ] **test-2**: Test hybrid fetch with various scenarios
- [ ] **test-3**: Test scheduler timing (market hours, after-market, weekends)
- [ ] **test-4**: Test holiday detection
- [ ] **test-5**: Test error handling and retries
- [ ] **test-6**: Test admin page controls
- [ ] **test-7**: Verify API rate limits are respected
- [ ] **test-8**: Test timezone conversion accuracy
- [ ] **test-9**: End-to-end integration test
- [ ] **test-10**: Performance testing

