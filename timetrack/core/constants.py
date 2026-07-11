# project/timetrack/core/constants.py
"""Constants and file paths for the timetrack application."""

from pathlib import Path

# Data directory and file paths
DATA_DIR = Path.home() / ".timetrack"
STATE_FILE = DATA_DIR / "state.json"
LOG_FILE = DATA_DIR / "timelog.json"
CONFIG_FILE = DATA_DIR / "config.json"
MEMOS_FILE = DATA_DIR / "memos.json"
DASHBOARD_DIR = DATA_DIR / "dashboard"
