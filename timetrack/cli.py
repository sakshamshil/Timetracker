# project/timetrack/cli.py
"""Command-line interface for the timetrack application."""

from typing import Optional
import click  # type: ignore
from .core import TimeTracker


@click.group()
def main():
    """A simple CLI for time tracking."""
    pass


@main.command()
@click.argument("activity")
@click.option(
    "--start",
    "start_str",
    required=True,
    help="Start time (e.g., 'today 10am', '25-07-2025 14:00').",
)
@click.option("--end", "end_str", help="End time (e.g., 'today 11am').")
@click.option("--for", "duration_str", help="Duration (e.g., '1h', '30m').")
def add(
    activity: str, start_str: str, end_str: Optional[str], duration_str: Optional[str]
):
    """Add a completed time entry retrospectively."""
    if not (end_str or duration_str):
        click.echo("❗ Error: You must provide either --end or --for.", err=True)
        return
    if end_str and duration_str:
        click.echo("❗ Error: You cannot provide both --end and --for.", err=True)
        return

    tracker = TimeTracker()
    success, message = tracker.add_entry(activity, start_str, end_str, duration_str)
    click.echo(message)


@main.command()
@click.argument("activity")
def start(activity: str):
    """Start tracking a new task."""
    tracker = TimeTracker()
    success, message = tracker.start(activity)
    click.echo(message)


@main.command()
def stop():
    """Stop the current task."""
    tracker = TimeTracker()
    success, message = tracker.stop()
    click.echo(message)


@main.command()
def pause():
    """Pause the current task."""
    tracker = TimeTracker()
    success, message = tracker.pause()
    click.echo(message)


@main.command()
def resume():
    """Resume the current task."""
    tracker = TimeTracker()
    success, message = tracker.resume()
    click.echo(message)


@main.command()
def status():
    """Show the current task status."""
    tracker = TimeTracker()
    message = tracker.status()
    click.echo(message)


@main.command()
@click.argument("note_text")
def notes(note_text: str):
    """Add a note to the active task."""
    tracker = TimeTracker()
    success, message = tracker.add_note(note_text)
    click.echo(message)



@main.command()
@click.argument("when", default="today")
def log(when: str):
    """Show all tasks logged for a specific day (e.g., 'today', 'yesterday', or 'DD-MM-YYYY')."""
    tracker = TimeTracker()
    message = tracker.get_log(when)
    click.echo(message)


@main.command()
@click.option(
    "--format",
    "file_format",
    default="xlsx",
    type=click.Choice(["csv", "xlsx"]),
    help="The file format to export to.",
)
def export(file_format: str):
    """Export all time data to a file."""
    tracker = TimeTracker()
    success, message = tracker.export_log(file_format)
    click.echo(message)


@main.command()
def prev():
    """Start a new task based on the previous one."""
    tracker = TimeTracker()
    success, message = tracker.start_previous()
    click.echo(message)


if __name__ == "__main__":
    main()
