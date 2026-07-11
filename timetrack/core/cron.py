# project/timetrack/core/cron.py
"""Install a scheduled job that runs `track sync` daily."""

import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Tuple


def _track_command() -> str:
    """Best-effort resolve the command used to invoke `track`."""
    exe = shutil.which("track")
    if exe:
        return exe
    # Fall back to `python -m timetrack.cli`.
    return f'{sys.executable} -m timetrack.cli'


def _cron_line() -> str:
    return f"55 23 * * * {_track_command()} sync >> {_log_path()} 2>&1"


def _log_path() -> Path:
    data_dir = Path.home() / ".timetrack"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "sync.log"


def install() -> Tuple[bool, str]:
    """Install a daily cron/launchd job.

    Returns:
        A tuple of (success, message).
    """
    system = platform.system()
    if system == "Darwin":
        return _install_launchd()
    if system == "Linux":
        return _install_crontab()
    return False, f"Unsupported platform for cron install: {system}"


def _install_launchd() -> Tuple[bool, str]:
    label = "com.timetrack.sync"
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{label}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{_track_command()}</string>
    <string>sync</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>23</integer>
    <key>Minute</key>
    <integer>55</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>{_log_path()}</string>
  <key>StandardErrorPath</key>
  <string>{_log_path()}</string>
</dict>
</plist>
"""
    plist_path.write_text(plist)
    try:
        subprocess.run(["launchctl", "load", str(plist_path)], check=False)
    except Exception:  # pragma: no cover - best effort
        pass
    return True, f"✅ Scheduled daily sync via launchd ({plist_path})."


def _install_crontab() -> Tuple[bool, str]:
    line = _cron_line()
    try:
        result = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True, check=False
        )
        existing = result.stdout if result.returncode == 0 else ""
        if "timetrack" in existing and "track sync" in existing:
            return True, "✅ Daily sync already scheduled in crontab."
        new_crontab = (existing + "\n" + line + "\n").lstrip()
        subprocess.run(
            ["crontab", "-"], input=new_crontab, text=True, check=True
        )
    except Exception as e:
        return False, f"❗ Could not update crontab: {e}"
    return True, f"✅ Scheduled daily sync in crontab: {line}"


def uninstall() -> Tuple[bool, str]:
    """Remove the scheduled job (best effort)."""
    system = platform.system()
    if system == "Darwin":
        label = "com.timetrack.sync"
        plist_path = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
        subprocess.run(["launchctl", "unload", str(plist_path)], check=False)
        if plist_path.exists():
            plist_path.unlink()
        return True, "✅ Removed launchd job."
    if system == "Linux":
        try:
            result = subprocess.run(
                ["crontab", "-l"], capture_output=True, text=True, check=False
            )
            existing = result.stdout if result.returncode == 0 else ""
            kept = "\n".join(
                line for line in existing.splitlines() if "track sync" not in line
            )
            subprocess.run(
                ["crontab", "-"], input=kept, text=True, check=True
            )
        except Exception as e:
            return False, f"❗ Could not update crontab: {e}"
        return True, "✅ Removed crontab entry."
    return False, f"Unsupported platform: {system}"
