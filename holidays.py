"""
US Market Holidays checker.
Uses hardcoded list of standard US market holidays.
"""
from datetime import datetime, date
from typing import Optional
import pytz


# Standard US Market Holidays (hardcoded list)
# Format: (year, month, day)
US_MARKET_HOLIDAYS = [
    # 2025
    (2025, 1, 1),   # New Year's Day
    (2025, 1, 20),  # Martin Luther King Jr. Day
    (2025, 2, 17),  # Presidents Day
    (2025, 4, 18),  # Good Friday
    (2025, 5, 26),  # Memorial Day
    (2025, 6, 19),  # Juneteenth
    (2025, 7, 4),   # Independence Day
    (2025, 9, 1),   # Labor Day
    (2025, 11, 27), # Thanksgiving
    (2025, 12, 25), # Christmas
    
    # 2026
    (2026, 1, 1),   # New Year's Day
    (2026, 1, 19),  # Martin Luther King Jr. Day
    (2026, 2, 16),  # Presidents Day
    (2026, 4, 3),   # Good Friday
    (2026, 5, 25),  # Memorial Day
    (2026, 6, 19),  # Juneteenth
    (2026, 7, 3),   # Independence Day (observed)
    (2026, 9, 7),   # Labor Day
    (2026, 11, 26), # Thanksgiving
    (2026, 12, 25), # Christmas
    
    # 2027
    (2027, 1, 1),   # New Year's Day
    (2027, 1, 18),  # Martin Luther King Jr. Day
    (2027, 2, 15),  # Presidents Day
    (2027, 3, 26),  # Good Friday
    (2027, 5, 31),  # Memorial Day
    (2027, 6, 18),  # Juneteenth (observed)
    (2027, 7, 5),   # Independence Day (observed)
    (2027, 9, 6),   # Labor Day
    (2027, 11, 25), # Thanksgiving
    (2027, 12, 24), # Christmas (observed)
]


def is_market_holiday(check_date: date) -> bool:
    """
    Check if a given date is a US market holiday.
    
    Args:
        check_date: date object to check
    
    Returns:
        True if the date is a market holiday, False otherwise
    """
    date_tuple = (check_date.year, check_date.month, check_date.day)
    return date_tuple in US_MARKET_HOLIDAYS


def is_weekend(check_date: date) -> bool:
    """
    Check if a given date is a weekend (Saturday or Sunday).
    
    Args:
        check_date: date object to check
    
    Returns:
        True if the date is a weekend, False otherwise
    """
    return check_date.weekday() >= 5  # 5 = Saturday, 6 = Sunday


def should_fetch_today(check_date: Optional[date] = None) -> bool:
    """
    Check if we should fetch tweets today based on weekends and holidays.
    
    Args:
        check_date: date to check (defaults to today in ET timezone)
    
    Returns:
        True if we should fetch (not weekend and not holiday), False otherwise
    """
    if check_date is None:
        # Get current date in ET timezone
        et_tz = pytz.timezone('America/New_York')
        check_date = datetime.now(et_tz).date()
    
    # Don't fetch on weekends
    if is_weekend(check_date):
        return False
    
    # Don't fetch on holidays
    if is_market_holiday(check_date):
        return False
    
    return True


def get_next_trading_day(start_date: Optional[date] = None) -> date:
    """
    Get the next trading day (not weekend, not holiday).
    
    Args:
        start_date: date to start from (defaults to today in ET)
    
    Returns:
        Next trading day date
    """
    if start_date is None:
        et_tz = pytz.timezone('America/New_York')
        start_date = datetime.now(et_tz).date()
    
    next_date = start_date
    while True:
        next_date = date(next_date.year, next_date.month, next_date.day)
        # Move to next day
        from datetime import timedelta
        next_date = next_date + timedelta(days=1)
        
        if should_fetch_today(next_date):
            return next_date

