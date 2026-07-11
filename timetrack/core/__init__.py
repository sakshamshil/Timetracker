# project/timetrack/core/__init__.py
"""Core package for the timetrack application.

This package contains the refactored core logic, organized as follows:

- constants.py: Data directory and file paths
- utils.py: Utility functions (parsing, formatting, truncation)
- storage.py: Storage class for all file I/O operations
- aliases.py: AliasManager for task alias management
- memos.py: MemoManager for global memos
- tasks.py: TaskManager for task lifecycle (start/stop/pause/resume)
- entries.py: EntryManager for log entry management
- reports.py: ReportManager for reports and exports
- dashboard.py: DashboardManager for self-contained HTML dashboard
- deploy.py: DeployBackend (Vercel) for publishing the dashboard
- cron.py: scheduled-job installer (launchd/crontab)
- updater.py: UpdateManager for self-update functionality
- facade.py: TimeTracker facade that delegates to all managers

Usage:
    from timetrack.core import TimeTracker
    tracker = TimeTracker()
    tracker.start("my task")
"""

from .facade import TimeTracker
from .storage import Storage

__all__ = ["TimeTracker", "Storage"]
