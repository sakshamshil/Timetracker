# project/timetrack/core/utils.py
"""Utility functions for the timetrack application."""

import re
from datetime import date, timedelta
from typing import Optional


def parse_duration(duration_str: str) -> Optional[timedelta]:
    """
    Parses a duration string like '1h30m' into a timedelta.

    Args:
        duration_str: A string like '1h', '30m', or '1h30m'.

    Returns:
        A timedelta object or None if parsing fails.
    """
    match = re.match(r"((?P<hours>\d+)h)?((?P<minutes>\d+)m)?", duration_str)
    if not match:
        return None
    parts = match.groupdict()
    time_params = {}
    for name, param in parts.items():
        if param:
            time_params[name] = int(param)
    if not time_params:
        return None
    return timedelta(**time_params)


def format_duration(duration: timedelta) -> str:
    """
    Formats a timedelta into a human-readable string.

    Args:
        duration: A timedelta object.

    Returns:
        A formatted string like '1h 30m' or '30m'.
    """
    total_minutes = int(duration.total_seconds() / 60)
    hours, minutes = divmod(total_minutes, 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncates text to max_length, adding suffix if truncated.

    Args:
        text: The text to truncate.
        max_length: Maximum length of the result.
        suffix: Suffix to add when truncating (default: "...").

    Returns:
        The truncated text.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def parse_day_filter(day_filter: str) -> Optional[date]:
    """
    Parses a day filter string into a date object.

    Args:
        day_filter: 'today', 'yesterday', or 'DD-MM-YYYY'.

    Returns:
        A date object or None if parsing fails.
    """
    from datetime import datetime

    try:
        if day_filter == "today":
            return date.today()
        elif day_filter == "yesterday":
            return date.today() - timedelta(days=1)
        else:
            return datetime.strptime(day_filter, "%d-%m-%Y").date()
    except ValueError:
        return None
