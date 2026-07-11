# project/timetrack/core/tasks.py
"""Task lifecycle management for the timetrack application."""

from datetime import datetime
from typing import Optional, Tuple

from ..models import ApplicationState, TimeEntry
from .storage import Storage
from .utils import format_minutes, truncate_text


class TaskManager:
    """
    Manages task lifecycle: start, stop, pause, resume, status.

    This class handles the real-time tracking of active tasks,
    including pause/resume functionality and duration calculations.
    """

    def __init__(self, storage: Storage):
        """
        Initialize the TaskManager.

        Args:
            storage: The Storage instance for persistence.
        """
        self.storage = storage

    def start(self, activity: str) -> Tuple[bool, str]:
        """
        Starts a new task. Assumes no task is currently running.

        Args:
            activity: The name of the task (already resolved if it was an alias).

        Returns:
            A tuple containing a success flag and a message.
        """
        state = self.storage.read_state()
        if state:
            return (
                False,
                "A task is already running. Use -f or --force to stop it and start a new one.",
            )

        new_state = ApplicationState(activity=activity, start_time=datetime.now())
        self.storage.write_state(new_state)

        return True, f"Started tracking: '{activity}'"

    def stop(self) -> Tuple[bool, str]:
        """
        Stops the current task and logs the time.

        Returns:
            A tuple containing a success flag and a message.
        """
        state = self.storage.read_state()
        if not state:
            return False, "No task is currently running."

        if state.status == "paused":
            # If stopped while paused, the task effectively ended when it was paused.
            if not state.pause_start_time:
                return (
                    False,
                    "Task is paused but has no pause start time. Cannot stop.",
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

        log = self.storage.read_log()
        log.entries.append(log_entry)
        self.storage.write_log(log)

        self.storage.delete_state()
        return (
            True,
            f"Stopped tracking '{log_entry.activity}'. Logged {format_minutes(duration_minutes)}.",
        )

    def pause(self, reason: Optional[str] = None) -> Tuple[bool, str]:
        """
        Pauses the current running task.

        Args:
            reason: An optional reason for pausing.

        Returns:
            A tuple containing a success flag and a message.
        """
        state = self.storage.read_state()
        if not state:
            return False, "No task is running to pause."
        if state.status == "paused":
            return False, f"Task '{state.activity}' is already paused."

        now = datetime.now()

        # Calculate active time before pausing
        active_seconds = (
            now - state.start_time
        ).total_seconds() - state.total_paused_seconds
        active_minutes = round(active_seconds / 60)

        state.status = "paused"
        state.pause_start_time = now
        state.pause_reason = reason.strip() if reason and reason.strip() else None
        self.storage.write_state(state)

        message = (
            f"Paused '{state.activity}'. ({format_minutes(active_minutes)} logged so far)."
        )
        if state.pause_reason:
            message += f" Reason: {state.pause_reason}"

        return True, message

    def resume(self) -> Tuple[bool, str]:
        """
        Resumes the current paused task.

        Returns:
            A tuple containing a success flag and a message.
        """
        state = self.storage.read_state()
        if not state:
            return False, "No task is paused to resume."
        if state.status == "running":
            return False, f"Task '{state.activity}' is already running."

        if not state.pause_start_time:
            # This should not happen if the state is 'paused', but it's a safeguard.
            return False, "Cannot resume task, pause time is not set."

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
        state.pause_reason = None
        self.storage.write_state(state)

        return (
            True,
            f"Resumed tracking: '{state.activity}'. ({format_minutes(active_minutes)} already logged).",
        )

    def status(self) -> str:
        """
        Gets the status of the current task.

        Returns:
            A string describing the current status.
        """
        state = self.storage.read_state()
        if not state:
            return "No task is currently running."

        output = []
        # Truncate activity name for display
        activity_display = truncate_text(state.activity, 50)
        if state.status == "paused":
            # Calculate active time: time from start to pause, minus any previous pauses
            if state.pause_start_time:
                elapsed_seconds = (
                    state.pause_start_time - state.start_time
                ).total_seconds() - state.total_paused_seconds
            else:
                elapsed_seconds = 0
            elapsed_minutes = round(elapsed_seconds / 60)
            paused_line = (
                f"Paused Task: '{activity_display}' ({format_minutes(elapsed_minutes)} logged)"
            )
            if state.pause_reason:
                paused_line += f" - Reason: {state.pause_reason}"
            output.append(paused_line)
        else:
            # For running tasks
            elapsed_seconds = (
                datetime.now() - state.start_time
            ).total_seconds() - state.total_paused_seconds
            elapsed_minutes = round(elapsed_seconds / 60)
            start_time_str = state.start_time.strftime("%H:%M:%S")
            output.append(
                f"Active Task: '{activity_display}' (started at {start_time_str}, {format_minutes(elapsed_minutes)} so far)"
            )

        if state.notes:
            output.append("   Notes:")
            for note in state.notes:
                # Truncate long notes
                note_display = truncate_text(note, 70)
                output.append(f"     - {note_display}")

        return "\n".join(output)

    def add_note(self, note_text: str) -> Tuple[bool, str]:
        """
        Adds a note to the current task.

        Args:
            note_text: The note content.

        Returns:
            A tuple containing a success flag and a message.
        """
        state = self.storage.read_state()
        if not state:
            return False, "No task is currently running."

        state.notes.append(note_text)
        self.storage.write_state(state)
        return True, "Note added."

    def is_running(self) -> bool:
        """
        Checks if a task is currently running.

        Returns:
            True if a task is running, False otherwise.
        """
        return self.storage.read_state() is not None

    def get_current_activity(self) -> str:
        """
        Gets the name of the currently running task.

        Returns:
            The activity name, or empty string if no task is running.
        """
        state = self.storage.read_state()
        return state.activity if state else ""
