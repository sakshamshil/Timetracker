# track: A Simple CLI Time Tracker

A fast and simple command-line tool to track the time you spend on different tasks.

## Installation

One-line install (requires Python 3.8+):

```bash
curl -fsSL https://raw.githubusercontent.com/sakshamshil/Timetracker/main/install-remote.sh | bash
```

This will:
- Check for Python 3.8+
- Install pipx if not present
- Clone the repo to `~/.timetrack-repo`
- Install the `track` command globally

**Also available on PyPI**: https://test.pypi.org/project/timetrack-cli/

### Requirements

- **OS**: Linux, macOS, or WSL (Windows Subsystem for Linux)
- **Python**: 3.8 or higher
- **Tools**: `curl`, `git`, `bash`

### Troubleshooting

**"track: command not found"**
- Restart your terminal or run: `source ~/.bashrc` (or `~/.zshrc` for zsh)

**Permission errors**
- Run: `python3 -m pipx ensurepath` then restart terminal

**Behind a corporate proxy**
```bash
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
curl -fsSL https://raw.githubusercontent.com/sakshamshil/Timetracker/main/install-remote.sh | bash
```

## Updating

Run the built-in update command:

```bash
track update
```

This pulls the latest code from GitHub and reinstalls automatically.

## Uninstalling

```bash
pipx uninstall timetrack-cli  # or track
rm -rf ~/.timetrack-repo      # remove source code
rm -rf ~/.timetrack           # remove data files
```

## How to Use

All commands are run from your terminal.

### General Syntax
```bash
track [COMMAND]
```

---

### Commands

#### 1. Start a Task
To begin tracking time for a new activity, use the `start` command followed by the name of the task.

If a task is already running, you can use the `-f` or `--force` flag to automatically stop the current task and start the new one.

**Usage:**
```bash
track start "Your Task Name" [-f | --force]
```

**Examples:**

**1. Start a new task when no other task is running:**
```bash
track start "Developing a new feature"
```
> **Output:**
> `🟢 Started tracking: 'Developing a new feature'`

**2. Force start a new task when another is already running:**
```bash
track start "Urgent bug fix" --force
```
> **Output:**
> ```
> ✅ Stopped tracking 'Developing a new feature'. Logged 30 minutes.
> 🟢 Started tracking: 'Urgent bug fix'
> ```

---

#### 2. Stop the Current Task
When you have finished working on a task, use the `stop` command.

**Usage:**
```bash
track stop
```
> **Output:**
> `✅ Stopped tracking 'Developing a new feature'. Logged 25 minutes.`

---

#### 3. Pause the Current Task
If you need to take a break, use the `pause` command.

**Usage:**
```bash
track pause
```
> **Output:**
> `⏸️ Paused 'Developing a new feature'.`

---

#### 4. Resume a Paused Task
To continue a task that was previously paused, use the `resume` command.

**Usage:**
```bash
track resume
```
> **Output:**
> `🟢 Resumed tracking: 'Developing a new feature'`

---

#### 5. Add a Note to the Current Task
While a task is running, you can add multiple notes to it. This is useful for logging details, progress, or any other relevant information.

**Usage:**
```bash
track notes "<NOTE_TEXT>"
```

**Example:**
```bash
track notes "Finished the main logic, now writing tests."
```
> **Output:**
> `✅ Note added.`

---

#### 6. Check the Current Status
To see which task is currently running and for how long, use the `status` command. The output will also include any notes you've added.

**Usage:**
```bash
track status
```
> **Output (if a task is running with notes):**
> ```
> 🟢 Active Task: 'Developing a new feature' (15 minutes so far)
>    Notes:
>      - Finished the main logic, now writing tests.
> ```
>
> **Output (if a task is paused):**
> `⏸️ Paused Task: 'Developing a new feature' (20 minutes logged)`
>
> **Output (if no task is running):**
> `⚪ No task is currently running.`

---

#### 7. Add a Manual Time Entry
For moments when you forget to use `start` and `stop`, the `add` command lets you log time retrospectively. It's a flexible tool that accepts a variety of date, time, and duration formats.

**Usage:**
```bash
track add "<ACTIVITY>" --start "<TIME>" [--end "<TIME>" | --for "<DURATION>"]
```

**Arguments & Options:**
-   `"<ACTIVITY>"` (Required): The name of the task you are logging.
-   `--start "<TIME>"` (Required): The start time of the task.
-   `--end "<TIME>"` (Optional): The end time of the task. You must provide either `--end` or `--for`.
-   `--for "<DURATION>"` (Optional): The duration of the task. You must provide either `--end` or `--for`.

