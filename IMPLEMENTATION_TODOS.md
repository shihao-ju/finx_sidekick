# Implementation To-Do List

## Phase 1: Database Migration ✅ COMPLETE

### Database Schema
- [x] **db-1**: Create `accounts` table in `database.py`
- [x] **db-2**: Create `account_tracking` table in `database.py`
- [x] **db-3**: Create `scheduler_logs` table in `database.py`
- [x] **db-4**: Create `summaries` table in `database.py`
- [x] **db-4b**: Update `init_database()` to create all new tables

### Migration Functions
- [x] **db-5**: Create `migrate_from_state_json()` function
- [x] **db-6**: Migrate `monitored_accounts` → `accounts` table
- [x] **db-7**: Migrate `account_info` → `accounts.username`
- [x] **db-8**: Migrate `session_context` → `account_tracking` table

### Update Storage Layer
- [x] **db-9**: Update `storage.py` functions to use database instead of state.json
- [x] **db-10**: Update `get_monitored_accounts()` to read from database
- [x] **db-11**: Update `add_account()` to write to database
- [x] **db-12**: Update `update_account_username()` to write to database
- [x] **db-13**: Update `get_session_context()` to read from database
- [x] **db-14**: Update `update_session_context()` to write to database
- [x] **db-15**: Remove `previous_summary` storage logic

### Update Application
- [x] **db-16**: Update `main.py` to use database functions
- [x] **db-17**: Remove `previous_summary` from session context logic
- [x] **db-18**: Fetch latest summary from `summaries` table when needed
- [x] **db-19**: Run migration on startup (one-time check)

### Testing
- [x] **db-20**: Test migration with existing state.json data
- [x] **db-21**: Verify all data migrated correctly
- [x] **db-22**: Test backward compatibility

## Phase 2: Hybrid Fetch Implementation ✅ COMPLETE

### Dependencies
- [x] **fetch-1**: Install `pytz` library: `pip install pytz`

### Advanced Search API
- [x] **fetch-2**: Create `fetch_tweets_advanced_search()` function
- [x] **fetch-3**: Implement timestamp-based query: `from:handle since:timestamp until:now`
- [x] **fetch-4**: Handle pagination for Advanced Search API
- [x] **fetch-5**: Parse Advanced Search API response format

### Hybrid Fetch Function
- [x] **fetch-6**: Create `fetch_tweets_hybrid()` function
- [x] **fetch-7**: Implement timestamp primary approach
- [x] **fetch-8**: Implement since_id fallback approach
- [x] **fetch-9**: Store both `last_tweet_id` and `last_fetch_timestamp_utc`

### Timestamp Handling
- [x] **fetch-10**: Implement UTC timestamp storage
- [x] **fetch-11**: Implement ET→UTC conversion using pytz
- [x] **fetch-12**: Fix timestamp boundary issues (add 1-second buffer)
- [x] **fetch-13**: Use API server time, not local clock
- [x] **fetch-14**: Handle timezone conversion correctly (DST aware)

### Integration
- [x] **fetch-15**: Update `/refresh-brief` endpoint to use hybrid fetch
- [x] **fetch-16**: Update all `fetch_tweets()` calls to use `fetch_tweets_hybrid()`
- [x] **fetch-17**: Store `last_fetch_timestamp_utc` in `account_tracking` table

### Testing
- [x] **fetch-18**: Test hybrid fetch with timestamp queries
- [x] **fetch-19**: Test fallback to since_id when timestamp query fails
- [x] **fetch-20**: Test timezone conversion accuracy
- [x] **fetch-21**: Test boundary conditions

## Phase 3: Scheduler Implementation ✅ COMPLETE

### Dependencies
- [x] **sched-1**: Install `apscheduler` library: `pip install apscheduler`

### Configuration
- [x] **sched-2**: Create `config.json` with scheduler configuration
- [x] **sched-3**: Create `config.py` module to load configuration
- [x] **sched-4**: Implement `load_config()` function
- [x] **sched-5**: Implement `get_scheduler_config()` helper function
- [x] **sched-6**: Handle missing config gracefully with defaults

### Holiday Detection
- [x] **sched-7**: Create `holidays.py` with hardcoded US market holidays list
- [x] **sched-8**: Create `is_market_holiday(date)` function
- [x] **sched-9**: Create `is_weekend(date)` function
- [x] **sched-10**: Create `should_fetch_today()` function

### Scheduler Module
- [x] **sched-11**: Create `scheduler.py` module
- [x] **sched-12**: Create `SchedulerManager` class
- [x] **sched-13**: Initialize APScheduler with timezone support
- [x] **sched-14**: Create `_scheduled_refresh()` async function
- [x] **sched-15**: Implement error handling with retry logic
- [x] **sched-16**: Implement exponential backoff for retries
- [x] **sched-17**: Log all events to `scheduler_logs` table

### Schedule Jobs
- [x] **sched-18**: Create market hours schedule jobs (dynamic based on config interval)
- [x] **sched-19**: Create after-market schedule job (8pm ET → UTC)
- [x] **sched-20**: Create after-market schedule job (6am ET → UTC)
- [x] **sched-21**: Create weekend schedule job (8pm ET once per day)
- [x] **sched-22**: Handle weekend/holiday logic in schedule

### Integration
- [x] **sched-23**: Import scheduler module in `main.py`
- [x] **sched-24**: Initialize scheduler in `@app.on_event("startup")`
- [x] **sched-25**: Shutdown scheduler in `@app.on_event("shutdown")`
- [x] **sched-26**: Add scheduler status tracking

