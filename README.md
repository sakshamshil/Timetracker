# track: A Simple CLI Time Tracker

A fast and simple command-line tool to track the time you spend on different tasks.

## Installation

This application is installed using `pipx` to ensure it runs in an isolated environment and is available globally.

1.  **Install `pipx`:**
    If you don't have `pipx` installed, you can install it with pip:

    ```bash
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    ```
    *You may need to restart your terminal after this step.*

2.  **Install the Application:**
    Navigate to the `project/` directory and run the following command:

    ```bash
    pipx install --editable .
    ```

This will install the `track` command on your system, allowing you to run it from any directory.

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

**Usage:**
```bash
track start "Your Task Name"
```

**Example:**
```bash
track start "Developing a new feature"
```
> **Output:**
> `🟢 Started tracking: 'Developing a new feature'`

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
> Start      End        Activity                                             Duration
> --------------------------------------------------------------------------------
> 10:30:15   10:55:20   Developing a new feature                               25 min
>   - Finished the main logic.
> 11:05:00   11:35:30   Team meeting                                           30 min
> --------------------------------------------------------------------------------
> Total time for 2025-07-19: 55 minutes
> ```

---

#### 9. Export All Data
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
-   **Exported Files:** All exported files are saved in the `project/exports/` directory within the project folder.
