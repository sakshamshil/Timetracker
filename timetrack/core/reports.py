# project/timetrack/core/reports.py
"""Report generation for the timetrack application."""

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Tuple

import pandas as pd  # type: ignore

from .storage import Storage
from .utils import truncate_text


class ReportManager:
    """
    Manages report generation and data export.

    Supports text reports with ASCII bar charts, as well as
    CSV/XLSX exports.
    """

    def __init__(self, storage: Storage):
        """
        Initialize the ReportManager.

        Args:
            storage: The Storage instance for persistence.
        """
        self.storage = storage

    def generate_text_report(self, days: int = 7) -> str:
        """
        Generate a text-based report with ASCII bar charts.

        Args:
            days: Number of days to include in the report (default: 7).

        Returns:
            A formatted string with the report.
        """
        log = self.storage.read_log()
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
        output.append("Daily Hours:")
        output.append("-" * 60)

        max_hours = max(daily_hours.values()) if daily_hours else 1
        bar_width = 30

        for date_str in sorted(daily_hours.keys()):
            hours = daily_hours[date_str]
            bar_length = int((hours / max_hours) * bar_width) if max_hours > 0 else 0
            bar = "#" * bar_length + "-" * (bar_width - bar_length)
            output.append(f"{date_str} |{bar}| {hours:.1f}h")

        output.append("")

        # Activity breakdown
        output.append("Activity Breakdown:")
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
            bar = "#" * bar_length + "-" * (activity_bar_width - bar_length)
            activity_display = truncate_text(activity, 20)
            output.append(f"{activity_display:<20} |{bar}| {hours:.1f}h")

        # Summary statistics
        total_hours = sum(daily_hours.values())
        avg_hours = total_hours / len(daily_hours) if daily_hours else 0

        output.append("")
        output.append("Summary:")
        output.append("-" * 60)
        output.append(f"Total hours: {total_hours:.1f}h")
        output.append(f"Average per day: {avg_hours:.1f}h")
        output.append(f"Days tracked: {len(daily_hours)}")
        output.append(f"Activities: {len(activity_hours)}")
        output.append("=" * 60)

        return "\n".join(output)

    def export_log(self, file_format: str) -> Tuple[bool, str]:
        """
        Exports the entire time log to a file.

        Args:
            file_format: The format to export to (csv or xlsx).

        Returns:
            A tuple containing a success flag and a message.
        """
        log_data = self.storage.read_log()
        if not log_data.entries:
            return False, "No log entries to export."

        processed_entries = []
        for entry in log_data.entries:
            entry_dict = entry.model_dump()
            entry_dict["notes"] = "\n".join(entry.notes) if entry.notes else ""
            processed_entries.append(entry_dict)

        df = pd.DataFrame(processed_entries)

        # Define the output directory and create it if it doesn't exist
        project_dir = Path(__file__).parent.parent.parent
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

        return True, f"Successfully exported all data to {output_path}"

    def export_memos(self, file_format: str) -> Tuple[bool, str]:
        """
        Exports all global memos to a file.

        Args:
            file_format: The format to export to (csv or xlsx).

        Returns:
            A tuple containing a success flag and a message.
        """
        memo_list = self.storage.read_memos()
        if not memo_list.memos:
            return False, "No memos to export."

        processed_memos = [memo.model_dump() for memo in memo_list.memos]
        df = pd.DataFrame(processed_memos)

        # Define the output directory and create it if it doesn't exist
        project_dir = Path(__file__).parent.parent.parent
        output_dir = project_dir / "exports"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create a timestamp for the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"timetrack_memos_{timestamp}.{file_format}"
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

        return True, f"Successfully exported all memos to {output_path}"

    def report(self, days: int = 7) -> Tuple[bool, str]:
        """
        Generate a time tracking report.

        Args:
            days: Number of days to include.

        Returns:
            A tuple containing a success flag and a message.
        """
        report_text = self.generate_text_report(days)
        return True, report_text
