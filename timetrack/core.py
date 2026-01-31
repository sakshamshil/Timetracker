# project/timetrack/core.py
"""Core logic for the timetrack application."""

import json
import re
import subprocess
import shutil
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd  # type: ignore
from .models import ApplicationState, TimeEntry, TimeLog, Config, Memo, MemoList
from dateutil.parser import parse  # type: ignore

# =================================
# CONSTANTS
# =================================
DATA_DIR = Path.home() / ".timetrack"
STATE_FILE = DATA_DIR / "state.json"
LOG_FILE = DATA_DIR / "timelog.json"
CONFIG_FILE = DATA_DIR / "config.json"
MEMOS_FILE = DATA_DIR / "memos.json"


class TimeTracker:
    """
    Handles all the core logic for the time tracking application.
    """

    def __init__(self):
        """Initializes the TimeTracker and ensures data directory exists."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _read_state(self) -> Optional[ApplicationState]:
        """Reads and validates the current application state."""
        if not STATE_FILE.exists():
            return None
        try:
            state_data = json.loads(STATE_FILE.read_text())
            return ApplicationState.model_validate(state_data)
        except (json.JSONDecodeError, ValueError):
            return None

    def _write_state(self, state: ApplicationState):
        """Writes the application state to the state file."""
        STATE_FILE.write_text(state.model_dump_json(indent=4))

    def _read_log(self) -> TimeLog:
        """Reads and validates the time log."""
        if not LOG_FILE.exists():
            return TimeLog()
        try:
            log_data = json.loads(LOG_FILE.read_text())
            validated_entries = []
            for entry_data in log_data.get("entries", []):
                if (
                    "start_time" in entry_data
                    and isinstance(entry_data["start_time"], str)
                    and "date" in entry_data
                ):
                    # Old format, try to convert
                    try:
                        start_dt_str = (
                            f"{entry_data['date']} {entry_data['start_time']}"
                        )
                        end_dt_str = f"{entry_data['date']} {entry_data['end_time']}"
                        entry_data["start_time"] = datetime.fromisoformat(start_dt_str)
                        entry_data["end_time"] = datetime.fromisoformat(end_dt_str)
                    except (ValueError, KeyError):
                        continue  # Skip malformed old entries
                validated_entries.append(TimeEntry.model_validate(entry_data))
            return TimeLog(entries=validated_entries)
        except (json.JSONDecodeError, ValueError):
            return TimeLog()

    def _write_log(self, log: TimeLog):
        """Writes the time log to the log file."""
        log.entries.sort(key=lambda x: x.start_time)
        LOG_FILE.write_text(log.model_dump_json(indent=4))

    def _parse_day_filter(self, day_filter: str) -> Optional[date]:
        """
        Parses a day filter string into a date object.

        Args:
            day_filter: 'today', 'yesterday', or 'DD-MM-YYYY'.

        Returns:
            A date object or None if parsing fails.
        """
        try:
            if day_filter == "today":
                return date.today()
            elif day_filter == "yesterday":
                return date.today() - timedelta(days=1)
            else:
                return datetime.strptime(day_filter, "%d-%m-%Y").date()
        except ValueError:
            return None

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
        target_date = self._parse_day_filter(day_filter)
        if target_date is None:
            return [], None

        log = self._read_log()
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

    def start(self, activity: str, force: bool = False) -> Tuple[bool, str]:
        """
        Starts a new task.

        Args:
            activity (str): The name of the task or an alias.
            force (bool): If True, stops the current task before starting a new one.

        Returns:
            A tuple containing a success flag and a message.
        """
        # Resolve alias if provided
        if activity.startswith("@"):
            config = self._read_config()
            if activity not in config.aliases:
                return False, f"❗ Error: Alias '{activity}' not found."
            activity = config.aliases[activity]

        messages = []
        state = self._read_state()
        if state:
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
                # If stop fails, we probably shouldn't proceed.
                return (
                    False,
                    f"❗ Error: Could not stop the current task. {stop_message}",
                )

        # Start the new task
        new_state = ApplicationState(activity=activity, start_time=datetime.now())
        self._write_state(new_state)
        messages.append(f"🟢 Started tracking: '{activity}'")

        return True, "\n".join(messages)

    def stop(self) -> Tuple[bool, str]:
        """
        Stops the current task and logs the time.

        Returns:
            A tuple containing a success flag and a message.
        """
        state = self._read_state()
        if not state:
            return False, "❗ No task is currently running."

        if state.status == "paused":
            # If stopped while paused, the task effectively ended when it was paused.
            if not state.pause_start_time:
                return (
                    False,
                    "❗ Error: Task is paused but has no pause start time. Cannot stop.",
                )
            end_time = state.pause_start_time
            # The total active time is the duration from start to pause, minus previous pauses.
            total_seconds = (
                end_time - state.start_time
            ).total_seconds() - state.total_paused_seconds
        else:
            # If running, calculate total duration up to now.
            end_time = datetime.now()
            total_seconds = (
                end_time - state.start_time
            ).total_seconds() - state.total_paused_seconds

        duration_minutes = round(total_seconds / 60)

        # Safeguard against negative duration
        if duration_minutes < 0:
            duration_minutes = 0

        log_entry = TimeEntry(
            start_time=state.start_time,
            end_time=end_time,
            activity=state.activity,
            duration_minutes=duration_minutes,
            notes=state.notes,
        )

        log = self._read_log()
        log.entries.append(log_entry)
        self._write_log(log)

        STATE_FILE.unlink()
        return (
            True,
            f"✅ Stopped tracking '{log_entry.activity}'. Logged {duration_minutes} minutes.",
        )

    def pause(self) -> Tuple[bool, str]:
        """
        Pauses the current running task.

        Returns:
            A tuple containing a success flag and a message.
        """
        state = self._read_state()
        if not state:
            return False, "❗ No task is running to pause."
        if state.status == "paused":
            return False, f"❗ Task '{state.activity}' is already paused."

        now = datetime.now()

        # Calculate active time before pausing
        active_seconds = (
            now - state.start_time
        ).total_seconds() - state.total_paused_seconds
        active_minutes = round(active_seconds / 60)

        state.status = "paused"
        state.pause_start_time = now
        self._write_state(state)

        return (
            True,
            f"⏸️ Paused '{state.activity}'. ({active_minutes} minutes logged so far).",
        )

    def resume(self) -> Tuple[bool, str]:
        """
        Resumes the current paused task.

        Returns:
            A tuple containing a success flag and a message.
        """
        state = self._read_state()
        if not state:
            return False, "❗ No task is paused to resume."
        if state.status == "running":
            return False, f"❗ Task '{state.activity}' is already running."

        if not state.pause_start_time:
            # This should not happen if the state is 'paused', but it's a safeguard.
            return False, "❗ Error: Cannot resume task, pause time is not set."

        # Calculate active time at the moment of pausing
        active_seconds = (
            state.pause_start_time - state.start_time
        ).total_seconds() - state.total_paused_seconds
        active_minutes = round(active_seconds / 60)

        now = datetime.now()
        pause_duration = (now - state.pause_start_time).total_seconds()
        state.total_paused_seconds += pause_duration
        state.status = "running"
        state.pause_start_time = None
        self._write_state(state)

        return (
            True,
            f"🟢 Resumed tracking: '{state.activity}'. ({active_minutes} minutes already logged).",
        )

    def status(self) -> str:
        """
        Gets the status of the current task.

        Returns:
            A string describing the current status.
        """
        state = self._read_state()
        if not state:
            return "⚪ No task is currently running."

        output = []
        # Truncate activity name for display
        activity_display = self._truncate_text(state.activity, 50)
        if state.status == "paused":
            # Calculate active time: time from start to pause, minus any previous pauses
            if state.pause_start_time:
                elapsed_seconds = (
                    state.pause_start_time - state.start_time
                ).total_seconds() - state.total_paused_seconds
            else:
                elapsed_seconds = 0
            elapsed_minutes = round(elapsed_seconds / 60)
            output.append(
                f"⏸️ Paused Task: '{activity_display}' ({elapsed_minutes} minutes logged)"
            )
        else:
            # For running tasks
            elapsed_seconds = (
                datetime.now() - state.start_time
            ).total_seconds() - state.total_paused_seconds
            elapsed_minutes = round(elapsed_seconds / 60)
            start_time_str = state.start_time.strftime("%H:%M:%S")
            output.append(
                f"🟢 Active Task: '{activity_display}' (started at {start_time_str}, {elapsed_minutes} minutes so far)"
            )

        if state.notes:
            output.append("   Notes:")
            for note in state.notes:
                # Truncate long notes
                note_display = self._truncate_text(note, 70)
                output.append(f"     - {note_display}")

        return "\n".join(output)

    def get_log(self, day_filter: str) -> str:
        """
        Gets a formatted log for a specific day.

        Args:
            day_filter (str): 'today', 'yesterday', or a 'DD-MM-YYYY' date.

        Returns:
            A formatted string of the log entries.
        """
        log = self._read_log()
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
            return "❗ Error: Invalid date format. Please use DD-MM-YYYY."

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
            activity_display = self._truncate_text(entry.activity, 42)
            output.append(
                f"{i:<5} {entry.start_time.strftime('%H:%M:%S'):<10} {entry.end_time.strftime('%H:%M:%S'):<10} {activity_display:<45} {duration_str:>10}"
            )
            if entry.notes:
                for note in entry.notes:
                    # Truncate long notes
                    note_display = self._truncate_text(note, 65)
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

    def export_log(self, file_format: str) -> Tuple[bool, str]:
        """
        Exports the entire time log to a file.

        Args:
            file_format (str): The format to export to (csv or xlsx).

        Returns:
            A tuple containing a success flag and a message.
        """
        log_data = self._read_log()
        if not log_data.entries:
            return False, "No log entries to export."

        processed_entries = []
        for entry in log_data.entries:
            entry_dict = entry.model_dump()
            entry_dict["notes"] = "\n".join(entry.notes) if entry.notes else ""
            processed_entries.append(entry_dict)

        df = pd.DataFrame(processed_entries)

        # Define the output directory and create it if it doesn't exist
        project_dir = Path(__file__).parent.parent
        output_dir = project_dir / "exports"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create a timestamp for the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"timetrack_export_{timestamp}.{file_format}"
        output_path = output_dir / output_filename

        try:
            if file_format == "csv":
                df.to_csv(output_path, index=False)
            elif file_format == "xlsx":
                df.to_excel(output_path, index=False, engine="openpyxl")
            else:
                return False, f"Unsupported format: {file_format}"
        except Exception as e:
            return False, f"An error occurred during export: {e}"

        return True, f"✅ Successfully exported all data to {output_path}"

    def remove_entry(
        self, entry_id: int, day_filter: str = "today"
    ) -> Tuple[bool, str]:
        """
        Removes a specific entry from the log by its day-specific ID.

        Args:
            entry_id (int): The day-specific ID of the entry to remove.
            day_filter (str): 'today', 'yesterday', or 'DD-MM-YYYY'.

        Returns:
            A tuple containing a success flag and a message.
        """
        entries_for_day, target_date = self._get_entries_for_day(day_filter)

        if target_date is None:
            return False, "❗ Error: Invalid date format. Please use DD-MM-YYYY."

        if not entries_for_day:
            return False, f"❗ No entries found for {target_date.strftime('%Y-%m-%d')}."

        if not (0 <= entry_id < len(entries_for_day)):
            return (
                False,
                f"❗ Invalid ID: {entry_id}. Valid IDs for {target_date.strftime('%Y-%m-%d')}: 0-{len(entries_for_day) - 1}.",
            )

        entry_to_remove = entries_for_day[entry_id]

        # Find and remove from the full log by matching start_time
        log = self._read_log()
        log.entries = [
            e for e in log.entries if e.start_time != entry_to_remove.start_time
        ]
        self._write_log(log)

        return True, f"✅ Removed entry: '{entry_to_remove.activity}'"

    def get_entry_by_id(
        self, entry_id: int, day_filter: str = "today"
    ) -> Tuple[Optional[TimeEntry], str]:
        """
        Gets a specific entry from the log by its day-specific ID.

        Args:
            entry_id (int): The day-specific ID of the entry to retrieve.
            day_filter (str): 'today', 'yesterday', or 'DD-MM-YYYY'.

        Returns:
            A tuple of (TimeEntry or None, error message).
        """
        entries_for_day, target_date = self._get_entries_for_day(day_filter)

        if target_date is None:
            return None, "❗ Error: Invalid date format. Please use DD-MM-YYYY."

        if not entries_for_day:
            return None, f"❗ No entries found for {target_date.strftime('%Y-%m-%d')}."

        if not (0 <= entry_id < len(entries_for_day)):
            return (
                None,
                f"❗ Invalid ID: {entry_id}. Valid IDs for {target_date.strftime('%Y-%m-%d')}: 0-{len(entries_for_day) - 1}.",
            )

        return entries_for_day[entry_id], ""

    def edit_entry(
        self,
        entry_id: int,
        day_filter: str = "today",
        new_activity: Optional[str] = None,
        new_start_str: Optional[str] = None,
        new_end_str: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Edits an existing time entry by its day-specific ID."""
        original_entry, error_msg = self.get_entry_by_id(entry_id, day_filter)

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
            return False, "❗ Error: Invalid time format."

        if end_time <= start_time:
            return False, "❗ Error: End time must be after start time."

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
        log = self._read_log()
        for i, entry in enumerate(log.entries):
            if entry.start_time == original_entry.start_time:
                log.entries[i] = updated_entry
                break

        self._write_log(log)

        return True, f"✅ Entry {entry_id} updated."

    def add_note(self, note_text: str) -> Tuple[bool, str]:
        """Adds a note to the current task."""
        state = self._read_state()
        if not state:
            return False, "⚪ No task is currently running."

        state.notes.append(note_text)
        self._write_state(state)
        return True, "✅ Note added."

    def start_previous(self) -> Tuple[bool, str]:
        """
        Starts a new task with the same name as the last logged entry.

        Returns:
            A tuple containing a success flag and a message.
        """
        log = self._read_log()
        if not log.entries:
            return False, "❗ No previous task found to start."

        # The log is sorted by start_time, so the last entry is the most recent
        last_activity = log.entries[-1].activity
        return self.start(last_activity)

    def _parse_duration(self, duration_str: str) -> Optional[timedelta]:
        """Parses a duration string like '1h30m' into a timedelta."""
        match = re.match(r"((?P<hours>\d+)h)?((?P<minutes>\d+)m)?", duration_str)
        if not match:
            return None
        parts = match.groupdict()
        time_params = {}
        for name, param in parts.items():
            if param:
                time_params[name] = int(param)
        return timedelta(**time_params)

    def _format_duration(self, duration: timedelta) -> str:
        """Formats a timedelta into a human-readable string."""
        total_minutes = int(duration.total_seconds() / 60)
        hours, minutes = divmod(total_minutes, 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    def _truncate_text(self, text: str, max_length: int, suffix: str = "...") -> str:
        """Truncates text to max_length, adding suffix if truncated."""
        if len(text) <= max_length:
            return text
        return text[: max_length - len(suffix)] + suffix

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
            activity (str): The name of the task.
            start_str (str): The start time string.
            end_str (Optional[str]): The end time string.
            duration_str (Optional[str]): The duration string.

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
            return False, "❗ Error: Invalid start time format."

        if end_str:
            try:
                end_time = parse(end_str, dayfirst=True)
            except ValueError:
                return False, "❗ Error: Invalid end time format."
        elif duration_str:
            duration = self._parse_duration(duration_str)
            if not duration:
                return False, "❗ Error: Invalid duration format. Use '1h' or '30m'."
            end_time = start_time + duration
        else:
            return False, "❗ Error: Either --end or --for must be provided."

        if end_time <= start_time:
            return False, "❗ Error: End time must be after start time."

        duration_minutes = round((end_time - start_time).total_seconds() / 60)

        new_entry = TimeEntry(
            start_time=start_time,
            end_time=end_time,
            activity=activity,
            duration_minutes=duration_minutes,
        )

        log = self._read_log()
        log.entries.append(new_entry)
        log.entries.sort(key=lambda x: x.start_time)
        self._write_log(log)

        return (
            True,
            f"✅ Logged '{activity}' for {self._format_duration(end_time - start_time)}.",
        )

    def backdate_entry(self, duration_str: str, activity: str) -> Tuple[bool, str]:
        """
        Logs a task that just finished by backdating from the current time.

        Args:
            duration_str (str): The duration of the task (e.g., '1h', '30m').
            activity (str): The name of the task.

        Returns:
            A tuple containing a success flag and a message.
        """
        duration = self._parse_duration(duration_str)
        if not duration:
            return False, "❗ Error: Invalid duration format. Use '1h' or '30m'."

        end_time = datetime.now()
        start_time = end_time - duration
        duration_minutes = round(duration.total_seconds() / 60)

        new_entry = TimeEntry(
            start_time=start_time,
            end_time=end_time,
            activity=activity,
            duration_minutes=duration_minutes,
        )

        log = self._read_log()
        log.entries.append(new_entry)
        log.entries.sort(key=lambda x: x.start_time)
        self._write_log(log)

        return (
            True,
            f"✅ Logged '{activity}' for {self._format_duration(duration)}.",
        )

    def _read_config(self) -> Config:
        """Reads and validates the configuration file."""
        if not CONFIG_FILE.exists():
            return Config()
        try:
            config_data = json.loads(CONFIG_FILE.read_text())
            return Config.model_validate(config_data)
        except (json.JSONDecodeError, ValueError):
            return Config()

    def _write_config(self, config: Config):
        """Writes the configuration to the config file."""
        CONFIG_FILE.write_text(config.model_dump_json(indent=4))

    def add_alias(self, alias: str, activity: str) -> Tuple[bool, str]:
        """Adds or updates an alias."""
        if not alias.startswith("@"):
            return False, "❗ Error: Alias must start with '@'."

        config = self._read_config()
        config.aliases[alias] = activity
        self._write_config(config)

        return True, f"✅ Alias '{alias}' set to '{activity}'."

    def remove_alias(self, alias: str) -> Tuple[bool, str]:
        """Removes an alias."""
        config = self._read_config()
        if alias not in config.aliases:
            return False, f"❗ Error: Alias '{alias}' not found."

        del config.aliases[alias]
        self._write_config(config)

        return True, f"✅ Alias '{alias}' removed."

    def list_aliases(self) -> str:
        """Lists all aliases."""
        config = self._read_config()
        if not config.aliases:
            return "No aliases defined."

        output = ["--- Configured Aliases ---"]
        for alias, activity in config.aliases.items():
            output.append(f"{alias} -> {activity}")

        return "\n".join(output)

    def _read_memos(self) -> MemoList:
        """Reads and validates the memos file."""
        if not MEMOS_FILE.exists():
            return MemoList()
        try:
            memos_data = json.loads(MEMOS_FILE.read_text())
            return MemoList.model_validate(memos_data)
        except (json.JSONDecodeError, ValueError):
            return MemoList()

    def _write_memos(self, memos: MemoList):
        """Writes the memos to the memos file."""
        MEMOS_FILE.write_text(memos.model_dump_json(indent=4))

    def add_memo(self, text: str) -> Tuple[bool, str]:
        """
        Adds a new global memo.

        Args:
            text (str): The memo content.

        Returns:
            A tuple containing a success flag and a message.
        """
        memo = Memo(text=text, created_at=datetime.now())
        memos = self._read_memos()
        memos.memos.append(memo)
        self._write_memos(memos)

        return True, "✅ Memo added."

    def list_memos(self) -> str:
        """
        Lists all global memos.

        Returns:
            A formatted string of all memos.
        """
        memos = self._read_memos()
        if not memos.memos:
            return "No memos found."

        output = ["--- Memos ---"]
        output.append("{:<5} {:<20} {}".format("ID", "Created", "Note"))
        output.append("-" * 70)

        for i, memo in enumerate(memos.memos):
            created_str = memo.created_at.strftime("%Y-%m-%d %H:%M")
            # Truncate long memos for display
            display_text = self._truncate_text(memo.text, 45)
            output.append(f"{i:<5} {created_str:<20} {display_text}")

        output.append("-" * 70)

        return "\n".join(output)

    def remove_memo(self, memo_id: int) -> Tuple[bool, str]:
        """
        Removes a memo by its ID.

        Args:
            memo_id (int): The ID of the memo to remove.

        Returns:
            A tuple containing a success flag and a message.
        """
        memos = self._read_memos()

        if not memos.memos:
            return False, "❗ No memos found."

        if not (0 <= memo_id < len(memos.memos)):
            return (
                False,
                f"❗ Invalid ID: {memo_id}. Valid IDs: 0-{len(memos.memos) - 1}.",
            )

        removed_memo = memos.memos.pop(memo_id)
        self._write_memos(memos)

        # Truncate for display
        display_text = self._truncate_text(removed_memo.text, 30)
        return True, f"✅ Memo removed: '{display_text}'"

    def _check_remote_exists(self, repo_dir: Path) -> Tuple[bool, str]:
        """Check if git remote 'origin' exists."""
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
            )
            return result.returncode == 0, result.stdout.strip()
        except Exception:
            return False, ""

    def _add_remote(self, repo_dir: Path, remote_url: str) -> Tuple[bool, str]:
        """Add git remote 'origin'."""
        try:
            result = subprocess.run(
                ["git", "remote", "add", "origin", remote_url],
                cwd=repo_dir,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return True, "✅ Added remote origin."
            return False, f"❗ Failed to add remote: {result.stderr}"
        except Exception as e:
            return False, f"❗ Error adding remote: {e}"

    def _detect_installation_method(self) -> str:
        """Detect how track was originally installed."""
        # Check if installed via pipx
        try:
            result = subprocess.run(
                ["pipx", "list"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and "timetrack-cli" in result.stdout:
                return "pipx"
            if result.returncode == 0 and "track" in result.stdout:
                return "pipx"
        except Exception:
            pass

        # Check if installed via pip (editable)
        try:
            pip_cmd = shutil.which("pip3") or shutil.which("pip")
            if pip_cmd:
                result = subprocess.run(
                    [pip_cmd, "show", "timetrack-cli"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    # Check if it's an editable install
                    if "Editable project location" in result.stdout:
                        return "pip-editable"
                    return "pip"
        except Exception:
            pass

        # Default to pipx if available
        if shutil.which("pipx"):
            return "pipx"

        return "pip"

    def update(self) -> Tuple[bool, str]:
        """
        Updates the application by pulling latest changes from git and reinstalling.

        Uses fail-closed error handling: stops at first error with a meaningful message.

        Returns:
            A tuple containing a success flag and a message.
        """
        # Step 1: Find the repo directory
        repo_dir = Path(__file__).parent.parent

        # Step 2: Verify git is installed
        if not shutil.which("git"):
            # Offer alternative: pip install upgrade
            pip_cmd = shutil.which("pip3") or shutil.which("pip")
            if pip_cmd:
                try:
                    result = subprocess.run(
                        [pip_cmd, "install", "--upgrade", "timetrack-cli"],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode == 0:
                        return (
                            True,
                            "✅ Updated via pip (PyPI). Run 'track --version' to verify.",
                        )
                except Exception:
                    pass
            return (
                False,
                "❗ Error: git is not installed or not in PATH.\nFor PyPI installs, run: pip install --upgrade timetrack-cli",
            )

        # Step 3: Verify this is a git repository
        git_dir = repo_dir / ".git"
        if not git_dir.exists():
            # This is likely a PyPI install, suggest pip upgrade
            return (
                False,
                "❗ This appears to be a PyPI installation (not a git clone).\n"
                "To update, run: pip install --upgrade timetrack-cli\n"
                "Or reinstall with: pipx reinstall timetrack-cli",
            )

        # Step 4: Check for uncommitted changes that might cause conflicts
        try:
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
            )
            if status_result.returncode != 0:
                return (
                    False,
                    f"❗ Error: Failed to check git status.\n{status_result.stderr}",
                )

            if status_result.stdout.strip():
                return (
                    False,
                    "❗ Error: You have uncommitted changes. Please commit or stash them first.",
                )
        except Exception as e:
            return False, f"❗ Error: Failed to run git status: {e}"

        # Step 5: Check if remote exists, add if missing
        remote_exists, remote_url = self._check_remote_exists(repo_dir)
        if not remote_exists:
            default_remote = "https://github.com/sakshamshil/Timetracker.git"
            success, msg = self._add_remote(repo_dir, default_remote)
            if not success:
                return (
                    False,
                    f"❗ No git remote configured and failed to add default.\n{msg}",
                )

        # Step 6: Pull latest changes
        try:
            pull_result = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
            )
            if pull_result.returncode != 0:
                return False, f"❗ Error: git pull failed.\n{pull_result.stderr}"

            pull_output = pull_result.stdout.strip()
        except Exception as e:
            return False, f"❗ Error: Failed to run git pull: {e}"

        # Step 7: Detect installation method and reinstall appropriately
        install_method = self._detect_installation_method()

        if install_method == "pipx":
            # Try both package names
            try:
                # First try timetrack-cli (PyPI name)
                reinstall_result = subprocess.run(
                    ["pipx", "reinstall", "timetrack-cli"],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                )
                if reinstall_result.returncode != 0:
                    # Fallback to local editable install
                    reinstall_result = subprocess.run(
                        ["pipx", "install", "-e", ".", "--force"],
                        cwd=repo_dir,
                        capture_output=True,
                        text=True,
                    )
                    if reinstall_result.returncode != 0:
                        return (
                            False,
                            f"❗ Error: pipx reinstall failed.\n{reinstall_result.stderr}",
                        )
            except Exception as e:
                return False, f"❗ Error: Failed to run pipx reinstall: {e}"
        elif install_method in ["pip", "pip-editable"]:
            pip_cmd = shutil.which("pip3") or shutil.which("pip")
            if not pip_cmd:
                return False, "❗ Error: pip not found in PATH."

            try:
                reinstall_result = subprocess.run(
                    [pip_cmd, "install", "-e", "."],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                )
                if reinstall_result.returncode != 0:
                    return (
                        False,
                        f"❗ Error: pip install failed.\n{reinstall_result.stderr}",
                    )
            except Exception as e:
                return False, f"❗ Error: Failed to run pip install: {e}"
        else:
            return (
                False,
                "❗ Error: Could not detect installation method.\nTry: pipx install -e . or pip install -e .",
            )

        # Success!
        if "Already up to date" in pull_output:
            return True, "✅ Already up to date. No changes to pull."
        else:
            return True, f"✅ Updated successfully!\n{pull_output}"

    # =================================
    # REPORTING METHODS
    # =================================

    def generate_text_report(self, days: int = 7) -> str:
        """
        Generate a text-based report with ASCII bar charts.

        Args:
            days (int): Number of days to include in the report (default: 7).

        Returns:
            A formatted string with the report.
        """
        log = self._read_log()
        if not log.entries:
            return "No entries found in the log."

        # Get entries from the last N days
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        # Group by date and activity
        daily_hours = {}
        activity_hours = {}

        for entry in log.entries:
            entry_date = entry.start_time.date()
            if start_date <= entry_date <= end_date:
                # Daily totals
                date_str = entry_date.strftime("%Y-%m-%d")
                hours = entry.duration_minutes / 60
                daily_hours[date_str] = daily_hours.get(date_str, 0) + hours

                # Activity totals
                activity = entry.activity
                activity_hours[activity] = activity_hours.get(activity, 0) + hours

        if not daily_hours:
            return f"No entries found in the last {days} days."

        output = []
        output.append("=" * 60)
        output.append(f"     Time Report - Last {days} Days")
        output.append("=" * 60)
        output.append("")

        # Daily breakdown with bar chart
        output.append("📅 Daily Hours:")
        output.append("-" * 60)

        max_hours = max(daily_hours.values()) if daily_hours else 1
        bar_width = 30

        for date_str in sorted(daily_hours.keys()):
            hours = daily_hours[date_str]
            bar_length = int((hours / max_hours) * bar_width) if max_hours > 0 else 0
            bar = "█" * bar_length + "░" * (bar_width - bar_length)
            output.append(f"{date_str} │{bar}│ {hours:.1f}h")

        output.append("")

        # Activity breakdown
        output.append("📊 Activity Breakdown:")
        output.append("-" * 60)

        # Sort activities by hours (descending)
        sorted_activities = sorted(
            activity_hours.items(), key=lambda x: x[1], reverse=True
        )

        max_activity_hours = max(activity_hours.values()) if activity_hours else 1
        activity_bar_width = 25

        for activity, hours in sorted_activities:
            bar_length = (
                int((hours / max_activity_hours) * activity_bar_width)
                if max_activity_hours > 0
                else 0
            )
            bar = "█" * bar_length + "░" * (activity_bar_width - bar_length)
            activity_display = self._truncate_text(activity, 20)
            output.append(f"{activity_display:<20} │{bar}│ {hours:.1f}h")

        # Summary statistics
        total_hours = sum(daily_hours.values())
        avg_hours = total_hours / len(daily_hours) if daily_hours else 0

        output.append("")
        output.append("📈 Summary:")
        output.append("-" * 60)
        output.append(f"Total hours: {total_hours:.1f}h")
        output.append(f"Average per day: {avg_hours:.1f}h")
        output.append(f"Days tracked: {len(daily_hours)}")
        output.append(f"Activities: {len(activity_hours)}")
        output.append("=" * 60)

        return "\n".join(output)

    def generate_html_report(self, days: int = 30) -> Tuple[bool, str]:
        """
        Generate an HTML report with charts.

        Args:
            days (int): Number of days to include in the report (default: 30).

        Returns:
            A tuple containing a success flag and a message.
        """
        log = self._read_log()
        if not log.entries:
            return False, "No entries found in the log."

        # Get entries from the last N days
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        # Group by date and activity
        daily_data = {}
        activity_data = {}

        for entry in log.entries:
            entry_date = entry.start_time.date()
            if start_date <= entry_date <= end_date:
                date_str = entry_date.strftime("%Y-%m-%d")
                hours = entry.duration_minutes / 60
                daily_data[date_str] = daily_data.get(date_str, 0) + hours

                activity = entry.activity
                activity_data[activity] = activity_data.get(activity, 0) + hours

        if not daily_data:
            return False, f"No entries found in the last {days} days."

        # Prepare data for charts
        dates = sorted(daily_data.keys())
        hours_per_day = [daily_data[d] for d in dates]

        # Top activities (limit to top 10)
        sorted_activities = sorted(
            activity_data.items(), key=lambda x: x[1], reverse=True
        )[:10]
        activity_labels = [a[0] for a in sorted_activities]
        activity_values = [a[1] for a in sorted_activities]

        # Calculate statistics
        total_hours = sum(daily_data.values())
        avg_hours = total_hours / len(daily_data) if daily_data else 0

        # Generate HTML
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Time Tracking Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        h1 {{
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #4CAF50;
        }}
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .chart-title {{
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 15px;
            color: #333;
        }}
        .date-range {{
            text-align: center;
            color: #666;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <h1>📊 Time Tracking Report</h1>
    <div class="date-range">
        {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}
    </div>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-value">{total_hours:.1f}h</div>
            <div class="stat-label">Total Hours</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{avg_hours:.1f}h</div>
            <div class="stat-label">Average per Day</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{len(daily_data)}</div>
            <div class="stat-label">Days Tracked</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{len(activity_data)}</div>
            <div class="stat-label">Activities</div>
        </div>
    </div>

    <div class="chart-container">
        <div class="chart-title">Daily Hours</div>
        <canvas id="dailyChart"></canvas>
    </div>

    <div class="chart-container">
        <div class="chart-title">Time by Activity (Top 10)</div>
        <canvas id="activityChart"></canvas>
    </div>

    <script>
        // Daily hours chart
        const dailyCtx = document.getElementById('dailyChart').getContext('2d');
        new Chart(dailyCtx, {{
            type: 'bar',
            data: {{
                labels: {dates},
                datasets: [{{
                    label: 'Hours',
                    data: {hours_per_day},
                    backgroundColor: 'rgba(76, 175, 80, 0.6)',
                    borderColor: 'rgba(76, 175, 80, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Hours'
                        }}
                    }}
                }}
            }}
        }});

        // Activity pie chart
        const activityCtx = document.getElementById('activityChart').getContext('2d');
        new Chart(activityCtx, {{
            type: 'doughnut',
            data: {{
                labels: {activity_labels},
                datasets: [{{
                    data: {activity_values},
                    backgroundColor: [
                        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
                        '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384'
                    ]
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        position: 'right'
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""

        # Save HTML file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_dir = Path(__file__).parent.parent
        output_dir = project_dir / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"timetrack_report_{timestamp}.html"
        output_path.write_text(html_content)

        return True, f"✅ Report generated: {output_path}"

    def report(self, format: str = "text", days: int = 7) -> Tuple[bool, str]:
        """
        Generate a time tracking report.

        Args:
            format (str): Report format ('text' or 'html').
            days (int): Number of days to include.

        Returns:
            A tuple containing a success flag and a message.
        """
        if format == "html":
            # Use 30 days default for HTML reports
            return self.generate_html_report(days if days != 7 else 30)
        else:
            report_text = self.generate_text_report(days)
            return True, report_text
