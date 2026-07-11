# project/tests/test_easy_mode.py
"""Tests for the interactive 'easy mode' of the `add` command."""

import pytest
from click.testing import CliRunner

import timetrack.core.constants as constants
import timetrack.core.storage as storage
from timetrack.cli import main
from timetrack.core.storage import Storage


@pytest.fixture
def isolated_data_dir(tmp_path, monkeypatch):
    """Point the default storage location at a temp dir for CLI tests."""
    data_dir = tmp_path / ".timetrack"
    data_dir.mkdir()
    monkeypatch.setattr(constants, "DATA_DIR", data_dir)
    monkeypatch.setattr(constants, "STATE_FILE", data_dir / "state.json")
    monkeypatch.setattr(constants, "LOG_FILE", data_dir / "timelog.json")
    monkeypatch.setattr(constants, "CONFIG_FILE", data_dir / "config.json")
    monkeypatch.setattr(constants, "MEMOS_FILE", data_dir / "memos.json")
    # Storage imports these constants by value, so patch them there too.
    monkeypatch.setattr(storage, "DATA_DIR", data_dir)
    monkeypatch.setattr(storage, "STATE_FILE", data_dir / "state.json")
    monkeypatch.setattr(storage, "LOG_FILE", data_dir / "timelog.json")
    monkeypatch.setattr(storage, "CONFIG_FILE", data_dir / "config.json")
    monkeypatch.setattr(storage, "MEMOS_FILE", data_dir / "memos.json")
    return data_dir


def _entries(data_dir):
    return Storage(data_dir=data_dir).read_log().entries


def test_easy_mode_with_end_time(isolated_data_dir):
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["add"],
        input="My Task\nyesterday 10am\nyesterday 11am\n",
    )
    assert result.exit_code == 0, result.output
    assert "Logged 'My Task'" in result.output
    entries = _entries(isolated_data_dir)
    assert len(entries) == 1
    assert entries[0].activity == "My Task"
    assert entries[0].duration_minutes == 60


def test_easy_mode_with_duration(isolated_data_dir):
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["add"],
        input="Coding\ntoday 9am\n\n1h30m\n",
    )
    assert result.exit_code == 0, result.output
    assert "Logged 'Coding'" in result.output
    entries = _entries(isolated_data_dir)
    assert len(entries) == 1
    assert entries[0].duration_minutes == 90


def test_easy_mode_reprompts_on_invalid_start(isolated_data_dir):
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["add"],
        input="Task\nnot-a-real-time\nyesterday 10am\nyesterday 11am\n",
    )
    assert result.exit_code == 0, result.output
    assert "Invalid start time format" in result.output
    assert "Logged 'Task'" in result.output
    assert len(_entries(isolated_data_dir)) == 1


def test_easy_mode_empty_activity_reprompt(isolated_data_dir):
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["add"],
        input="\nReal Task\nyesterday 10am\nyesterday 11am\n",
    )
    assert result.exit_code == 0, result.output
    assert "Activity name cannot be empty" in result.output
    assert "Logged 'Real Task'" in result.output
    assert len(_entries(isolated_data_dir)) == 1


def test_easy_mode_with_preset_activity(isolated_data_dir):
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["add", "Preset Task"],
        input="yesterday 10am\nyesterday 11:30am\n",
    )
    assert result.exit_code == 0, result.output
    assert "Logged 'Preset Task'" in result.output
    entries = _entries(isolated_data_dir)
    assert len(entries) == 1
    assert entries[0].activity == "Preset Task"


def test_add_still_works_non_interactively(isolated_data_dir):
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["add", "Plain", "--start", "today 8am", "--for", "45m"],
    )
    assert result.exit_code == 0, result.output
    assert "Logged 'Plain'" in result.output
    assert len(_entries(isolated_data_dir)) == 1
