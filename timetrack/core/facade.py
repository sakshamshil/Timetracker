# project/timetrack/core/facade.py
"""TimeTracker facade - the main entry point for the application."""

from pathlib import Path
from typing import Optional, Tuple

from ..models import SyncConfig, TimeEntry
from .aliases import AliasManager
from .dashboard import DashboardManager
from .deploy import get_backend
from .entries import EntryManager
from .memos import MemoManager
from .reports import ReportManager
from .storage import Storage
from .tasks import TaskManager
from .updater import UpdateManager


class TimeTracker:
    """
    Facade for the timetrack application.

    This class provides the public API that the CLI uses. It delegates
    to specialized managers for each domain while handling cross-cutting
    concerns like alias resolution and UI decorations (emojis).

    The facade pattern allows:
    - Simple public API (same methods as before)
    - Internal separation of concerns
    - Easy testing with mock managers
    - Centralized handling of cross-domain operations
    """

    def __init__(self):
        """Initialize the TimeTracker with all managers."""
        self._storage = Storage()
        self._tasks = TaskManager(self._storage)
        self._entries = EntryManager(self._storage)
        self._aliases = AliasManager(self._storage)
        self._memos = MemoManager(self._storage)
        self._reports = ReportManager(self._storage)
        self._dashboard = DashboardManager(self._storage)
        self._updater = UpdateManager()

    # =================================
    # TASK LIFECYCLE (delegated to TaskManager)
    # =================================

    def start(self, activity: str, force: bool = False) -> Tuple[bool, str]:
        """
        Starts a new task.

        Args:
            activity: The name of the task or an alias (starting with @).
            force: If True, stops the current task before starting a new one.

        Returns:
            A tuple containing a success flag and a message.
        """
        # Resolve alias if provided
        if activity.startswith("@"):
            resolved = self._aliases.resolve_alias(activity)
            if resolved is None:
                return False, f"❗ Error: Alias '{activity}' not found."
            activity = resolved

        messages = []

        # Handle force stop if a task is running
        if self._tasks.is_running():
            if not force:
                return (
                    False,
                    "❗ Error: A task is already running. Use -f or --force to stop it and start a new one.",
                )

            # Force stop the current task
            stop_success, stop_message = self.stop()
            if stop_success:
                messages.append(stop_message)
            else:
                return (
                    False,
                    f"❗ Error: Could not stop the current task. {stop_message}",
                )

        # Start the new task
        success, message = self._tasks.start(activity)
        if success:
            messages.append(f"🟢 {message}")
        else:
            messages.append(f"❗ {message}")

        return success, "\n".join(messages)

    def stop(self) -> Tuple[bool, str]:
        """
        Stops the current task and logs the time.

        Returns:
            A tuple containing a success flag and a message.
        """
        success, message = self._tasks.stop()
        if success:
            return True, f"✅ {message}"
        return False, f"❗ {message}"

    def pause(self, reason: Optional[str] = None) -> Tuple[bool, str]:
        """
        Pauses the current running task.

        Args:
            reason: An optional reason for pausing.

        Returns:
            A tuple containing a success flag and a message.
        """
        success, message = self._tasks.pause(reason)
        if success:
            return True, f"⏸️ {message}"
        return False, f"❗ {message}"

    def resume(self) -> Tuple[bool, str]:
        """
        Resumes the current paused task.

        Returns:
            A tuple containing a success flag and a message.
        """
        success, message = self._tasks.resume()
        if success:
            return True, f"🟢 {message}"
        return False, f"❗ {message}"

    def status(self) -> str:
        """
        Gets the status of the current task.

        Returns:
            A string describing the current status.
        """
        message = self._tasks.status()
        # Add status emojis based on state
        if "No task" in message:
            return f"⚪ {message}"
        elif "Paused" in message:
            return f"⏸️ {message}"
        else:
            return f"🟢 {message}"

    def add_note(self, note_text: str) -> Tuple[bool, str]:
        """
        Adds a note to the current task.

        Args:
            note_text: The note content.

        Returns:
            A tuple containing a success flag and a message.
        """
        success, message = self._tasks.add_note(note_text)
        if success:
            return True, f"✅ {message}"
        return False, f"⚪ {message}"

    def validate_start_time(self, start_str: str) -> Optional[str]:
        """
        Validates a start time string without creating an entry.

        Args:
            start_str: The start time string to validate.

        Returns:
            An error message string if invalid, or None if valid.
        """
        return self._entries.validate_start_time(start_str)

    def get_last_activity(self) -> Optional[str]:
        """
        Gets the activity name of the last logged entry (or None).

        Returns:
            The activity name, or None if no entries exist.
        """
        return self._entries.get_last_activity()

    def start_previous(self) -> Tuple[bool, str]:
        """
        Starts a new task with the same name as the last logged entry.

        Returns:
            A tuple containing a success flag and a message.
        """
        last_activity = self._entries.get_last_activity()
        if not last_activity:
            return False, "❗ No previous task found to start."
        return self.start(last_activity)

    # =================================
    # ENTRY MANAGEMENT (delegated to EntryManager)
    # =================================

    def get_log(self, day_filter: str) -> str:
        """
        Gets a formatted log for a specific day.

        Args:
            day_filter: 'today', 'yesterday', or a 'DD-MM-YYYY' date.

        Returns:
            A formatted string of the log entries.
        """
        return self._entries.get_log(day_filter)

    def add_entry(
        self,
        activity: str,
        start_str: str,
        end_str: Optional[str],
        duration_str: Optional[str],
    ) -> Tuple[bool, str]:
        """
        Adds a time entry retrospectively.

        Args:
            activity: The name of the task.
            start_str: The start time string.
            end_str: The end time string.
            duration_str: The duration string.

        Returns:
            A tuple containing a success flag and a message.
        """
        success, message = self._entries.add(activity, start_str, end_str, duration_str)
        if success:
            return True, f"✅ {message}"
        return False, f"❗ {message}"

    def backdate_entry(self, duration_str: str, activity: str) -> Tuple[bool, str]:
        """
        Logs a task that just finished by backdating from the current time.

        Args:
            duration_str: The duration of the task (e.g., '1h', '30m').
            activity: The name of the task.

        Returns:
            A tuple containing a success flag and a message.
        """
        success, message = self._entries.backdate(duration_str, activity)
        if success:
            return True, f"✅ {message}"
        return False, f"❗ {message}"

    def remove_entry(
        self, entry_id: int, day_filter: str = "today"
    ) -> Tuple[bool, str]:
        """
        Removes a specific entry from the log by its day-specific ID.

        Args:
            entry_id: The day-specific ID of the entry to remove.
            day_filter: 'today', 'yesterday', or 'DD-MM-YYYY'.

        Returns:
            A tuple containing a success flag and a message.
        """
        success, message = self._entries.remove(entry_id, day_filter)
        if success:
            return True, f"✅ {message}"
        return False, f"❗ {message}"

    def get_entry_by_id(
        self, entry_id: int, day_filter: str = "today"
    ) -> Tuple[Optional[TimeEntry], str]:
        """
        Gets a specific entry from the log by its day-specific ID.

        Args:
            entry_id: The day-specific ID of the entry to retrieve.
            day_filter: 'today', 'yesterday', or 'DD-MM-YYYY'.

        Returns:
            A tuple of (TimeEntry or None, error message).
        """
        entry, message = self._entries.get_by_id(entry_id, day_filter)
        if entry is None:
            return None, f"❗ {message}"
        return entry, message

    def edit_entry(
        self,
        entry_id: int,
        day_filter: str = "today",
        new_activity: Optional[str] = None,
        new_start_str: Optional[str] = None,
        new_end_str: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Edits an existing time entry by its day-specific ID.

        Args:
            entry_id: The day-specific ID of the entry to edit.
            day_filter: 'today', 'yesterday', or 'DD-MM-YYYY'.
            new_activity: New activity name (optional).
            new_start_str: New start time string (optional).
            new_end_str: New end time string (optional).

        Returns:
            A tuple containing a success flag and a message.
        """
        success, message = self._entries.edit(
            entry_id, day_filter, new_activity, new_start_str, new_end_str
        )
        if success:
            return True, f"✅ {message}"
        return False, f"❗ {message}"

    # =================================
    # ALIAS MANAGEMENT (delegated to AliasManager)
    # =================================

    def add_alias(self, alias: str, activity: str) -> Tuple[bool, str]:
        """
        Adds or updates an alias.

        Args:
            alias: The alias name (must start with '@').
            activity: The full activity name.

        Returns:
            A tuple containing a success flag and a message.
        """
        success, message = self._aliases.add(alias, activity)
        if success:
            return True, f"✅ {message}"
        return False, f"❗ {message}"

    def remove_alias(self, alias: str) -> Tuple[bool, str]:
        """
        Removes an alias.

        Args:
            alias: The alias name to remove.

        Returns:
            A tuple containing a success flag and a message.
        """
        success, message = self._aliases.remove(alias)
        if success:
            return True, f"✅ {message}"
        return False, f"❗ {message}"

    def list_aliases(self) -> str:
        """
        Lists all configured aliases.

        Returns:
            A formatted string of all aliases.
        """
        return self._aliases.list_all()

    # =================================
    # MEMO MANAGEMENT (delegated to MemoManager)
    # =================================

    def add_memo(self, text: str) -> Tuple[bool, str]:
        """
        Adds a new global memo.

        Args:
            text: The memo content.

        Returns:
            A tuple containing a success flag and a message.
        """
        success, message = self._memos.add(text)
        if success:
            return True, f"✅ {message}"
        return False, f"❗ {message}"

    def list_memos(self) -> str:
        """
        Lists all global memos.

        Returns:
            A formatted string of all memos.
        """
        return self._memos.list_all()

    def remove_memo(self, memo_id: int) -> Tuple[bool, str]:
        """
        Removes a memo by its ID.

        Args:
            memo_id: The ID of the memo to remove.

        Returns:
            A tuple containing a success flag and a message.
        """
        success, message = self._memos.remove(memo_id)
        if success:
            return True, f"✅ {message}"
        return False, f"❗ {message}"

    def export_memos(self, file_format: str) -> Tuple[bool, str]:
        """
        Exports all global memos to a file.

        Args:
            file_format: The format to export to (csv or xlsx).

        Returns:
            A tuple containing a success flag and a message.
        """
        success, message = self._reports.export_memos(file_format)
        if success:
            return True, f"✅ {message}"
        return False, f"❗ {message}"

    # =================================
    # REPORTS & EXPORT (delegated to ReportManager)
    # =================================

    def export_log(self, file_format: str) -> Tuple[bool, str]:
        """
        Exports the entire time log to a file.

        Args:
            file_format: The format to export to (csv or xlsx).

        Returns:
            A tuple containing a success flag and a message.
        """
        success, message = self._reports.export_log(file_format)
        if success:
            return True, f"✅ {message}"
        return False, message

    def generate_text_report(self, days: int = 7) -> str:
        """
        Generate a text-based report with ASCII bar charts.

        Args:
            days: Number of days to include in the report.

        Returns:
            A formatted string with the report.
        """
        return self._reports.generate_text_report(days)

    def report(self, days: int = 7) -> Tuple[bool, str]:
        """
        Generate a time tracking report.

        Args:
            days: Number of days to include.

        Returns:
            A tuple containing a success flag and a message.
        """
        return self._reports.report(days)

    # =================================
    # DASHBOARD & SYNC
    # =================================

    def get_sync_config(self) -> SyncConfig:
        """Return the current sync configuration."""
        return self._storage.read_config().sync

    def configure_sync(self, **changes) -> Tuple[bool, str]:
        """Persist sync configuration changes.

        Args:
            **changes: Fields of SyncConfig to update (e.g. host, project,
                domain, token, passphrase_protected, passphrase).

        Returns:
            A tuple of (success, message).
        """
        config = self._storage.read_config()
        for key, value in changes.items():
            if hasattr(config.sync, key):
                setattr(config.sync, key, value)
        self._storage.write_config(config)
        return True, "✅ Sync configuration saved."

    def generate_dashboard(
        self, out_dir=None, days: int = 30
    ) -> Tuple[bool, str]:
        """Generate the dashboard HTML locally (no deploy).

        Args:
            out_dir: Directory to write into (defaults to the dashboard dir).
            days: Number of trailing days to include.

        Returns:
            A tuple of (success, message/path).
        """
        from .constants import DASHBOARD_DIR

        target = Path(out_dir) if out_dir else DASHBOARD_DIR
        sync = self.get_sync_config()
        passphrase = sync.passphrase if sync.passphrase_protected else None
        success, message = self._dashboard.generate(target, days, passphrase)
        if success:
            return True, f"✅ Dashboard written to {message}"
        return False, f"❗ {message}"

    def check_sync_ready(self) -> Tuple[bool, str]:
        """Pre-flight check that the deploy backend is usable.

        Returns:
            ``(ok, message)`` — ``ok`` is False with a clear, actionable
            message when the backend cannot deploy (e.g. missing CLI).
        """
        backend = get_backend(self.get_sync_config())
        return backend.preflight()

    def sync(self) -> Tuple[bool, str]:
        """Generate and deploy the dashboard.

        Returns:
            A tuple of (success, message/url).
        """
        if not self.get_sync_config().configured:
            return (
                False,
                "❗ Sync is not set up. Run `track sync` to configure it first.",
            )

        gen_ok, gen_msg = self.generate_dashboard()
        if not gen_ok:
            return gen_ok, gen_msg

        from .constants import DASHBOARD_DIR

        backend = get_backend(self.get_sync_config())
        ok, url = backend.deploy(DASHBOARD_DIR, prod=True)
        if ok:
            return True, f"✅ Dashboard live at: {url}"
        return False, f"❗ Deploy failed: {url}"

    def install_cron(self) -> Tuple[bool, str]:
        """Install a daily scheduled job for `track sync`.

        Returns:
            A tuple of (success, message).
        """
        from . import cron as cron_mod

        ok, message = cron_mod.install()
        if ok:
            config = self._storage.read_config()
            config.sync.cron_installed = True
            self._storage.write_config(config)
        return ok, message

    # =================================
    # UPDATE (delegated to UpdateManager)
    # =================================

    def update(self) -> Tuple[bool, str]:
        """
        Updates the application by pulling latest changes from git and reinstalling.

        Returns:
            A tuple containing a success flag and a message.
        """
        success, message = self._updater.update()
        if success:
            return True, f"✅ {message}"
        return False, f"❗ {message}"
