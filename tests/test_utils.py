# tests/test_utils.py
"""Tests for utility functions."""

import pytest
from datetime import date, timedelta

from timetrack.core.utils import (
    parse_duration,
    format_duration,
    truncate_text,
    parse_day_filter,
)


class TestParseDuration:
    """Tests for parse_duration function."""

    def test_parse_hours_only(self):
        result = parse_duration("2h")
        assert result == timedelta(hours=2)

    def test_parse_minutes_only(self):
        result = parse_duration("30m")
        assert result == timedelta(minutes=30)

    def test_parse_hours_and_minutes(self):
        result = parse_duration("1h30m")
        assert result == timedelta(hours=1, minutes=30)

    def test_parse_zero_hours(self):
        result = parse_duration("0h45m")
        assert result == timedelta(minutes=45)

    def test_parse_large_values(self):
        result = parse_duration("10h120m")
        assert result == timedelta(hours=10, minutes=120)

    def test_parse_invalid_format(self):
        result = parse_duration("invalid")
        assert result is None

    def test_parse_empty_string(self):
        result = parse_duration("")
        assert result is None

    def test_parse_no_unit(self):
        result = parse_duration("30")
        assert result is None


class TestFormatDuration:
    """Tests for format_duration function."""

    def test_format_hours_and_minutes(self):
        duration = timedelta(hours=2, minutes=30)
        assert format_duration(duration) == "2h 30m"

    def test_format_hours_only(self):
        duration = timedelta(hours=3)
        assert format_duration(duration) == "3h 0m"

    def test_format_minutes_only(self):
        duration = timedelta(minutes=45)
        assert format_duration(duration) == "45m"

    def test_format_zero_duration(self):
        duration = timedelta()
        assert format_duration(duration) == "0m"

    def test_format_large_duration(self):
        duration = timedelta(hours=25, minutes=30)
        assert format_duration(duration) == "25h 30m"

    def test_format_seconds_rounded(self):
        # 90 seconds = 1.5 minutes, should round to 1 or 2
        duration = timedelta(seconds=90)
        result = format_duration(duration)
        assert result in ["1m", "2m"]


class TestTruncateText:
    """Tests for truncate_text function."""

    def test_no_truncation_needed(self):
        text = "short text"
        result = truncate_text(text, 20)
        assert result == "short text"

    def test_exact_length(self):
        text = "exact"
        result = truncate_text(text, 5)
        assert result == "exact"

    def test_truncation_with_default_suffix(self):
        text = "this is a long text"
        result = truncate_text(text, 10)
        assert result == "this is..."
        assert len(result) == 10

    def test_truncation_with_custom_suffix(self):
        text = "this is a long text"
        result = truncate_text(text, 10, suffix="..")
        assert result == "this is .."
        assert len(result) == 10

    def test_truncation_empty_suffix(self):
        text = "this is a long text"
        result = truncate_text(text, 7, suffix="")
        assert result == "this is"

    def test_empty_text(self):
        result = truncate_text("", 10)
        assert result == ""

    def test_max_length_smaller_than_suffix(self):
        # Edge case: max_length is very small
        # When max_length < len(suffix), the function still appends suffix
        # This is an edge case that could be improved, but we test current behavior
        text = "hello"
        result = truncate_text(text, 2)
        # Current behavior: truncates to negative slice + suffix = "..." or similar
        # The function doesn't specially handle this edge case
        assert result.endswith("...")


class TestParseDayFilter:
    """Tests for parse_day_filter function."""

    def test_parse_today(self):
        result = parse_day_filter("today")
        assert result == date.today()

    def test_parse_yesterday(self):
        result = parse_day_filter("yesterday")
        assert result == date.today() - timedelta(days=1)

    def test_parse_date_format(self):
        result = parse_day_filter("25-12-2024")
        assert result == date(2024, 12, 25)

    def test_parse_another_date(self):
        result = parse_day_filter("01-01-2025")
        assert result == date(2025, 1, 1)

    def test_parse_invalid_format(self):
        result = parse_day_filter("2024-12-25")  # Wrong format (YYYY-MM-DD)
        assert result is None

    def test_parse_invalid_date(self):
        result = parse_day_filter("32-13-2024")  # Invalid day/month
        assert result is None

    def test_parse_empty_string(self):
        result = parse_day_filter("")
        assert result is None

    def test_parse_random_text(self):
        result = parse_day_filter("not a date")
        assert result is None
