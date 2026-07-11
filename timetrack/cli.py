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
@click.argument("activity", required=False)
@click.option(
    "--start",
    "start_str",
    required=False,
    help="Start time (e.g., 'today 10am', '25-07-2025 14:00').",
)
@click.option("--end", "end_str", help="End time (e.g., 'today 11am').")
@click.option("--for", "duration_str", help="Duration (e.g., '1h', '30m').")
def add(
    activity: Optional[str],
    start_str: Optional[str],
    end_str: Optional[str],
    duration_str: Optional[str],
):
    """Add a completed time entry retrospectively.

    Run with no arguments for an interactive "easy mode" that prompts for
    the activity, start time, and either an end time or a duration.
    """
    if not start_str:
        run_easy_mode(activity)
        return

    if activity is None:
        click.echo("❗ Error: You must provide an activity name.", err=True)
        return
    if not (end_str or duration_str):
        click.echo("❗ Error: You must provide either --end or --for.", err=True)
        return
    if end_str and duration_str:
        click.echo("❗ Error: You cannot provide both --end and --for.", err=True)
        return

    tracker = TimeTracker()
    success, message = tracker.add_entry(activity, start_str, end_str, duration_str)
    click.echo(message)


def run_easy_mode(initial_activity: Optional[str] = None) -> None:
    """Interactive guide for adding a time entry.

    Prompts for the activity (unless already provided), the start time, and
    then either an end time or a duration. Saves directly on success.
    """
    tracker = TimeTracker()

    activity = initial_activity
    if not activity:
        last = tracker.get_last_activity()
        activity = click.prompt("Activity name", default=last if last else "")
    while not activity or not activity.strip():
        click.echo("❗ Error: Activity name cannot be empty.", err=True)
        activity = click.prompt("Activity name", default="")

    # Collect time fields, re-prompting on validation failure.
    while True:
        start_str = click.prompt("Start time (e.g. 'today 10am', 'yesterday 3pm')")
        start_error = tracker.validate_start_time(start_str)
        if start_error:
            click.echo(f"❗ Error: {start_error}", err=True)
            continue

        end_str = click.prompt(
            "End time (leave blank to use a duration)", default=""
        )
        duration_str: Optional[str] = None
        if not end_str.strip():
            duration_str = click.prompt("Duration (e.g. '1h', '30m', '1h30m')")

        success, message = tracker.add_entry(
            activity, start_str, end_str or None, duration_str
        )
        click.echo(message)
        if success:
            return
        # On failure (end/duration), loop and re-collect the time fields.


@main.command()
@click.argument("duration_str")
@click.argument("activity")
def backdate(duration_str: str, activity: str):
    """Logs a task that just finished by backdating from the current time."""
    tracker = TimeTracker()
    success, message = tracker.backdate_entry(duration_str, activity)
    click.echo(message)


@main.command()
@click.argument("activity")
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Force start a new task, stopping the current one if it exists.",
)
def start(activity: str, force: bool):
    """Start tracking a new task."""
    tracker = TimeTracker()
    success, message = tracker.start(activity, force=force)
    click.echo(message)


@main.command()
def stop():
    """Stop the current task."""
    tracker = TimeTracker()
    success, message = tracker.stop()
    click.echo(message)


@main.command()
@click.argument("reason", required=False)
def pause(reason: Optional[str]):
    """Pause the current task, optionally with a REASON."""
    tracker = TimeTracker()
    success, message = tracker.pause(reason)
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
@click.option(
    "--days",
    default=7,
    type=int,
    help="Number of days to include in the report.",
)
def report(days: int):
    """Generate a time tracking report with terminal charts."""
    tracker = TimeTracker()
    success, message = tracker.report(days=days)
    click.echo(message)


@main.command()
@click.option(
    "--days",
    default=30,
    type=int,
    help="Number of days to include in the dashboard.",
)
@click.option(
    "--out",
    "out_dir",
    default=None,
    help="Output directory (default: ~/.timetrack/dashboard).",
)
def dashboard(days: int, out_dir: Optional[str]):
    """Generate the dashboard HTML locally (no deploy)."""
    tracker = TimeTracker()
    success, message = tracker.generate_dashboard(out_dir, days)
    click.echo(message)


@main.command()
@click.option(
    "--install-cron",
    is_flag=True,
    help="Also install a daily scheduled job to sync automatically.",
)
def sync(install_cron: bool):
    """Deploy your dashboard so you can view it from anywhere."""
    tracker = TimeTracker()
    if not tracker.get_sync_config().configured:
        _run_sync_wizard(tracker)
    if install_cron:
        ok, msg = tracker.install_cron()
        click.echo(msg)
    success, message = tracker.sync()
    click.echo(message)


