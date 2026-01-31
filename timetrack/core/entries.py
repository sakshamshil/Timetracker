# project/timetrack/core/entries.py
"""Entry management for the timetrack application."""

from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

from dateutil.parser import parse  # type: ignore

from ..models import TimeEntry
from .storage import Storage
from .utils import format_duration, parse_day_filter, parse_duration, truncate_text


class EntryManager:
    """
    Manages time log entries: add, edit, remove, and retrieve.

    This class handles retrospective entries (add, backdate) and
    modifications to existing entries.
    """

    def __init__(self, storage: Storage):
        """
        Initialize the EntryManager.

        Args:
            storage: The Storage instance for persistence.
        """
        self.storage = storage

    def _get_entries_for_day(
        self, day_filter: str
    ) -> Tuple[List[TimeEntry], Optional[date]]:
        """
        Gets all entries for a specific day, sorted by start time.

        Args:
            day_filter: 'today', 'yesterday', or 'DD-MM-YYYY'.

        Returns:
            A tuple of (list of entries for that day, target date).
            Returns ([], None) if date parsing fails.
        """
        target_date = parse_day_filter(day_filter)
        if target_date is None:
            return [], None

        log = self.storage.read_log()
        target_date_str = target_date.strftime("%Y-%m-%d")

        entries_for_day = sorted(
            [
                e
                for e in log.entries
                if e.start_time.strftime("%Y-%m-%d") == target_date_str
            ],
            key=lambda x: x.start_time,
        )

        return entries_for_day, target_date

    def get_log(self, day_filter: str) -> str:
        """
        Gets a formatted log for a specific day.

        Args:
            day_filter: 'today', 'yesterday', or a 'DD-MM-YYYY' date.

        Returns:
            A formatted string of the log entries.
        """
        log = self.storage.read_log()
        if not log.entries:
            return "No entries found in the log."

        try:
            if day_filter == "today":
                target_date = date.today()
            elif day_filter == "yesterday":
                target_date = date.today() - timedelta(days=1)
            else:
                target_date = datetime.strptime(day_filter, "%d-%m-%Y").date()
        except ValueError:
            return "Error: Invalid date format. Please use DD-MM-YYYY."

        target_date_str = target_date.strftime("%Y-%m-%d")

        entries_for_day = sorted(
            [
                e
                for e in log.entries
                if e.start_time.strftime("%Y-%m-%d") == target_date_str
            ],
            key=lambda x: x.start_time,
        )

        if not entries_for_day:
            return f"No log entries for {target_date.strftime('%Y-%m-%d')}."

        output = [f"--- Time Log for {target_date_str} ---"]
        output.append(
            "{:<5} {:<10} {:<10} {:<45} {:>10}".format(
                "ID", "Start", "End", "Activity", "Duration"
            )
        )
        output.append("-" * 82)

        total_minutes = 0
        for i, entry in enumerate(entries_for_day):
            duration_str = f"{entry.duration_minutes} min"
            # Truncate activity name to fit column
            activity_display = truncate_text(entry.activity, 42)
            output.append(
                f"{i:<5} {entry.start_time.strftime('%H:%M:%S'):<10} {entry.end_time.strftime('%H:%M:%S'):<10} {activity_display:<45} {duration_str:>10}"
            )
            if entry.notes:
                for note in entry.notes:
                    # Truncate long notes
                    note_display = truncate_text(note, 65)
                    output.append(f"      - {note_display}")
            total_minutes += entry.duration_minutes

        output.append("-" * 82)

        hours, remainder_minutes = divmod(total_minutes, 60)
        if hours > 0:
            total_str = f"{int(hours)}h {int(remainder_minutes)}m"
        else:
            total_str = f"{int(remainder_minutes)} minutes"

        output.append(f"Total time for {target_date_str}: {total_str}")

        return "\n".join(output)

    def add(
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
            end_str: The end time string (optional if duration_str provided).
            duration_str: The duration string (optional if end_str provided).

        Returns:
            A tuple containing a success flag and a message.
        """
        today_str = date.today().strftime("%Y-%m-%d")
        yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

        start_str = start_str.lower().replace("today", today_str)
        start_str = start_str.lower().replace("yesterday", yesterday_str)

        if end_str:
            end_str = end_str.lower().replace("today", today_str)
            end_str = end_str.lower().replace("yesterday", yesterday_str)

        try:
            start_time = parse(start_str, dayfirst=True)
        except ValueError:
            return False, "Error: Invalid start time format."

        if end_str:
            try:
                end_time = parse(end_str, dayfirst=True)
            except ValueError:
                return False, "Error: Invalid end time format."
        elif duration_str:
            duration = parse_duration(duration_str)
            if not duration:
                return False, "Error: Invalid duration format. Use '1h' or '30m'."
            end_time = start_time + duration
        else:
            return False, "Error: Either --end or --for must be provided."

        if end_time <= start_time:
            return False, "Error: End time must be after start time."

        duration_minutes = round((end_time - start_time).total_seconds() / 60)

        new_entry = TimeEntry(
            start_time=start_time,
            end_time=end_time,
            activity=activity,
            duration_minutes=duration_minutes,
        )

        log = self.storage.read_log()
        log.entries.append(new_entry)
        log.entries.sort(key=lambda x: x.start_time)
        self.storage.write_log(log)

        return (
            True,
            f"Logged '{activity}' for {format_duration(end_time - start_time)}.",
        )

    def backdate(self, duration_str: str, activity: str) -> Tuple[bool, str]:
        """
        Logs a task that just finished by backdating from the current time.

        Args:
            duration_str: The duration of the task (e.g., '1h', '30m').
            activity: The name of the task.

        Returns:
            A tuple containing a success flag and a message.
        """
        duration = parse_duration(duration_str)
        if not duration:
            return False, "Error: Invalid duration format. Use '1h' or '30m'."

        end_time = datetime.now()
        start_time = end_time - duration
        duration_minutes = round(duration.total_seconds() / 60)

        new_entry = TimeEntry(
            start_time=start_time,
            end_time=end_time,
            activity=activity,
            duration_minutes=duration_minutes,
        )

        log = self.storage.read_log()
        log.entries.append(new_entry)
        log.entries.sort(key=lambda x: x.start_time)
        self.storage.write_log(log)

        return (
            True,
            f"Logged '{activity}' for {format_duration(duration)}.",
        )

    def remove(self, entry_id: int, day_filter: str = "today") -> Tuple[bool, str]:
        """
        Removes a specific entry from the log by its day-specific ID.

        Args:
            entry_id: The day-specific ID of the entry to remove.
            day_filter: 'today', 'yesterday', or 'DD-MM-YYYY'.

        Returns:
            A tuple containing a success flag and a message.
        """
        entries_for_day, target_date = self._get_entries_for_day(day_filter)

        if target_date is None:
            return False, "Error: Invalid date format. Please use DD-MM-YYYY."

        if not entries_for_day:
            return False, f"No entries found for {target_date.strftime('%Y-%m-%d')}."

        if not (0 <= entry_id < len(entries_for_day)):
            return (
                False,
                f"Invalid ID: {entry_id}. Valid IDs for {target_date.strftime('%Y-%m-%d')}: 0-{len(entries_for_day) - 1}.",
            )

        entry_to_remove = entries_for_day[entry_id]

        # Find and remove from the full log by matching start_time
        log = self.storage.read_log()
        log.entries = [
            e for e in log.entries if e.start_time != entry_to_remove.start_time
        ]
        self.storage.write_log(log)

        return True, f"Removed entry: '{entry_to_remove.activity}'"

    def get_by_id(
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
        entries_for_day, target_date = self._get_entries_for_day(day_filter)

        if target_date is None:
            return None, "Error: Invalid date format. Please use DD-MM-YYYY."

        if not entries_for_day:
            return None, f"No entries found for {target_date.strftime('%Y-%m-%d')}."

        if not (0 <= entry_id < len(entries_for_day)):
            return (
                None,
                f"Invalid ID: {entry_id}. Valid IDs for {target_date.strftime('%Y-%m-%d')}: 0-{len(entries_for_day) - 1}.",
            )

        return entries_for_day[entry_id], ""

    def edit(
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
        original_entry, error_msg = self.get_by_id(entry_id, day_filter)

        if not original_entry:
            return False, error_msg

        # Use new values if provided, otherwise keep original values
        activity = new_activity if new_activity is not None else original_entry.activity

        try:
            start_time = (
                parse(new_start_str)
                if new_start_str is not None
                else original_entry.start_time
            )
            end_time = (
                parse(new_end_str)
                if new_end_str is not None
                else original_entry.end_time
            )
        except ValueError:
            return False, "Error: Invalid time format."

        if end_time <= start_time:
            return False, "Error: End time must be after start time."

        duration_minutes = round((end_time - start_time).total_seconds() / 60)

        # Create a new entry with the updated details
        updated_entry = TimeEntry(
            start_time=start_time,
            end_time=end_time,
            activity=activity,
            duration_minutes=duration_minutes,
            notes=original_entry.notes,  # Preserve original notes
        )

        # Find and replace in the full log by matching original start_time
        log = self.storage.read_log()
        for i, entry in enumerate(log.entries):
            if entry.start_time == original_entry.start_time:
                log.entries[i] = updated_entry
                break

        self.storage.write_log(log)

        return True, f"Entry {entry_id} updated."

    def get_last_activity(self) -> Optional[str]:
        """
        Gets the activity name of the last logged entry.

        Returns:
            The activity name, or None if no entries exist.
        """
        log = self.storage.read_log()
        if not log.entries:
            return None
        # The log is sorted by start_time, so the last entry is the most recent
        return log.entries[-1].activity
