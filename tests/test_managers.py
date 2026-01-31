# tests/test_managers.py
"""Tests for manager classes."""

import pytest
from datetime import datetime, timedelta, date
import time

from timetrack.core.tasks import TaskManager
from timetrack.core.entries import EntryManager
from timetrack.core.aliases import AliasManager
from timetrack.core.memos import MemoManager
from timetrack.core.reports import ReportManager


class TestTaskManager:
    """Tests for TaskManager."""

    def test_start_task(self, task_manager):
        success, message = task_manager.start("coding")

        assert success is True
        assert "Started tracking" in message
        assert "coding" in message
        assert task_manager.is_running() is True

    def test_start_task_when_already_running(self, task_manager):
        task_manager.start("first task")

        success, message = task_manager.start("second task")

        assert success is False
        assert "already running" in message

    def test_stop_task(self, task_manager):
        task_manager.start("coding")

        success, message = task_manager.stop()

        assert success is True
        assert "Stopped tracking" in message
        assert task_manager.is_running() is False

    def test_stop_when_no_task(self, task_manager):
        success, message = task_manager.stop()

        assert success is False
        assert "No task" in message

    def test_pause_task(self, task_manager):
        task_manager.start("coding")

        success, message = task_manager.pause()

        assert success is True
        assert "Paused" in message

    def test_pause_when_no_task(self, task_manager):
        success, message = task_manager.pause()

        assert success is False
        assert "No task" in message

    def test_pause_already_paused(self, task_manager):
        task_manager.start("coding")
        task_manager.pause()

        success, message = task_manager.pause()

        assert success is False
        assert "already paused" in message

    def test_resume_task(self, task_manager):
        task_manager.start("coding")
        task_manager.pause()

        success, message = task_manager.resume()

        assert success is True
        assert "Resumed" in message

    def test_resume_when_no_task(self, task_manager):
        success, message = task_manager.resume()

        assert success is False
        assert "No task" in message

    def test_resume_already_running(self, task_manager):
        task_manager.start("coding")

        success, message = task_manager.resume()

        assert success is False
        assert "already running" in message

    def test_status_no_task(self, task_manager):
        status = task_manager.status()

        assert "No task" in status

    def test_status_running_task(self, task_manager):
        task_manager.start("coding")

        status = task_manager.status()

        assert "Active Task" in status
        assert "coding" in status

    def test_status_paused_task(self, task_manager):
        task_manager.start("coding")
        task_manager.pause()

        status = task_manager.status()

        assert "Paused Task" in status
        assert "coding" in status

    def test_add_note(self, task_manager):
        task_manager.start("coding")

        success, message = task_manager.add_note("Fixed bug #123")

        assert success is True
        assert "Note added" in message

    def test_add_note_no_task(self, task_manager):
        success, message = task_manager.add_note("A note")

        assert success is False
        assert "No task" in message

    def test_status_with_notes(self, task_manager):
        task_manager.start("coding")
        task_manager.add_note("First note")
        task_manager.add_note("Second note")

        status = task_manager.status()

        assert "Notes:" in status
        assert "First note" in status
        assert "Second note" in status

    def test_get_current_activity(self, task_manager):
        assert task_manager.get_current_activity() == ""

        task_manager.start("coding")

        assert task_manager.get_current_activity() == "coding"

    def test_stop_creates_log_entry(self, task_manager, storage):
        task_manager.start("coding")
        task_manager.stop()

        log = storage.read_log()

        assert len(log.entries) == 1
        assert log.entries[0].activity == "coding"

    def test_stop_paused_task(self, task_manager, storage):
        task_manager.start("coding")
        task_manager.pause()

        success, message = task_manager.stop()

        assert success is True
        log = storage.read_log()
        assert len(log.entries) == 1


