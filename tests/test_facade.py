# tests/test_facade.py
"""Integration tests for the TimeTracker facade."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from timetrack.core.facade import TimeTracker
from timetrack.core.storage import Storage
from timetrack.models import TimeEntry, TimeLog


@pytest.fixture
def tracker(tmp_path):
    """Create a TimeTracker with isolated storage."""
    data_dir = tmp_path / ".timetrack"
    data_dir.mkdir()

    # Patch Storage to use our temp directory
    with patch("timetrack.core.facade.Storage") as MockStorage:
        storage = Storage(data_dir=data_dir)
        MockStorage.return_value = storage

        tracker = TimeTracker()
        # Manually set the storage to our isolated instance
        tracker._storage = storage
        tracker._tasks.storage = storage
        tracker._entries.storage = storage
        tracker._aliases.storage = storage
        tracker._memos.storage = storage
        tracker._reports.storage = storage

        yield tracker


class TestTaskLifecycle:
    """Integration tests for the complete task lifecycle."""

    def test_start_stop_workflow(self, tracker):
        # Start a task
        success, message = tracker.start("coding")
        assert success is True
        assert "Started tracking" in message

        # Check status
        status = tracker.status()
        assert "coding" in status
        assert "Active Task" in status or "Active" in status

        # Stop the task
        success, message = tracker.stop()
        assert success is True
        assert "Stopped tracking" in message

    def test_start_pause_resume_stop(self, tracker):
        tracker.start("coding")

        # Pause
        success, message = tracker.pause()
        assert success is True

        status = tracker.status()
        assert "Paused" in status

        # Resume
        success, message = tracker.resume()
        assert success is True

        status = tracker.status()
        assert "Active" in status or "running" in status.lower()

        # Stop
        success, message = tracker.stop()
        assert success is True

    def test_force_start(self, tracker):
        tracker.start("first task")

        # Force start a new task
        success, message = tracker.start("second task", force=True)

        assert success is True
        assert "Stopped tracking" in message
        assert "Started tracking" in message
        assert "second task" in message

    def test_start_without_force_fails(self, tracker):
        tracker.start("first task")

        success, message = tracker.start("second task", force=False)

        assert success is False
        assert "already running" in message


class TestAliasIntegration:
    """Integration tests for aliases with task tracking."""

    def test_start_with_alias(self, tracker):
        # Create an alias
        tracker.add_alias("@work", "Working on project")

        # Start using alias
        success, message = tracker.start("@work")

        assert success is True
        assert "Working on project" in message

        # Verify status shows resolved name
        status = tracker.status()
        assert "Working on project" in status

    def test_start_with_unknown_alias(self, tracker):
        success, message = tracker.start("@unknown")

        assert success is False
        assert "not found" in message

    def test_alias_crud_workflow(self, tracker):
        # Add
        success, _ = tracker.add_alias("@test", "Test activity")
        assert success is True

        # List
        result = tracker.list_aliases()
        assert "@test" in result
        assert "Test activity" in result

        # Remove
        success, _ = tracker.remove_alias("@test")
        assert success is True

        # List again
        result = tracker.list_aliases()
        assert "No aliases" in result


class TestEntryManagement:
    """Integration tests for entry management."""

    def test_add_and_view_entry(self, tracker):
        # Add an entry
        success, message = tracker.add_entry(
            activity="meeting",
            start_str="today 10am",
            end_str="today 11am",
            duration_str=None,
        )
        assert success is True

        # View log
        log = tracker.get_log("today")
        assert "meeting" in log
        assert "60 min" in log or "1h" in log

    def test_backdate_and_view(self, tracker):
        success, message = tracker.backdate_entry("45m", "quick call")
        assert success is True

        log = tracker.get_log("today")
        assert "quick call" in log

    def test_edit_entry(self, tracker):
        # Add entry
        tracker.add_entry(
            activity="original",
            start_str="today 10am",
            end_str="today 11am",
            duration_str=None,
        )

        # Edit it
        success, message = tracker.edit_entry(
            entry_id=0,
            day_filter="today",
            new_activity="edited",
        )
        assert success is True

        # Verify
        log = tracker.get_log("today")
        assert "edited" in log

    def test_remove_entry(self, tracker):
        # Add entry
        tracker.add_entry(
            activity="to remove",
            start_str="today 10am",
            end_str="today 11am",
            duration_str=None,
        )

        # Remove it
        success, message = tracker.remove_entry(0, "today")
        assert success is True

        # Verify
        log = tracker.get_log("today")
        assert "to remove" not in log or "No log entries" in log


class TestStartPrevious:
    """Integration tests for start_previous."""

    def test_start_previous(self, tracker):
        # Create some logged entries
        tracker.start("first task")
        tracker.stop()
        tracker.start("second task")
        tracker.stop()

        # Start previous should start "second task"
        success, message = tracker.start_previous()

        assert success is True
        assert "second task" in message

    def test_start_previous_no_entries(self, tracker):
        success, message = tracker.start_previous()

        assert success is False
        assert "No previous task" in message


class TestMemoIntegration:
    """Integration tests for memos."""

    def test_memo_crud_workflow(self, tracker):
        # Add
        success, _ = tracker.add_memo("Remember this")
        assert success is True

        # List
        result = tracker.list_memos()
        assert "Remember this" in result

        # Remove
        success, _ = tracker.remove_memo(0)
        assert success is True

        # List again
        result = tracker.list_memos()
        assert "No memos" in result


class TestNotesOnTasks:
    """Integration tests for notes on active tasks."""

    def test_add_note_to_task(self, tracker):
        tracker.start("coding")

        success, message = tracker.add_note("Fixed bug #123")
        assert success is True

        # Verify note appears in status
        status = tracker.status()
        assert "Fixed bug #123" in status

    def test_notes_preserved_after_stop(self, tracker):
        tracker.start("coding")
        tracker.add_note("Note 1")
        tracker.add_note("Note 2")
        tracker.stop()

        # Notes should be in the logged entry
        log = tracker.get_log("today")
        assert "Note 1" in log
        assert "Note 2" in log


class TestReportIntegration:
    """Integration tests for reports."""

    def test_report_with_data(self, tracker):
        # Create some entries
        tracker.add_entry(
            activity="coding",
            start_str="today 9am",
            end_str="today 12pm",
            duration_str=None,
        )
        tracker.add_entry(
            activity="meeting",
            start_str="today 2pm",
            end_str="today 3pm",
            duration_str=None,
        )

        # Generate report
        success, message = tracker.report(format="text", days=7)

        assert success is True
        assert "Time Report" in message
        assert "coding" in message
        assert "meeting" in message

    def test_export_with_data(self, tracker):
        tracker.add_entry(
            activity="task",
            start_str="today 10am",
            end_str="today 11am",
            duration_str=None,
        )

        success, message = tracker.export_log("csv")

        assert success is True
        assert "exported" in message


class TestEmojiDecorations:
    """Tests to verify emoji decorations are added correctly."""

    def test_start_has_green_emoji(self, tracker):
        success, message = tracker.start("task")
        assert "🟢" in message

    def test_stop_has_checkmark(self, tracker):
        tracker.start("task")
        success, message = tracker.stop()
        assert "✅" in message

    def test_pause_has_pause_emoji(self, tracker):
        tracker.start("task")
        success, message = tracker.pause()
        assert "⏸️" in message

    def test_error_has_exclamation(self, tracker):
        success, message = tracker.stop()  # No task running
        assert "❗" in message

    def test_status_no_task_has_white_circle(self, tracker):
        status = tracker.status()
        assert "⚪" in status


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_multiple_pause_resume_cycles(self, tracker):
        tracker.start("task")

        for _ in range(3):
            success, _ = tracker.pause()
            assert success is True
            success, _ = tracker.resume()
            assert success is True

        success, _ = tracker.stop()
        assert success is True

    def test_very_long_activity_name(self, tracker):
        long_name = "a" * 200
        success, _ = tracker.start(long_name)
        assert success is True

        # Status should truncate
        status = tracker.status()
        assert "..." in status or len(status) < 300

    def test_special_characters_in_activity(self, tracker):
        success, _ = tracker.start("task with 'quotes' and \"double\"")
        assert success is True

        tracker.stop()

        log = tracker.get_log("today")
        assert "quotes" in log

    def test_concurrent_operations_sequence(self, tracker):
        """Test a realistic sequence of operations."""
        # Morning work
        tracker.add_alias("@code", "Coding session")
        tracker.start("@code")
        tracker.add_note("Started feature X")
        tracker.pause()
        tracker.resume()
        tracker.stop()

        # Add a backdated meeting
        tracker.backdate_entry("30m", "standup")

        # Afternoon work
        tracker.start("@code", force=False)
        tracker.add_note("Continued feature X")
        tracker.stop()

        # Check log
        log = tracker.get_log("today")
        assert "Coding session" in log
        assert "standup" in log
        assert "Started feature X" in log