def _run_sync_wizard(tracker: "TimeTracker") -> None:
    """Interactive first-run setup for `track sync`."""
    click.echo("Set up remote dashboard — deploy your time review to a static host.")
    if not click.confirm("Continue?", default=True):
        click.echo("Aborted. Run `track sync` again when ready.")
        raise SystemExit(0)

    host = "vercel"
    click.echo(f"Host: {host} (only backend in this version)")

    token = click.prompt(
        "Vercel token (run `vercel login`, or paste a VERCEL_TOKEN)",
        default="",
        show_default=False,
    ).strip()
    project = click.prompt("Project name", default="track-dash").strip()
    domain = click.prompt(
        "Custom domain? (optional, e.g. track.yourdomain.com)",
        default="",
        show_default=False,
    ).strip()
    protect = click.confirm(
        "Protect with a passphrase? (optional, not mandatory)", default=False
    )
    passphrase = None
    if protect:
        passphrase = click.prompt(
            "Passphrase", hide_input=True, confirmation_prompt=True
        )

    tracker.configure_sync(
        configured=True,
        host=host,
        token=token or None,
        project=project or "track-dash",
        domain=domain or None,
        passphrase_protected=protect,
        passphrase=passphrase,
    )
    click.echo("✅ Sync configuration saved.")


@main.command()
@click.argument("entry_id", type=int)
@click.option(
    "--when",
    default="today",
    help="Date context: 'today', 'yesterday', or 'DD-MM-YYYY'.",
)
def remove(entry_id: int, when: str):
    """Remove a specific log entry by its ID (for a given day)."""
    tracker = TimeTracker()
    success, message = tracker.remove_entry(entry_id, when)
    click.echo(message)


@main.command()
@click.argument("entry_id", type=int)
@click.option(
    "--when",
    default="today",
    help="Date context: 'today', 'yesterday', or 'DD-MM-YYYY'.",
)
def edit(entry_id: int, when: str):
    """Interactively edit a time entry (for a given day)."""
    tracker = TimeTracker()
    entry, error_msg = tracker.get_entry_by_id(entry_id, when)

    if not entry:
        click.echo(error_msg, err=True)
        return

    # Interactively get new values
    new_activity = click.prompt("Activity", default=entry.activity)
    new_start_str = click.prompt("Start Time", default=entry.start_time.isoformat())
    new_end_str = click.prompt("End Time", default=entry.end_time.isoformat())

    success, message = tracker.edit_entry(
        entry_id,
        day_filter=when,
        new_activity=new_activity,
        new_start_str=new_start_str,
        new_end_str=new_end_str,
    )
    click.echo(message)


@main.command()
def prev():
    """Start a new task based on the previous one."""
    tracker = TimeTracker()
    success, message = tracker.start_previous()
    click.echo(message)


@main.command()
@click.argument("text", required=False)
@click.option(
    "--remove",
    "-r",
    "remove_id",
    type=int,
    help="Remove a memo by its ID.",
)
@click.option(
    "--export",
    "-e",
    "export_format",
    type=click.Choice(["csv", "xlsx"]),
    help="Export all memos to a file (csv or xlsx).",
)
def memo(
    text: Optional[str],
    remove_id: Optional[int],
    export_format: Optional[str],
):
    """Manage global memos. Add with TEXT, list without args, remove with --remove ID, export with --export FORMAT."""
    tracker = TimeTracker()

    if export_format is not None:
        success, message = tracker.export_memos(export_format)
        click.echo(message)
    elif remove_id is not None:
        success, message = tracker.remove_memo(remove_id)
        click.echo(message)
    elif text:
        success, message = tracker.add_memo(text)
        click.echo(message)
    else:
        message = tracker.list_memos()
        click.echo(message)


@main.command()
def update():
    """Update the application by pulling latest changes from git."""
    tracker = TimeTracker()
    success, message = tracker.update()
    click.echo(message)
    if not success:
        raise SystemExit(1)


@main.group()
def alias():
    """Manage task aliases."""
    pass


@alias.command("add")
@click.argument("alias_name")
@click.argument("activity")
def add_alias(alias_name: str, activity: str):
    """Add or update an alias for an activity."""
    tracker = TimeTracker()
    success, message = tracker.add_alias(alias_name, activity)
    click.echo(message)


@alias.command("remove")
@click.argument("alias_name")
def remove_alias(alias_name: str):
    """Remove an alias."""
    tracker = TimeTracker()
    success, message = tracker.remove_alias(alias_name)
    click.echo(message)


@alias.command("list")
def list_aliases():
    """List all configured aliases."""
    tracker = TimeTracker()
    message = tracker.list_aliases()
    click.echo(message)


if __name__ == "__main__":
    main()
