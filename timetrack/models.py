# project/timetrack/models.py
"""Pydantic models for the timetrack application."""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ApplicationState(BaseModel):
    """
    Represents the current state of the application (state.json).

    Args:
        activity (str): The name of the task being tracked.
        start_time (datetime): The time the task was started.
        status (str): The current status, e.g., 'running' or 'paused'.
        pause_start_time (Optional[datetime]): The time a pause began.
        total_paused_seconds (float): The accumulated time in seconds the task has been paused.
    """

    activity: str
    start_time: datetime
    status: str = "running"
    pause_start_time: Optional[datetime] = None
    total_paused_seconds: float = 0.0


class TimeEntry(BaseModel):
    """
    Represents a single, completed time entry in the log (timelog.json).

    Args:
        date (str): The date of the entry in YYYY-MM-DD format.
        start_time (str): The start time in HH:MM:SS format.
        end_time (str): The end time in HH:MM:SS format.
        activity (str): The name of the logged task.
        duration_minutes (int): The total duration of the task in minutes.
    """

    date: str
    start_time: str
    end_time: str
    activity: str
    duration_minutes: int


class TimeLog(BaseModel):
    """
    Represents the entire log file, containing a list of entries.

    Args:
        entries (List[TimeEntry]): A list of time log entries.
    """

    entries: List[TimeEntry] = Field(default_factory=list)
