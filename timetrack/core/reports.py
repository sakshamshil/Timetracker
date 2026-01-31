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

    Supports text reports with ASCII bar charts and HTML reports
    with Chart.js visualizations, as well as CSV/XLSX exports.
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

    def generate_html_report(self, days: int = 30) -> Tuple[bool, str]:
        """
        Generate an HTML report with charts.

        Args:
            days: Number of days to include in the report (default: 30).

        Returns:
            A tuple containing a success flag and a message.
        """
        log = self.storage.read_log()
        if not log.entries:
            return False, "No entries found in the log."

        # Get entries from the last N days
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        # Group by date and activity
        daily_data = {}
        activity_data = {}

        for entry in log.entries:
            entry_date = entry.start_time.date()
            if start_date <= entry_date <= end_date:
                date_str = entry_date.strftime("%Y-%m-%d")
                hours = entry.duration_minutes / 60
                daily_data[date_str] = daily_data.get(date_str, 0) + hours

                activity = entry.activity
                activity_data[activity] = activity_data.get(activity, 0) + hours

        if not daily_data:
            return False, f"No entries found in the last {days} days."

        # Prepare data for charts
        dates = sorted(daily_data.keys())
        hours_per_day = [daily_data[d] for d in dates]

        # Top activities (limit to top 10)
        sorted_activities = sorted(
            activity_data.items(), key=lambda x: x[1], reverse=True
        )[:10]
        activity_labels = [a[0] for a in sorted_activities]
        activity_values = [a[1] for a in sorted_activities]

        # Calculate statistics
        total_hours = sum(daily_data.values())
        avg_hours = total_hours / len(daily_data) if daily_data else 0

        # Generate HTML
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Time Tracking Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        h1 {{
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #4CAF50;
        }}
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .chart-title {{
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 15px;
            color: #333;
        }}
        .date-range {{
            text-align: center;
            color: #666;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <h1>Time Tracking Report</h1>
    <div class="date-range">
        {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}
    </div>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-value">{total_hours:.1f}h</div>
            <div class="stat-label">Total Hours</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{avg_hours:.1f}h</div>
            <div class="stat-label">Average per Day</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{len(daily_data)}</div>
            <div class="stat-label">Days Tracked</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{len(activity_data)}</div>
            <div class="stat-label">Activities</div>
        </div>
    </div>

    <div class="chart-container">
        <div class="chart-title">Daily Hours</div>
        <canvas id="dailyChart"></canvas>
    </div>

    <div class="chart-container">
        <div class="chart-title">Time by Activity (Top 10)</div>
        <canvas id="activityChart"></canvas>
    </div>

    <script>
        // Daily hours chart
        const dailyCtx = document.getElementById('dailyChart').getContext('2d');
        new Chart(dailyCtx, {{
            type: 'bar',
            data: {{
                labels: {dates},
                datasets: [{{
                    label: 'Hours',
                    data: {hours_per_day},
                    backgroundColor: 'rgba(76, 175, 80, 0.6)',
                    borderColor: 'rgba(76, 175, 80, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Hours'
                        }}
                    }}
                }}
            }}
        }});

        // Activity pie chart
        const activityCtx = document.getElementById('activityChart').getContext('2d');
        new Chart(activityCtx, {{
            type: 'doughnut',
            data: {{
                labels: {activity_labels},
                datasets: [{{
                    data: {activity_values},
                    backgroundColor: [
                        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
                        '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384'
                    ]
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        position: 'right'
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""

        # Save HTML file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_dir = Path(__file__).parent.parent.parent
        output_dir = project_dir / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"timetrack_report_{timestamp}.html"
        output_path.write_text(html_content)

        return True, f"Report generated: {output_path}"

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

    def report(self, format: str = "text", days: int = 7) -> Tuple[bool, str]:
        """
        Generate a time tracking report.

        Args:
            format: Report format ('text' or 'html').
            days: Number of days to include.

        Returns:
            A tuple containing a success flag and a message.
        """
        if format == "html":
            # Use 30 days default for HTML reports
            return self.generate_html_report(days if days != 7 else 30)
        else:
            report_text = self.generate_text_report(days)
            return True, report_text