class TestEntryManager:
    """Tests for EntryManager."""

    def test_add_entry_with_end_time(self, entry_manager):
        success, message = entry_manager.add(
            activity="meeting",
            start_str="today 10am",
            end_str="today 11am",
            duration_str=None,
        )

        assert success is True
        assert "Logged" in message
        assert "meeting" in message

    def test_add_entry_with_duration(self, entry_manager):
        success, message = entry_manager.add(
            activity="coding",
            start_str="today 2pm",
            end_str=None,
            duration_str="1h30m",
        )

        assert success is True
        assert "Logged" in message

    def test_add_entry_invalid_start(self, entry_manager):
        success, message = entry_manager.add(
            activity="task",
            start_str="invalid time",
            end_str="today 11am",
            duration_str=None,
        )

        assert success is False
        assert "Invalid start time" in message

    def test_add_entry_invalid_duration(self, entry_manager):
        success, message = entry_manager.add(
            activity="task",
            start_str="today 10am",
            end_str=None,
            duration_str="invalid",
        )

        assert success is False
        assert "Invalid duration" in message

    def test_add_entry_end_before_start(self, entry_manager):
        success, message = entry_manager.add(
            activity="task",
            start_str="today 11am",
            end_str="today 10am",
            duration_str=None,
        )

        assert success is False
        assert "End time must be after" in message

    def test_add_entry_missing_end_and_duration(self, entry_manager):
        success, message = entry_manager.add(
            activity="task",
            start_str="today 10am",
            end_str=None,
            duration_str=None,
        )

        assert success is False
        assert "--end or --for must be provided" in message

    def test_backdate_entry(self, entry_manager):
        success, message = entry_manager.backdate("30m", "quick meeting")

        assert success is True
        assert "Logged" in message
        assert "quick meeting" in message

    def test_backdate_invalid_duration(self, entry_manager):
        success, message = entry_manager.backdate("invalid", "task")

        assert success is False
        assert "Invalid duration" in message

    def test_get_log_empty(self, entry_manager):
        result = entry_manager.get_log("today")

        assert "No entries found" in result

    def test_get_log_with_entries(self, entry_manager, sample_entries):
        result = entry_manager.get_log("today")

        assert "Time Log for" in result
        assert "coding" in result
        assert "meeting" in result

    def test_get_log_invalid_date(self, entry_manager, sample_entries):
        # Need entries in the log for date validation to occur
        result = entry_manager.get_log("invalid-date")

        assert "Invalid date format" in result

    def test_remove_entry(self, entry_manager, sample_entries, storage):
        initial_count = len(storage.read_log().entries)

        success, message = entry_manager.remove(0, "today")

        assert success is True
        assert "Removed" in message
        assert len(storage.read_log().entries) == initial_count - 1

    def test_remove_entry_invalid_id(self, entry_manager, sample_entries):
        success, message = entry_manager.remove(999, "today")

        assert success is False
        assert "Invalid ID" in message

    def test_remove_entry_invalid_date(self, entry_manager):
        success, message = entry_manager.remove(0, "invalid-date")

        assert success is False
        assert "Invalid date format" in message

    def test_get_by_id(self, entry_manager, sample_entries):
        entry, error = entry_manager.get_by_id(0, "today")

        assert entry is not None
        assert error == ""
        assert entry.activity == "coding"

    def test_get_by_id_invalid(self, entry_manager, sample_entries):
        entry, error = entry_manager.get_by_id(999, "today")

        assert entry is None
        assert "Invalid ID" in error

    def test_edit_entry_activity(self, entry_manager, sample_entries, storage):
        success, message = entry_manager.edit(
            entry_id=0,
            day_filter="today",
            new_activity="updated activity",
        )

        assert success is True
        assert "updated" in message

        log = storage.read_log()
        # Find the entry that was at position 0 for today
        today_entries = [
            e for e in log.entries if e.start_time.date() == date.today()
        ]
        assert any(e.activity == "updated activity" for e in today_entries)

    def test_edit_entry_invalid_id(self, entry_manager, sample_entries):
        success, message = entry_manager.edit(entry_id=999, day_filter="today")

        assert success is False
        assert "Invalid ID" in message

    def test_get_last_activity(self, entry_manager, sample_entries):
        result = entry_manager.get_last_activity()

        # The last entry in sample_entries is "coding"
        assert result == "coding"

    def test_get_last_activity_empty(self, entry_manager):
        result = entry_manager.get_last_activity()

        assert result is None


