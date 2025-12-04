"""
Scheduler module for automated tweet fetching and summary generation.
Uses APScheduler to schedule refreshes based on market hours, after-market times, and weekends.
"""
import asyncio
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from config import get_scheduler_config, is_scheduler_enabled, save_scheduler_config
from holidays import should_fetch_today
from database import log_scheduler_event, get_all_accounts
from storage import get_monitored_account_handles


class SchedulerManager:
    """Manages the scheduler for automated tweet fetching."""
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.config = get_scheduler_config()
        # Load paused state from config (persists across restarts)
        self.is_paused = self.config.get("paused", False)
    
    def start(self):
        """Initialize and start the scheduler."""
        if not is_scheduler_enabled():
            print("[INFO] Scheduler is disabled in config.json")
            return
        
        if self.scheduler and self.scheduler.running:
            print("[WARNING] Scheduler is already running")
            return
        
        print("[INFO] Starting scheduler...")
        self.scheduler = AsyncIOScheduler(timezone=pytz.UTC)
        
        # Schedule jobs based on configuration
        self._schedule_market_hours()
        self._schedule_after_market()
        self._schedule_weekends()
        
        self.scheduler.start()
        
        # If we were paused before restart, pause again
        if self.is_paused:
            self.scheduler.pause()
            print("[INFO] Scheduler started in paused state")
        else:
            print("[INFO] Scheduler started successfully")
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            print("[INFO] Scheduler stopped")
    
    def pause(self):
        """Pause the scheduler."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.pause()
            self.is_paused = True
            self._save_pause_state()
            print("[INFO] Scheduler paused")
    
    def resume(self):
        """Resume the scheduler."""
        if not self.scheduler:
            print("[WARNING] Scheduler not initialized")
            return
        
        # Check if scheduler is actually paused (either our state or APScheduler's state)
        # APScheduler state: 1=running, 2=paused
        scheduler_paused = self.scheduler.running and hasattr(self.scheduler, 'state') and self.scheduler.state == 2
        
        if self.is_paused or scheduler_paused:
            self.scheduler.resume()
            self.is_paused = False
            self._save_pause_state()
            print("[INFO] Scheduler resumed")
        else:
            print("[INFO] Scheduler is not paused")
    
    def trigger_now(self):
        """Manually trigger a refresh now."""
        print("[INFO] Manual trigger requested")
        asyncio.create_task(self._scheduled_refresh("manual"))
    
    def _save_pause_state(self):
        """Save pause state to config.json."""
        try:
            save_scheduler_config({"paused": self.is_paused})
        except Exception as e:
            print(f"[WARNING] Failed to save pause state: {e}")
    
    def schedule_test_job(self, seconds_from_now: int = 60):
        """
        Schedule a one-time test job that will run in X seconds.
        Useful for testing scheduler functionality.
        
        Args:
            seconds_from_now: Number of seconds from now to schedule the job (default: 60)
        
        Returns:
            Dict with job info and scheduled time
        """
        if not self.scheduler:
            raise RuntimeError("Scheduler not initialized. Call start() first.")
        
        if not self.scheduler.running:
            raise RuntimeError("Scheduler is not running.")
        
        # Calculate the run time
        run_time = datetime.now(pytz.UTC) + timedelta(seconds=seconds_from_now)
        
        # Schedule a one-time job
        job_id = f"test_job_{datetime.now().timestamp()}"
        self.scheduler.add_job(
            self._scheduled_refresh,
            trigger=DateTrigger(run_date=run_time),
            id=job_id,
            name=f"Test Job (scheduled for {seconds_from_now}s from now)",
            args=("test",),
            replace_existing=False
        )
        
        print(f"[INFO] Test job scheduled to run in {seconds_from_now} seconds (at {run_time})")
        
        return {
            "job_id": job_id,
            "scheduled_time": run_time.isoformat(),
            "seconds_from_now": seconds_from_now,
            "message": f"Test job scheduled to run in {seconds_from_now} seconds"
        }
    
    def get_status(self) -> Dict:
        """Get scheduler status."""
        if not self.scheduler:
            return {
                "enabled": False,
                "running": False,
                "paused": False,
                "next_runs": []
            }
        
        jobs = self.scheduler.get_jobs()
        next_runs = []
        for job in jobs:
            next_runs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
            })
        
        return {
            "enabled": is_scheduler_enabled(),
            "running": self.scheduler.running,
            "paused": self.is_paused,
            "next_runs": next_runs,
            "config": self.config
        }
    
    def _schedule_market_hours(self):
        """Schedule jobs for market hours."""
        market_config = self.config.get("market_hours", {})
        start_time = market_config.get("start", "09:30")
        end_time = market_config.get("end", "16:00")
        interval_minutes = market_config.get("fetch_interval_minutes", 30)
        timezone_str = market_config.get("timezone", "America/New_York")
        
        # Parse start and end times
        start_hour, start_minute = map(int, start_time.split(":"))
        end_hour, end_minute = map(int, end_time.split(":"))
        
        # Get timezone objects
        et_tz = pytz.timezone(timezone_str)
        utc_tz = pytz.UTC
        
        # Create datetime objects in ET timezone for today
        et_now = datetime.now(et_tz)
        today_start_et = et_now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
        today_end_et = et_now.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
        
        # Convert to UTC to get UTC hour range
        today_start_utc = today_start_et.astimezone(utc_tz)
        today_end_utc = today_end_et.astimezone(utc_tz)
        
        start_hour_utc = today_start_utc.hour
        end_hour_utc = today_end_utc.hour
        
        # Handle case where end time might be next day in UTC (e.g., 4 PM ET = 9 PM UTC, but if DST, could be 8 PM UTC)
        # Also handle case where start hour > end hour in UTC (e.g., 9:30 AM ET = 2:30 PM UTC, 4 PM ET = 9 PM UTC)
        # For simplicity, use the ET timezone directly in CronTrigger
        trigger = CronTrigger(
            hour=f"{start_hour}-{end_hour}",
            minute=f"*/{interval_minutes}",
            timezone=et_tz  # Use ET timezone directly instead of UTC
        )
        
        self.scheduler.add_job(
            self._scheduled_refresh,
            trigger=trigger,
            id="market_hours",
            name=f"Market Hours Fetch (every {interval_minutes} min)",
            args=("market_hours",),
            replace_existing=True
        )
        
        print(f"[INFO] Scheduled market hours job (every {interval_minutes} minutes from {start_time} to {end_time} ET)")
    
    def _schedule_after_market(self):
        """Schedule jobs for after-market hours."""
        after_market_config = self.config.get("after_market", {})
        if not after_market_config.get("enabled", True):
            return
        
        times = after_market_config.get("times", ["20:00", "06:00"])
        timezone_str = after_market_config.get("timezone", "America/New_York")
        
        et_tz = pytz.timezone(timezone_str)
        
        for i, time_str in enumerate(times):
            hour, minute = map(int, time_str.split(":"))
            
            # Use ET timezone directly in CronTrigger
            trigger = CronTrigger(
                hour=hour,
                minute=minute,
                timezone=et_tz  # Use ET timezone directly
            )
            
            job_id = f"after_market_{i}"
            self.scheduler.add_job(
                self._scheduled_refresh,
                trigger=trigger,
                id=job_id,
                name=f"After Market Fetch {time_str} ET",
                args=("after_market",),
                replace_existing=True
            )
        
        print(f"[INFO] Scheduled {len(times)} after-market jobs")
    
    def _schedule_weekends(self):
        """Schedule jobs for weekends."""
        weekends_config = self.config.get("weekends", {})
        if not weekends_config.get("enabled", True):
            return
        
        fetch_time = weekends_config.get("fetch_time", "20:00")
        timezone_str = weekends_config.get("timezone", "America/New_York")
        
        hour, minute = map(int, fetch_time.split(":"))
        
        et_tz = pytz.timezone(timezone_str)
        
        # Schedule for Saturday and Sunday using ET timezone directly
        trigger = CronTrigger(
            day_of_week="sat,sun",
            hour=hour,
            minute=minute,
            timezone=et_tz  # Use ET timezone directly
        )
        
        self.scheduler.add_job(
            self._scheduled_refresh,
            trigger=trigger,
            id="weekend",
            name=f"Weekend Fetch {fetch_time} ET",
            args=("weekend",),
            replace_existing=True
        )
        
        print(f"[INFO] Scheduled weekend job ({fetch_time} ET)")
    
    async def _scheduled_refresh(self, fetch_type: str):
        """
        Perform a scheduled refresh.
        This function is called by the scheduler.
        
        Args:
            fetch_type: Type of fetch ("market_hours", "after_market", "weekend", "manual")
        """
        # Check if we should fetch today (skip weekends/holidays for market_hours)
        if fetch_type == "market_hours":
            et_tz = pytz.timezone("America/New_York")
            today = datetime.now(et_tz).date()
            if not should_fetch_today(today):
                print(f"[INFO] Skipping market hours fetch - today is weekend or holiday")
                log_scheduler_event(
                    account_handle=None,
                    fetch_type=fetch_type,
                    status="skipped",
                    error_message=f"Today ({today}) is weekend or holiday"
                )
                return
        
        print(f"[INFO] Starting scheduled refresh (type: {fetch_type})")
        
        # Get accounts
        accounts = get_monitored_account_handles()
        if not accounts:
            print("[WARNING] No accounts to fetch")
            log_scheduler_event(
                account_handle=None,
                fetch_type=fetch_type,
                status="error",
                error_message="No accounts monitored"
            )
            return
        
        # Import refresh logic from main
        try:
            from main import refresh_brief_logic
            
            # Retry logic with exponential backoff
            retry_config = self.config.get("retry", {})
            max_attempts = retry_config.get("max_attempts", 3)
            backoff_seconds = retry_config.get("backoff_seconds", 60)
            
            last_error = None
            for attempt in range(1, max_attempts + 1):
                try:
                    result = await refresh_brief_logic()
                    
                    if result:
                        print(f"[SUCCESS] Scheduled refresh completed successfully (attempt {attempt}/{max_attempts})")
                        log_scheduler_event(
                            account_handle=None,
                            fetch_type=fetch_type,
                            status="success",
                            tweets_fetched=result.get("tweet_count", 0),
                            summary_generated=bool(result.get("summary_id"))
                        )
                        return  # Success, exit retry loop
                    else:
                        print(f"[WARNING] Scheduled refresh returned no result (attempt {attempt}/{max_attempts})")
                        log_scheduler_event(
                            account_handle=None,
                            fetch_type=fetch_type,
                            status="warning",
                            error_message="No result returned",
                            retry_count=attempt - 1
                        )
                        return  # No result but not an error, exit retry loop
                        
                except Exception as e:
                    last_error = e
                    print(f"[ERROR] Scheduled refresh failed (attempt {attempt}/{max_attempts}): {e}")
                    
                    if attempt < max_attempts:
                        # Wait before retry with exponential backoff
                        wait_time = backoff_seconds * (2 ** (attempt - 1))
                        print(f"[INFO] Retrying in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                    else:
                        # Final attempt failed
                        import traceback
                        error_trace = traceback.format_exc()
                        print(f"[ERROR] All retry attempts failed. Last error: {e}")
                        print(f"[ERROR] Traceback:\n{error_trace}")
                        
                        log_scheduler_event(
                            account_handle=None,
                            fetch_type=fetch_type,
                            status="error",
                            error_message=str(e),
                            retry_count=attempt
                        )
            
        except Exception as e:
            print(f"[ERROR] Unexpected error in scheduled refresh: {e}")
            import traceback
            traceback.print_exc()
            
            # Log error
            log_scheduler_event(
                account_handle=None,
                fetch_type=fetch_type,
                status="error",
                error_message=str(e)
            )


# Global scheduler instance
_scheduler_manager: Optional[SchedulerManager] = None


def get_scheduler_manager() -> SchedulerManager:
    """Get or create the global scheduler manager instance."""
    global _scheduler_manager
    if _scheduler_manager is None:
        _scheduler_manager = SchedulerManager()
    return _scheduler_manager

