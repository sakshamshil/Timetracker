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

#### 5. Check the Current Status
To see which task is currently running and for how long, use the `status` command.

**Usage:**
```bash
track status
```
> **Output (if a task is running):**
> `🟢 Active Task: 'Developing a new feature' (15 minutes so far)`
>
> **Output (if a task is paused):**
> `⏸️ Paused Task: 'Developing a new feature' (20 minutes logged)`
>
> **Output (if no task is running):**
> `⚪ No task is currently running.`

---

#### 6. View Time Logs
To see a summary of all tasks you have logged, use the `log` command. By default, it shows today's log.

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
> 11:05:00   11:35:30   Team meeting                                           30 min
> --------------------------------------------------------------------------------
> Total time for 2025-07-19: 55 minutes
> ```

---

#### 7. Export All Data
To export your entire time log history to a file, use the `export` command.

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
