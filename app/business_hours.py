"""
Business hours utility functions for scheduling calls.
"""
from datetime import datetime, time, timezone
from typing import Optional, Dict, Any, Tuple
import pytz


def parse_time(time_str: str) -> time:
    """
    Parse time string in HH:MM format.
    
    Args:
        time_str: Time string in HH:MM format
        
    Returns:
        time object
    """
    hour, minute = map(int, time_str.split(':'))
    return time(hour, minute)


def _get_local_time(
    business_hours_config: Dict[str, Any],
    dt: datetime
) -> Tuple[datetime, pytz.tzinfo.BaseTzInfo]:
    """
    Convert a datetime to the campaign's local timezone.
    
    Args:
        business_hours_config: Business hours configuration dict
        dt: Datetime to convert
        
    Returns:
        Tuple of (localized datetime, timezone object)
    """
    # Get timezone
    timezone_str = business_hours_config.get('timezone', 'UTC')
    try:
        tz = pytz.timezone(timezone_str)
    except pytz.UnknownTimeZoneError:
        # Default to UTC if timezone is invalid
        tz = pytz.UTC
    
    # Convert datetime to the campaign's timezone
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    
    local_time = dt.astimezone(tz)
    return local_time, tz


def is_within_business_hours(
    business_hours_config: Optional[Dict[str, Any]],
    check_time: Optional[datetime] = None
) -> bool:
    """
    Check if the given time is within configured business hours.
    
    Args:
        business_hours_config: Business hours configuration dict
        check_time: Time to check (defaults to current UTC time)
        
    Returns:
        True if within business hours or no configuration provided, False otherwise
    """
    if not business_hours_config:
        # No business hours restriction
        return True
    
    if check_time is None:
        check_time = datetime.now(timezone.utc)
    
    # Convert to local timezone
    local_time, tz = _get_local_time(business_hours_config, check_time)
    
    # Get current day of week
    day_name = local_time.strftime('%A').lower()
    
    # Get business hours for this day
    hours_list = business_hours_config.get('hours', [])
    
    for hour_slot in hours_list:
        slot_day = hour_slot.get('day', '').lower()
        if slot_day == day_name:
            start_time = parse_time(hour_slot.get('start', '00:00'))
            end_time = parse_time(hour_slot.get('end', '23:59'))
            
            current_time = local_time.time()
            
            # Check if current time is within this slot
            if start_time <= current_time <= end_time:
                return True
    
    return False


def calculate_next_business_hour(
    business_hours_config: Optional[Dict[str, Any]],
    from_time: Optional[datetime] = None
) -> Optional[datetime]:
    """
    Calculate the next available business hour.
    
    Args:
        business_hours_config: Business hours configuration dict
        from_time: Starting time (defaults to current UTC time)
        
    Returns:
        Next business hour datetime or None if no business hours configured
    """
    if not business_hours_config:
        return from_time or datetime.now(timezone.utc)
    
    if from_time is None:
        from_time = datetime.now(timezone.utc)
    
    # Convert to local timezone
    local_time, tz = _get_local_time(business_hours_config, from_time)
    
    # Try the next 7 days
    for day_offset in range(7):
        day_name = local_time.strftime('%A').lower()
        
        hours_list = business_hours_config.get('hours', [])
        for hour_slot in hours_list:
            slot_day = hour_slot.get('day', '').lower()
            if slot_day == day_name:
                start_time = parse_time(hour_slot.get('start', '00:00'))
                
                # Create datetime for this slot
                next_time = local_time.replace(
                    hour=start_time.hour,
                    minute=start_time.minute,
                    second=0,
                    microsecond=0
                )
                
                if next_time > local_time:
                    return next_time.astimezone(pytz.UTC)
        
        # Move to next day
        local_time = local_time.replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        local_time += timedelta(days=1)
    
    # No business hours found in next 7 days, return original time
    return from_time