class TestAliasManager:
    """Tests for AliasManager."""

    def test_add_alias(self, alias_manager):
        success, message = alias_manager.add("@work", "Working on project")

        assert success is True
        assert "@work" in message
        assert "Working on project" in message

    def test_add_alias_without_at_symbol(self, alias_manager):
        success, message = alias_manager.add("work", "Working on project")

        assert success is False
        assert "must start with '@'" in message

    def test_resolve_alias(self, alias_manager):
        alias_manager.add("@work", "Working on project")

        result = alias_manager.resolve_alias("@work")

        assert result == "Working on project"

    def test_resolve_nonexistent_alias(self, alias_manager):
        result = alias_manager.resolve_alias("@unknown")

        assert result is None

    def test_resolve_non_alias(self, alias_manager):
        result = alias_manager.resolve_alias("regular text")

        assert result == "regular text"

    def test_remove_alias(self, alias_manager):
        alias_manager.add("@work", "Working on project")

        success, message = alias_manager.remove("@work")

        assert success is True
        assert "@work" in message

    def test_remove_nonexistent_alias(self, alias_manager):
        success, message = alias_manager.remove("@unknown")

        assert success is False
        assert "not found" in message

    def test_list_aliases_empty(self, alias_manager):
        result = alias_manager.list_all()

        assert "No aliases" in result

    def test_list_aliases(self, alias_manager):
        alias_manager.add("@work", "Working")
        alias_manager.add("@lunch", "Lunch break")

        result = alias_manager.list_all()

        assert "@work" in result
        assert "@lunch" in result
        assert "Working" in result
        assert "Lunch break" in result


class TestMemoManager:
    """Tests for MemoManager."""

    def test_add_memo(self, memo_manager):
        success, message = memo_manager.add("Remember to review PR")

        assert success is True
        assert "Memo added" in message

    def test_list_memos_empty(self, memo_manager):
        result = memo_manager.list_all()

        assert "No memos found" in result

    def test_list_memos(self, memo_manager):
        memo_manager.add("First memo")
        memo_manager.add("Second memo")

        result = memo_manager.list_all()

        assert "First memo" in result
        assert "Second memo" in result
        assert "ID" in result

    def test_remove_memo(self, memo_manager):
        memo_manager.add("To be removed")

        success, message = memo_manager.remove(0)

        assert success is True
        assert "removed" in message

    def test_remove_memo_invalid_id(self, memo_manager):
        memo_manager.add("A memo")

        success, message = memo_manager.remove(999)

        assert success is False
        assert "Invalid ID" in message

    def test_remove_memo_empty_list(self, memo_manager):
        success, message = memo_manager.remove(0)

        assert success is False
        assert "No memos found" in message


class TestReportManager:
    """Tests for ReportManager."""

    def test_text_report_empty(self, report_manager):
        result = report_manager.generate_text_report()

        assert "No entries found" in result

    def test_text_report_with_data(self, report_manager, sample_entries_multiday):
        result = report_manager.generate_text_report(days=7)

        assert "Time Report" in result
        assert "Daily Hours" in result
        assert "Activity Breakdown" in result
        assert "Summary" in result
        assert "project work" in result
        assert "meetings" in result

    def test_text_report_summary_stats(self, report_manager, sample_entries_multiday):
        result = report_manager.generate_text_report(days=7)

        assert "Total hours" in result
        assert "Average per day" in result
        assert "Days tracked" in result
        assert "Activities" in result

    def test_html_report_empty(self, report_manager):
        success, message = report_manager.generate_html_report()

        assert success is False
        assert "No entries found" in message

    def test_html_report_with_data(self, report_manager, sample_entries_multiday):
        success, message = report_manager.generate_html_report(days=7)

        assert success is True
        assert "Report generated" in message
        assert ".html" in message

    def test_export_log_empty(self, report_manager):
        success, message = report_manager.export_log("csv")

        assert success is False
        assert "No log entries" in message

    def test_export_csv(self, report_manager, sample_entries):
        success, message = report_manager.export_log("csv")

        assert success is True
        assert "exported" in message
        assert ".csv" in message

    def test_export_xlsx(self, report_manager, sample_entries):
        success, message = report_manager.export_log("xlsx")

        assert success is True
        assert "exported" in message
        assert ".xlsx" in message

    def test_export_invalid_format(self, report_manager, sample_entries):
        success, message = report_manager.export_log("pdf")

        assert success is False
        assert "Unsupported format" in message

    def test_report_text_format(self, report_manager, sample_entries_multiday):
        success, message = report_manager.report(format="text", days=7)

        assert success is True
        assert "Time Report" in message

    def test_report_html_format(self, report_manager, sample_entries_multiday):
        success, message = report_manager.report(format="html", days=7)

        assert success is True
        assert "Report generated" in message