**Key Features:**
-   You must provide a start time and **either** an end time or a duration, but not both.
-   The command intelligently parses a wide range of time and duration formats.

**Time Format Examples (`--start` and `--end`):**
The time parser is highly flexible. Here are some of the formats you can use:
-   **Relative Dates:** `today 10:00`, `yesterday 3pm`, `today 14:30:15`
-   **Absolute Dates:** `25-07-2025 10:00`, `2025-07-25 14:30`, `July 25 2025 2:30pm`
-   **Time Only:** `10:00` (defaults to today), `3:15pm`

**Duration Format Examples (`--for`):**
Provide durations in a simple, combined format:
-   `1h` (1 hour)
-   `30m` (30 minutes)
-   `2h15m` (2 hours and 15 minutes)
-   `90m` (90 minutes)

**Examples:**
```bash
# Log a 2-hour task that happened today
track add "Team Retrospective" --start "today 2pm" --for "2h"

# Log a task from yesterday with a specific start and end time
track add "Design review" --start "yesterday 10:00" --end "yesterday 11:30"

# Log a task with a specific date
track add "Client call" --start "22-07-2025 15:00" --for "45m"
```

---

#### 8. View Time Logs
To see a summary of all tasks you have logged, use the `log` command. By default, it shows today's log. Any notes associated with a task will be displayed beneath it.

**Usage:**
```bash
track log [WHEN]
```
The `WHEN` argument can be:
- `today` (default)
- `yesterday`
- A date in `DD-MM-YYYY` format (e.g., `19-07-2025`)

**Example:**
```bash
track log yesterday
```
> **Output:**
> ```
> --- Time Log for 2025-07-19 ---
> ID    Start      End        Activity                                             Duration
> --------------------------------------------------------------------------------
> 0     10:30:15   10:55:20   Developing a new feature                               25 min
>       - Finished the main logic.
> 1     11:05:00   11:35:30   Team meeting                                           30 min
> --------------------------------------------------------------------------------
> Total time for 2025-07-19: 55 minutes
> ```

---

#### 9. Remove a Log Entry
To remove a specific time entry from your log, use the `remove` command with the ID of the entry you want to delete. You can find the ID for each entry by running `track log`.

**Usage:**
```bash
track remove <ID> [--when WHEN]
```

**Arguments & Options:**
-   `<ID>` (Required): The numerical ID of the log entry to be removed.
-   `--when WHEN` (Optional): Specifies the day from which to remove the entry. It accepts the same formats as the `log` command (`today`, `yesterday`, or `DD-MM-YYYY`). Defaults to `today`.

**Example:**
First, view the log to find the ID of the entry you want to remove:
```bash
track log
```
> **Output:**
> ```
> --- Time Log for 2025-07-26 ---
> ID    Start      End        Activity                  Duration
> ----------------------------------------------------------------------
> 0     09:00:00   10:00:00   Team Stand-up             60 min
> 1     10:15:00   11:00:00   Code Review               45 min
> ----------------------------------------------------------------------
> Total time for 2025-07-26: 1h 45m
> ```

Now, remove the "Team Stand-up" entry using its ID:
```bash
track remove 0
```
> **Output:**
> `✅ Removed entry: 'Team Stand-up'`

---

#### 10. Edit a Log Entry
To edit a specific time entry from your log, use the `edit` command with the ID of the entry you want to change. You can find the ID for each entry by running `track log`.

**Usage:**
```bash
track edit <ID> [--when WHEN]
```

**Arguments & Options:**
-   `<ID>` (Required): The numerical ID of the log entry to be edited.
-   `--when WHEN` (Optional): Specifies the day from which to edit the entry. It accepts the same formats as the `log` command (`today`, `yesterday`, or `DD-MM-YYYY`). Defaults to `today`.

**Example:**
First, view the log to find the ID of the entry you want to edit:
```bash
track log
```
> **Output:**
> ```
> --- Time Log for 2025-09-26 ---
> ID    Start      End        Activity                  Duration
> ----------------------------------------------------------------------
> 0     09:00:00   10:00:00   Team Stand-up             60 min
> 1     10:15:00   11:00:00   Code Review               45 min
> ----------------------------------------------------------------------
> Total time for 2025-09-26: 1h 45m
> ```

Now, edit the "Code Review" entry using its ID:
```bash
track edit 1
```
> **Output:**
> ```
> Activity [Code Review]:
> Start Time [2025-09-26T10:15:00]: 2025-09-26T10:20:00
> End Time [2025-09-26T11:00:00]:
> ✅ Entry 1 updated.
> ```

---