### Testing
- [x] **sched-27**: Test scheduler with shorter intervals (test job implemented)
- [x] **sched-28**: Test timezone conversion and schedule timing
- [x] **sched-29**: Test market hours schedule
- [x] **sched-30**: Test after-market schedule
- [x] **sched-31**: Test weekend schedule
- [x] **sched-32**: Test holiday detection

## Phase 4: Admin Page & API ✅ COMPLETE

### API Endpoints
- [x] **admin-1**: Create `/api/scheduler/status` endpoint
- [x] **admin-2**: Create `/api/scheduler/pause` endpoint
- [x] **admin-3**: Create `/api/scheduler/resume` endpoint
- [x] **admin-4**: Create `/api/scheduler/trigger` endpoint (manual trigger)
- [x] **admin-5**: Create `/api/scheduler/logs` endpoint
- [x] **admin-6**: Create `/api/scheduler/config` endpoint (get/update)

### Admin HTML Page
- [x] **admin-7**: Create `admin.html` page
- [x] **admin-8**: Add scheduler status display (enabled/disabled)
- [x] **admin-9**: Add next fetch times display
- [x] **admin-10**: Add last fetch status and times
- [x] **admin-11**: Add Pause/Resume buttons
- [x] **admin-12**: Add Manual trigger button
- [x] **admin-13**: Add Recent logs table
- [x] **admin-14**: Add Configuration display
- [x] **admin-15**: Style consistent with main app
- [x] **admin-16**: Add JavaScript to call API endpoints
- [x] **admin-17**: Add auto-refresh status (every 10 seconds)

### Routes
- [x] **admin-18**: Add route in `main.py` to serve `admin.html`
- [x] **admin-19**: Ensure same access as main app (no separate auth)

### Testing
- [x] **admin-20**: Test admin page functionality
- [x] **admin-21**: Test pause/resume functionality
- [x] **admin-22**: Test manual trigger
- [x] **admin-23**: Test logs display

## Phase 5: Error Handling & Logging ✅ COMPLETE

### Logging Functions
- [x] **error-1**: Create `log_scheduler_event()` function
- [x] **error-2**: Log success events to `scheduler_logs` table
- [x] **error-3**: Log failure events with error messages
- [x] **error-4**: Log retry events with retry counts
- [x] **error-5**: Include tweet counts and summary generation status

### Error Handling
- [x] **error-6**: Implement retry logic with max attempts
- [x] **error-7**: Implement exponential backoff for retries
- [x] **error-8**: Handle API rate limit errors gracefully
- [x] **error-9**: Continue schedule even if one account fetch fails
- [x] **error-10**: Handle network errors
- [x] **error-11**: Handle API errors

### Testing
- [x] **error-12**: Test error scenarios (API failure, network error)
- [x] **error-13**: Test retry logic
- [x] **error-14**: Test error logging

## Phase 6: Final Testing & Validation 🔄 IN PROGRESS

- [x] **test-1**: Test database migration with existing data
- [x] **test-2**: Test hybrid fetch with various scenarios
- [x] **test-3**: Test scheduler timing (market hours, after-market, weekends)
- [x] **test-4**: Test holiday detection
- [x] **test-5**: Test error handling and retries
- [x] **test-6**: Test admin page controls
- [ ] **test-7**: Verify API rate limits are respected (6-second delay implemented)
- [x] **test-8**: Test timezone conversion accuracy
- [ ] **test-9**: End-to-end integration test (production-like scenario)
- [ ] **test-10**: Performance testing (load testing, concurrent requests)

## Phase 7: Additional Features & Improvements 🆕

### Database & Data Management
- [x] **feat-1**: Summaries database with deduplication logic
- [x] **feat-2**: Summary timestamp preservation when updating
- [x] **feat-3**: News/trades timestamp improvements (use earliest tweet timestamp)
- [x] **feat-4**: Database viewer (`/view-summaries` page)
- [x] **feat-5**: Clean up state.json references

### UI/UX Improvements
- [x] **feat-6**: Improved timestamp display in admin page (UTC labels)
- [x] **feat-7**: Sequential numbering in summaries viewer
- [ ] **feat-8**: Add search/filter functionality to summaries viewer
- [ ] **feat-9**: Add export functionality (CSV/JSON) for summaries
- [ ] **feat-10**: Add summary detail view (expandable cards)

### Performance & Optimization
- [ ] **feat-11**: Optimize database queries (add indexes if needed)
- [ ] **feat-12**: Implement caching for frequently accessed data
- [ ] **feat-13**: Add pagination to summaries API endpoint
- [ ] **feat-14**: Optimize news/trades parsing performance

### Monitoring & Analytics
- [ ] **feat-15**: Add summary statistics dashboard
- [ ] **feat-16**: Track summary generation success rate
- [ ] **feat-17**: Monitor API usage and rate limits
- [ ] **feat-18**: Add alerting for failed fetches

### Documentation
- [ ] **feat-19**: Update README with new features
- [ ] **feat-20**: Add API documentation
- [ ] **feat-21**: Document database schema
- [ ] **feat-22**: Add deployment guide

## Next Steps (Priority Order)

1. **Complete Phase 6 Testing** (test-7, test-9, test-10)
   - Verify rate limiting is working correctly
   - Run end-to-end integration test
   - Performance testing

2. **Enhance Summaries Viewer** (feat-8, feat-9, feat-10)
   - Add search/filter functionality
   - Add export functionality
   - Improve detail view

3. **Performance Optimization** (feat-11, feat-12, feat-13, feat-14)
   - Database query optimization
   - Caching implementation
   - Pagination improvements

4. **Monitoring & Analytics** (feat-15, feat-16, feat-17, feat-18)
   - Add statistics dashboard
   - Track success rates
   - Add alerting

5. **Documentation** (feat-19, feat-20, feat-21, feat-22)
   - Update README
   - API documentation
   - Deployment guide
