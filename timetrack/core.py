
# project/timetrack/core.py
"""Core logic for the timetrack application."""

import json
import re
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
from .models import ApplicationState, TimeEntry, TimeLog

# =================================
# CONSTANTS
# =================================
DATA_DIR = Path.home() / ".timetrack"
STATE_FILE = DATA_DIR / "state.json"
LOG_FILE = DATA_DIR / "timelog.json"


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
            return TimeLog.model_validate(log_data)
        except (json.JSONDecodeError, ValueError):
            return TimeLog()

    def _write_log(self, log: TimeLog):
        """Writes the time log to the log file."""
        LOG_FILE.write_text(log.model_dump_json(indent=4))

    def start(self, activity: str) -> Tuple[bool, str]:
        """
        Starts a new task.

        Args:
            activity (str): The name of the task.

        Returns:
            A tuple containing a success flag and a message.
        """
        if self._read_state():
            return False, "❗ Error: A task is already running."

        state = ApplicationState(activity=activity, start_time=datetime.now())
        self._write_state(state)
        return True, f"🟢 Started tracking: '{activity}'"

    def stop(self) -> Tuple[bool, str]:
        """
        Stops the current task and logs the time.

        Returns:
            A tuple containing a success flag and a message.
        """
        state = self._read_state()
        if not state:
            return False, "❗ No task is currently running."

        end_time = datetime.now()

        if state.status == "paused":
            # If stopped while paused, calculate duration up to the pause time
            total_seconds = state.total_paused_seconds
        else:
            # If running, calculate total duration including previous pauses
            total_seconds = (
                end_time - state.start_time
            ).total_seconds() - state.total_paused_seconds

        duration_minutes = round(total_seconds / 60)

        log_entry = TimeEntry(
            date=state.start_time.strftime("%Y-%m-%d"),
            start_time=state.start_time.strftime("%H:%M:%S"),
            end_time=end_time.strftime("%H:%M:%S"),
            activity=state.activity,
            duration_minutes=duration_minutes,
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

        state.status = "paused"
        state.pause_start_time = datetime.now()
        self._write_state(state)
        return True, f"⏸️ Paused '{state.activity}'."

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

        pause_duration = (datetime.now() - state.pause_start_time).total_seconds()
        state.total_paused_seconds += pause_duration
        state.status = "running"
        state.pause_start_time = None
        self._write_state(state)
        return True, f"🟢 Resumed tracking: '{state.activity}'"

    def status(self) -> str:
        """
        Gets the status of the current task.

        Returns:
            A string describing the current status.
        """
        state = self._read_state()
        if not state:
            return "⚪ No task is currently running."

        if state.status == "paused":
            elapsed_seconds = state.total_paused_seconds
            elapsed_minutes = round(elapsed_seconds / 60)
            return (
                f"⏸️ Paused Task: '{state.activity}' ({elapsed_minutes} minutes logged)"
            )

        # For running tasks
        elapsed_seconds = (
            datetime.now() - state.start_time
        ).total_seconds() - state.total_paused_seconds
        elapsed_minutes = round(elapsed_seconds / 60)
        start_time_str = state.start_time.strftime("%H:%M:%S")
        return f"🟢 Active Task: '{state.activity}' (started at {start_time_str}, {elapsed_minutes} minutes so far)"

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

        entries_for_day = [e for e in log.entries if e.date == target_date_str]

        if not entries_for_day:
            return f"No log entries for {target_date.strftime('%Y-%m-%d')}."

        output = [f"--- Time Log for {target_date_str} ---"]
        output.append(
            "{:<10} {:<10} {:<50} {:>10}".format("Start", "End", "Activity", "Duration")
        )
        output.append("-" * 82)

        total_minutes = 0
        for entry in entries_for_day:
            duration_str = f"{entry.duration_minutes} min"
            output.append(
                f"{entry.start_time:<10} {entry.end_time:<10} {entry.activity:<50} {duration_str:>10}"
            )
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

        df = pd.DataFrame([entry.model_dump() for entry in log_data.entries])

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
                df.to_excel(output_path, index=False, engine='openpyxl')
            else:
                return False, f"Unsupported format: {file_format}"
        except Exception as e:
            return False, f"An error occurred during export: {e}"

        return True, f"✅ Successfully exported all data to {output_path}"

    def start_previous(self) -> Tuple[bool, str]:
        """
        Starts a new task based on the last logged activity.

        Returns:
            A tuple containing a success flag and a message.
        """
        if self._read_state():
            return False, "🔴 Error: A task is already running. Please stop it before starting a new one."

        log = self._read_log()
        if not log.entries:
            return False, "🔴 Error: No previous task found in the log. Use 'track start' to begin."

        last_task_name = log.entries[-1].activity
        
        match = re.search(r'(.+) - (\d+)$', last_task_name)
        if match:
            base_name, number = match.groups()
            new_task_name = f"{base_name} - {int(number) + 1}"
        else:
            new_task_name = f"{last_task_name} - 2"
            
        return self.start(new_task_name)
