# project/timetrack/models.py
"""Pydantic models for the timetrack application."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field  # type: ignore
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
    notes: List[str] = Field(default_factory=list)


class TimeEntry(BaseModel):
    """
    Represents a single, completed time entry in the log (timelog.json).

    Args:
        start_time (datetime): The start time of the entry.
        end_time (datetime): The end time of the entry.
        activity (str): The name of the logged task.
        duration_minutes (int): The total duration of the task in minutes.
        notes (List[str]): A list of notes for the entry.
    """

    start_time: datetime
    end_time: datetime
    activity: str
    duration_minutes: int
    notes: List[str] = Field(default_factory=list)


class TimeLog(BaseModel):
    """
    Represents the entire log file, containing a list of entries.

    Args:
        entries (List[TimeEntry]): A list of time log entries.
    """

    entries: List[TimeEntry] = Field(default_factory=list)


class Config(BaseModel):
    """
    Represents the configuration file (config.json).

    Args:
        aliases (Dict[str, str]): A mapping of alias names to full activity names.
    """

    aliases: Dict[str, str] = Field(default_factory=dict)


class Memo(BaseModel):
    """
    Represents a single global memo/note.

    Args:
        text (str): The memo content.
        created_at (datetime): When the memo was created.
    """

    text: str
    created_at: datetime


class MemoList(BaseModel):
    """
    Represents the memos file (memos.json).

    Args:
        memos (List[Memo]): A list of global memos.
    """

    memos: List[Memo] = Field(default_factory=list)
