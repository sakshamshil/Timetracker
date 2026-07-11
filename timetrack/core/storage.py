# project/timetrack/core/storage.py
"""Storage layer for all file I/O operations."""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..models import ApplicationState, Config, Memo, MemoList, TimeEntry, TimeLog
from .constants import CONFIG_FILE, DATA_DIR, LOG_FILE, MEMOS_FILE, STATE_FILE


def _atomic_write(path: Path, data: str) -> None:
    """
    Atomically write text to ``path``.

    Writes to a temporary file in the same directory, flushes it to disk, then
    atomically replaces the target via ``os.replace``. This ensures the target
    file is never left half-written if the process is interrupted mid-write:
    it will contain either the complete old contents or the complete new ones.

    Args:
        path: The destination file path.
        data: The text content to write.
    """
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class Storage:
    """
    Handles all file I/O operations for the timetrack application.

    This class centralizes all data persistence, making it easy to:
    - Test with mock storage or temp directories
    - Change storage backends in the future
    - Maintain consistent data handling
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the storage layer.

        Args:
            data_dir: Optional custom data directory. If None, uses the default
                      ~/.timetrack directory. Useful for testing.
        """
        if data_dir is not None:
            self.data_dir = data_dir
            self.state_file = data_dir / "state.json"
            self.log_file = data_dir / "timelog.json"
            self.config_file = data_dir / "config.json"
            self.memos_file = data_dir / "memos.json"
        else:
            self.data_dir = DATA_DIR
            self.state_file = STATE_FILE
            self.log_file = LOG_FILE
            self.config_file = CONFIG_FILE
            self.memos_file = MEMOS_FILE

        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # =================================
    # STATE OPERATIONS
    # =================================

    def read_state(self) -> Optional[ApplicationState]:
        """
        Reads and validates the current application state.

        Returns:
            The current ApplicationState or None if no task is running.
        """
        if not self.state_file.exists():
            return None
        try:
            state_data = json.loads(self.state_file.read_text())
            return ApplicationState.model_validate(state_data)
        except (json.JSONDecodeError, ValueError):
            return None

    def write_state(self, state: ApplicationState) -> None:
        """
        Writes the application state to the state file.

        Args:
            state: The ApplicationState to persist.
        """
        _atomic_write(self.state_file, state.model_dump_json(indent=4))

    def delete_state(self) -> None:
        """Deletes the state file (when a task is stopped)."""
        if self.state_file.exists():
            self.state_file.unlink()

    # =================================
    # LOG OPERATIONS
    # =================================

    def read_log(self) -> TimeLog:
        """
        Reads and validates the time log.

        Returns:
            The TimeLog containing all entries.
        """
        if not self.log_file.exists():
            return TimeLog()
        try:
            log_data = json.loads(self.log_file.read_text())
            validated_entries = []
            for entry_data in log_data.get("entries", []):
                if (
                    "start_time" in entry_data
                    and isinstance(entry_data["start_time"], str)
                    and "date" in entry_data
                ):
                    # Old format migration: convert date + time strings to datetime
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

    def write_log(self, log: TimeLog) -> None:
        """
        Writes the time log to the log file.

        Args:
            log: The TimeLog to persist. Entries are sorted by start_time.
        """
        log.entries.sort(key=lambda x: x.start_time)
        _atomic_write(self.log_file, log.model_dump_json(indent=4))

    # =================================
    # CONFIG OPERATIONS
    # =================================

    def read_config(self) -> Config:
        """
        Reads and validates the configuration file.

        Returns:
            The Config containing aliases and other settings.
        """
        if not self.config_file.exists():
            return Config()
        try:
            config_data = json.loads(self.config_file.read_text())
            return Config.model_validate(config_data)
        except (json.JSONDecodeError, ValueError):
            return Config()

    def write_config(self, config: Config) -> None:
        """
        Writes the configuration to the config file.

        Args:
            config: The Config to persist.
        """
        _atomic_write(self.config_file, config.model_dump_json(indent=4))

    # =================================
    # MEMO OPERATIONS
    # =================================

    def read_memos(self) -> MemoList:
        """
        Reads and validates the memos file.

        Returns:
            The MemoList containing all memos.
        """
        if not self.memos_file.exists():
            return MemoList()
        try:
            memos_data = json.loads(self.memos_file.read_text())
            return MemoList.model_validate(memos_data)
        except (json.JSONDecodeError, ValueError):
            return MemoList()

    def write_memos(self, memos: MemoList) -> None:
        """
        Writes the memos to the memos file.

        Args:
            memos: The MemoList to persist.
        """
        _atomic_write(self.memos_file, memos.model_dump_json(indent=4))
