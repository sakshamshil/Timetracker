# tests/conftest.py
"""Shared pytest fixtures for the timetrack test suite."""

import pytest
from pathlib import Path
from datetime import datetime, timedelta

from timetrack.core.storage import Storage
from timetrack.core.tasks import TaskManager
from timetrack.core.entries import EntryManager
from timetrack.core.aliases import AliasManager
from timetrack.core.memos import MemoManager
from timetrack.core.reports import ReportManager
from timetrack.core.facade import TimeTracker
from timetrack.models import TimeEntry, TimeLog


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary data directory for testing."""
    data_dir = tmp_path / ".timetrack"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def storage(temp_data_dir):
    """Create a Storage instance with a temporary data directory."""
    return Storage(data_dir=temp_data_dir)


@pytest.fixture
def task_manager(storage):
    """Create a TaskManager instance."""
    return TaskManager(storage)


@pytest.fixture
def entry_manager(storage):
    """Create an EntryManager instance."""
    return EntryManager(storage)


@pytest.fixture
def alias_manager(storage):
    """Create an AliasManager instance."""
    return AliasManager(storage)


@pytest.fixture
def memo_manager(storage):
    """Create a MemoManager instance."""
    return MemoManager(storage)


@pytest.fixture
def report_manager(storage):
    """Create a ReportManager instance."""
    return ReportManager(storage)


@pytest.fixture
def sample_entries(storage):
    """Create sample log entries for testing."""
    now = datetime.now()
    entries = [
        TimeEntry(
            start_time=now - timedelta(hours=3),
            end_time=now - timedelta(hours=2),
            activity="coding",
            duration_minutes=60,
            notes=["Fixed bug #123"],
        ),
        TimeEntry(
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=1, minutes=30),
            activity="meeting",
            duration_minutes=30,
            notes=[],
        ),
        TimeEntry(
            start_time=now - timedelta(hours=1),
            end_time=now - timedelta(minutes=30),
            activity="coding",
            duration_minutes=30,
            notes=["Code review"],
        ),
    ]
    log = TimeLog(entries=entries)
    storage.write_log(log)
    return entries


@pytest.fixture
def sample_entries_multiday(storage):
    """Create sample entries spanning multiple days for report testing."""
    now = datetime.now()
    entries = []

    # Create entries for the last 5 days
    for days_ago in range(5):
        day_start = now - timedelta(days=days_ago)
        entries.append(
            TimeEntry(
                start_time=day_start.replace(hour=9, minute=0, second=0, microsecond=0),
                end_time=day_start.replace(hour=12, minute=0, second=0, microsecond=0),
                activity="project work",
                duration_minutes=180,
                notes=[],
            )
        )
        entries.append(
            TimeEntry(
                start_time=day_start.replace(hour=14, minute=0, second=0, microsecond=0),
                end_time=day_start.replace(hour=15, minute=30, second=0, microsecond=0),
                activity="meetings",
                duration_minutes=90,
                notes=[],
            )
        )

    log = TimeLog(entries=entries)
    storage.write_log(log)
    return entries