#### 11. Manage Task Aliases
To save time on frequently used task names, you can create aliases.

**Usage:**
```bash
track alias [COMMAND]
```

**Commands:**

-   **`add <ALIAS_NAME> "<FULL_ACTIVITY>"`**
    Adds a new alias or updates an existing one. It's recommended to prefix aliases with `@` to distinguish them from regular task names.

    *Example:*
    ```bash
    track alias add @docs "Writing documentation for Project Phoenix"
    ```
    > **Output:**
    > `✅ Alias '@docs' set to 'Writing documentation for Project Phoenix'.`

-   **`remove <ALIAS_NAME>`**
    Removes a specified alias.

    *Example:*
    ```bash
    track alias remove @docs
    ```
    > **Output:**
    > `✅ Alias '@docs' removed.`

-   **`list`**
    Shows all aliases you have configured.

    *Example:*
    ```bash
    track alias list
    ```
    > **Output:**
    > ```
    > --- Configured Aliases ---
    > @docs -> Writing documentation for Project Phoenix
    > @projx -> Internal Project Phoenix - Scoping
    > ```

---

#### 12. Start the Previous Task
Quickly restart the last task you logged without typing the full name.

**Usage:**
```bash
track prev
```
> **Output:**
> `🟢 Started tracking: 'Team meeting'`

---

#### 13. Backdate a Task
If you just finished a task but forgot to track it, use `backdate` to quickly log it by specifying how long you spent. The end time is set to "now" and the start time is calculated automatically.

**Usage:**
```bash
track backdate <DURATION> "<ACTIVITY>"
```

**Duration Format:**
-   `1h` (1 hour)
-   `30m` (30 minutes)
-   `2h15m` (2 hours and 15 minutes)

**Example:**
```bash
track backdate 2h "Team meeting"
```
> **Output:**
> `✅ Logged 'Team meeting' for 2h 0m.`

---

#### 14. Global Memos
Unlike task notes (which are tied to a running task), memos are standalone notes you can add anytime. Use them for quick reminders, TODOs, or anything you want to jot down.

**Usage:**
```bash
# Add a memo
track memo "<TEXT>"

# List all memos
track memo

# Remove a memo by ID
track memo --remove <ID>
```

**Examples:**

**1. Add a memo:**
```bash
track memo "Fix bug in timelogger"
```
> **Output:**
> `✅ Memo added.`

**2. List all memos:**
```bash
track memo
```
> **Output:**
> ```
> --- Memos ---
> ID    Created              Note
> ----------------------------------------------------------------------
> 0     2025-12-23 15:30     Fix bug in timelogger
> 1     2025-12-23 16:00     Review PR #42
> ----------------------------------------------------------------------
> ```

**3. Remove a memo:**
```bash
track memo --remove 0
```
> **Output:**
> `✅ Memo removed: 'Fix bug in timelogger'`

---

#### 15. Update the Application
Keep your installation up to date by pulling the latest changes from GitHub and reinstalling.

**Usage:**
```bash
track update
```

**What it does:**
1. Checks for uncommitted local changes (fails if found)
2. Runs `git pull origin main`
3. Reinstalls with `pipx reinstall track` (or `pip install -e .` as fallback)

**Example:**
```bash
track update
```
> **Output (when updates available):**
> ```
> ✅ Updated successfully!
> Updating 508fbee..a1b2c3d
> Fast-forward
>  timetrack/core.py | 50 ++++++++++++++++++++++++++++++++++++++++++++++++++
>  1 file changed, 50 insertions(+)
> ```
>
> **Output (when already up to date):**
> `✅ Already up to date. No changes to pull.`
>
> **Output (when you have uncommitted changes):**
> `❗ Error: You have uncommitted changes. Please commit or stash them first.`

---

#### 16. Export All Data
To export your entire time log history to a file, use the `export` command. The exported file will include a `notes` column where multiple notes are separated by newlines.

**Usage:**
```bash
track export [--format FORMAT]
```
The `FORMAT` can be `csv` or `xlsx` (default is `xlsx`).

**Example:**
```bash
track export --format csv
```
> **Output:**
> `✅ Successfully exported all data to /path/to/project/exports/timetrack_export_20250720_221403.csv`

---

### Data and Export Files

-   **Log Data:** The application stores its data in the `~/.timetrack` directory.
    -   `timelog.json`: A persistent log of all your completed time entries.
    -   `state.json`: A temporary file that only exists when a task is actively being tracked or paused.
    -   `config.json`: Stores your task aliases.
    -   `memos.json`: Stores your global memos.
-   **Exported Files:** All exported files are saved in the `project/exports/` directory within the project folder.
