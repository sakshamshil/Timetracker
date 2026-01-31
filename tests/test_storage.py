# tests/test_storage.py
"""Tests for the Storage class."""

import pytest
import json
from datetime import datetime

from timetrack.core.storage import Storage
from timetrack.models import (
    ApplicationState,
    Config,
    Memo,
    MemoList,
    TimeEntry,
    TimeLog,
)


class TestStorageInit:
    """Tests for Storage initialization."""

    def test_creates_data_directory(self, tmp_path):
        data_dir = tmp_path / "new_dir"
        assert not data_dir.exists()

        storage = Storage(data_dir=data_dir)

        assert data_dir.exists()
        assert storage.data_dir == data_dir

    def test_uses_custom_paths(self, tmp_path):
        data_dir = tmp_path / "custom"
        storage = Storage(data_dir=data_dir)

        assert storage.state_file == data_dir / "state.json"
        assert storage.log_file == data_dir / "timelog.json"
        assert storage.config_file == data_dir / "config.json"
        assert storage.memos_file == data_dir / "memos.json"


class TestStateOperations:
    """Tests for state read/write operations."""

    def test_read_state_when_not_exists(self, storage):
        result = storage.read_state()
        assert result is None

    def test_write_and_read_state(self, storage):
        state = ApplicationState(
            activity="test task",
            start_time=datetime(2024, 1, 15, 10, 30, 0),
            status="running",
        )
        storage.write_state(state)

        result = storage.read_state()

        assert result is not None
        assert result.activity == "test task"
        assert result.status == "running"
        assert result.start_time == datetime(2024, 1, 15, 10, 30, 0)

    def test_write_state_with_notes(self, storage):
        state = ApplicationState(
            activity="task with notes",
            start_time=datetime.now(),
            notes=["note 1", "note 2"],
        )
        storage.write_state(state)

        result = storage.read_state()

        assert result.notes == ["note 1", "note 2"]

    def test_write_paused_state(self, storage):
        pause_time = datetime(2024, 1, 15, 11, 0, 0)
        state = ApplicationState(
            activity="paused task",
            start_time=datetime(2024, 1, 15, 10, 0, 0),
            status="paused",
            pause_start_time=pause_time,
            total_paused_seconds=300.0,
        )
        storage.write_state(state)

        result = storage.read_state()

        assert result.status == "paused"
        assert result.pause_start_time == pause_time
        assert result.total_paused_seconds == 300.0

    def test_delete_state(self, storage):
        state = ApplicationState(activity="to delete", start_time=datetime.now())
        storage.write_state(state)

        assert storage.read_state() is not None

        storage.delete_state()

        assert storage.read_state() is None

    def test_delete_state_when_not_exists(self, storage):
        # Should not raise an error
        storage.delete_state()
        assert storage.read_state() is None

    def test_read_corrupted_state(self, storage):
        storage.state_file.write_text("not valid json")

        result = storage.read_state()

        assert result is None


class TestLogOperations:
    """Tests for time log read/write operations."""

    def test_read_log_when_not_exists(self, storage):
        result = storage.read_log()
        assert result.entries == []

    def test_write_and_read_log(self, storage):
        entry = TimeEntry(
            start_time=datetime(2024, 1, 15, 10, 0, 0),
            end_time=datetime(2024, 1, 15, 11, 0, 0),
            activity="coding",
            duration_minutes=60,
        )
        log = TimeLog(entries=[entry])
        storage.write_log(log)

        result = storage.read_log()

        assert len(result.entries) == 1
        assert result.entries[0].activity == "coding"
        assert result.entries[0].duration_minutes == 60

    def test_write_log_sorts_by_start_time(self, storage):
        entries = [
            TimeEntry(
                start_time=datetime(2024, 1, 15, 14, 0, 0),
                end_time=datetime(2024, 1, 15, 15, 0, 0),
                activity="later",
                duration_minutes=60,
            ),
            TimeEntry(
                start_time=datetime(2024, 1, 15, 10, 0, 0),
                end_time=datetime(2024, 1, 15, 11, 0, 0),
                activity="earlier",
                duration_minutes=60,
            ),
        ]
        log = TimeLog(entries=entries)
        storage.write_log(log)

        result = storage.read_log()

        assert result.entries[0].activity == "earlier"
        assert result.entries[1].activity == "later"

    def test_write_log_with_notes(self, storage):
        entry = TimeEntry(
            start_time=datetime(2024, 1, 15, 10, 0, 0),
            end_time=datetime(2024, 1, 15, 11, 0, 0),
            activity="task",
            duration_minutes=60,
            notes=["note 1", "note 2"],
        )
        log = TimeLog(entries=[entry])
        storage.write_log(log)

        result = storage.read_log()

        assert result.entries[0].notes == ["note 1", "note 2"]

    def test_read_corrupted_log(self, storage):
        storage.log_file.write_text("invalid json")

        result = storage.read_log()

        assert result.entries == []


class TestConfigOperations:
    """Tests for config read/write operations."""

    def test_read_config_when_not_exists(self, storage):
        result = storage.read_config()
        assert result.aliases == {}

    def test_write_and_read_config(self, storage):
        config = Config(aliases={"@work": "Working on project", "@lunch": "Lunch break"})
        storage.write_config(config)

        result = storage.read_config()

        assert result.aliases == {"@work": "Working on project", "@lunch": "Lunch break"}

    def test_read_corrupted_config(self, storage):
        storage.config_file.write_text("invalid json")

        result = storage.read_config()

        assert result.aliases == {}


class TestMemoOperations:
    """Tests for memo read/write operations."""

    def test_read_memos_when_not_exists(self, storage):
        result = storage.read_memos()
        assert result.memos == []

    def test_write_and_read_memos(self, storage):
        memo = Memo(text="Remember this", created_at=datetime(2024, 1, 15, 10, 0, 0))
        memos = MemoList(memos=[memo])
        storage.write_memos(memos)

        result = storage.read_memos()

        assert len(result.memos) == 1
        assert result.memos[0].text == "Remember this"

    def test_write_multiple_memos(self, storage):
        memos_list = MemoList(
            memos=[
                Memo(text="First", created_at=datetime(2024, 1, 15, 10, 0, 0)),
                Memo(text="Second", created_at=datetime(2024, 1, 15, 11, 0, 0)),
            ]
        )
        storage.write_memos(memos_list)

        result = storage.read_memos()

        assert len(result.memos) == 2

    def test_read_corrupted_memos(self, storage):
        storage.memos_file.write_text("invalid json")

        result = storage.read_memos()

        assert result.memos == []
