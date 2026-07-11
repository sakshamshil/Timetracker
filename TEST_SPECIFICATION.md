# Comprehensive Test Specification for Time Tracking CLI Tool

## Document Overview
This document provides a complete inventory of all features, commands, options, methods, edge cases, validation rules, file operations, and user interactions that require testing.

---

## 1. CLI COMMANDS AND OPTIONS

### Main Command Group
- **Command**: `track` (main entry point)
- **Help text**: "A simple CLI for time tracking."

### 1.1 `add` Command
**Purpose**: Add a completed time entry retrospectively

**Arguments**:
- `activity` (required, positional): The activity name

**Options**:
- `--start` / `-s` (required): Start time (e.g., 'today 10am', '25-07-2025 14:00')
- `--end` / `-e` (optional): End time (e.g., 'today 11am')
- `--for` (optional): Duration (e.g., '1h', '30m')

**Validation Rules**:
- Must provide either `--end` OR `--for` (mutually exclusive)
- Cannot provide both `--end` AND `--for`
- Returns error: "❗ Error: You must provide either --end or --for."
- Returns error: "❗ Error: You cannot provide both --end and --for."

**Success Output**: "✅ Logged '{activity}' for {duration}."
**Error Output**: "❗ Error: {message}"

**Interactive Easy Mode**:
- Triggered when `track add` is invoked with **no arguments** (and no `--start`).
- Prompts interactively (using `click.prompt`) for:
  1. Activity name (default = last logged activity via `get_last_activity()`; empty input is re-prompted with "Activity name cannot be empty.")
  2. Start time (re-prompted on "Invalid start time format.")
  3. End time, OR a duration if the end-time prompt is left blank (mutually exclusive, mirroring the flag-based rule).
- Saves directly on success (no confirmation step).
- Backward compatible: `track add "<activity>" --start ... [--end|--for]` still works non-interactively. If `--start` is omitted but an activity is provided, easy mode is used for the time prompts.
- If `activity` is supplied positionally, the activity prompt is skipped.

---

### 1.2 `backdate` Command
**Purpose**: Logs a task that just finished by backdating from current time

**Arguments**:
- `duration_str` (required, positional): Duration (e.g., '1h', '30m')
- `activity` (required, positional): Activity name

**Success Output**: "✅ Logged '{activity}' for {duration}."
**Error Output**: "❗ Error: {message}"

---

### 1.3 `start` Command
**Purpose**: Start tracking a new task

**Arguments**:
- `activity` (required, positional): Activity name or alias (starting with @)

**Options**:
- `-f` / `--force` (flag): Force start, stopping current task if one exists

**Edge Cases**:
- If task already running and no `--force`: Error
- If task already running and `--force`: Stops current, starts new
- If alias provided (@work): Resolves to full activity name
- If alias not found: Error "❗ Error: Alias '{alias}' not found."

**Success Output**: "🟢 Started tracking: '{activity}'"
**Force Stop Output**: "✅ Stopped tracking '{activity}'. Logged {duration}.\n🟢 Started tracking: '{new_activity}'" (duration formatted via `format_minutes`, e.g. "1h 30m" / "45m")
**Error Output**: "❗ Error: {message}"

---

### 1.4 `stop` Command
**Purpose**: Stop the current task

**No arguments or options**

**Edge Cases**:
- No task running: Error "❗ No task is currently running."
- Task paused: Calculates duration up to pause time
- Task running: Calculates duration from start to now, minus paused time

**Success Output**: "✅ Stopped tracking '{activity}'. Logged {duration}." (duration via `format_minutes`, e.g. "1h 0m" / "30m")
**Error Output**: "❗ {message}"

---

### 1.5 `pause` Command
**Purpose**: Pause the current task

**Arguments**:
- `reason` (optional, positional): A free-text reason for the pause.

**Edge Cases**:
- No task running: Error
- Task already paused: Error "❗ Task '{activity}' is already paused."
- Task running: Pauses and calculates active time so far
- Reason is optional; a blank/whitespace-only reason is stored as `None`.
- Reason is saved on `ApplicationState.pause_reason` and cleared on resume.

**Success Output**: "⏸️ Paused '{activity}'. ({duration} logged so far)." (duration via `format_minutes`)
- If a reason is provided, " Reason: {reason}" is appended.
**Error Output**: "❗ {message}"

---

### 1.6 `resume` Command
**Purpose**: Resume the current paused task

**No arguments or options**

**Edge Cases**:
- No task paused: Error
- Task already running: Error "❗ Task '{activity}' is already running."
- Calculates total paused time and adds to `total_paused_seconds`
- Clears `pause_reason` (set back to `None`)

**Success Output**: "🟢 Resumed tracking: '{activity}'. ({duration} already logged)." (duration via `format_minutes`)
**Error Output**: "❗ {message}"

---

### 1.7 `status` Command
**Purpose**: Show current task status

**No arguments or options**

**Output Scenarios**:
1. No task running: "⚪ No task is currently running."
2. Task paused: "⏸️ Paused Task: '{activity}' ({duration} logged)" (duration via `format_minutes`); if a pause reason is set, " - Reason: {reason}" is appended
3. Task running: "🟢 Active Task: '{activity}' (started at {time}, {duration} so far)" (duration via `format_minutes`)
4. With notes: Displays list of notes under the task

**Note Display**:
- Truncates notes to 70 characters
- Shows up to 50 characters for activity names

---

### 1.8 `notes` Command
**Purpose**: Add a note to the active task

**Arguments**:
- `note_text` (required, positional): Note content

**Edge Cases**:
- No task running: Error "⚪ No task is currently running."

**Success Output**: "✅ Note added."
**Error Output**: "⚪ {message}"

---

### 1.9 `log` Command
**Purpose**: Show all tasks logged for a specific day

**Arguments**:
- `when` (optional, positional, default="today"): Date filter ('today', 'yesterday', 'DD-MM-YYYY')

**Output Format**:
```
--- Time Log for {date} ---
ID    Start      End        Activity                                       Duration
----------------------------------------------------------------------------------
0     09:00:00   10:00:00   Meeting                                           1h 0m
      - Note content
----------------------------------------------------------------------------------
Total time for {date}: 1h 0m
```

**Edge Cases**:
- No entries for day: "No log entries for {date}."
- No entries in log: "No entries found in the log."
- Invalid date format: "Error: Invalid date format. Please use DD-MM-YYYY."

**Features**:
- Shows day-specific IDs (0, 1, 2...)
- Truncates activity names to 42 characters
- Truncates notes to 65 characters
- Per-entry Duration and the total use `format_minutes` (e.g. "1h 30m" / "45m");
  no raw "{n} min" values
- Sorts entries by start time

---

### 1.10 `export` Command
**Purpose**: Export all time data to a file

**Options**:
- `--format` (default="xlsx", choices=["csv", "xlsx"]): File format

**Output Location**: `{project_dir}/exports/timetrack_export_{timestamp}.{format}`

**Edge Cases**:
- No entries: "No log entries to export."
- Export error: "An error occurred during export: {error}"

**Success Output**: "✅ Successfully exported all data to {path}"
**Error Output**: Error message without emoji prefix

---

### 1.11 `report` Command
**Purpose**: Generate time tracking report with terminal charts

**Options**:
- `--days` (default=7, type=int): Number of days to include

**Text Report Output**:
- ASCII bar charts for daily hours
- Activity breakdown with bar charts
- Summary statistics (total, average, days tracked, activities)

**Edge Cases**:
- No entries: "No entries found in the log."
- No entries in date range: "No entries found in the last {days} days."

**Success Output**: "✅ {report_text}"
**Error Output**: Error message without emoji prefix

---

### 1.12 `remove` Command
**Purpose**: Remove a specific log entry by ID

**Arguments**:
- `entry_id` (required, positional, type=int): Entry ID for the day

**Options**:
- `--when` (default="today"): Date context ('today', 'yesterday', 'DD-MM-YYYY')

**Edge Cases**:
- Invalid date format: Error
- No entries for day: Error
- Invalid ID: "Invalid ID: {id}. Valid IDs for {date}: 0-{max}."

**Success Output**: "✅ Removed entry: '{activity}'"
**Error Output**: "❗ {message}"

---

### 1.13 `edit` Command
**Purpose**: Interactively edit a time entry

**Arguments**:
- `entry_id` (required, positional, type=int): Entry ID for the day

**Options**:
- `--when` (default="today"): Date context

**Interactive Prompts**:
1. "Activity" (default: current value)
2. "Start Time" (default: current ISO format)
3. "End Time" (default: current ISO format)

**Edge Cases**:
- Entry not found: Error and exit
- Invalid time format during edit: Error
- End time <= start time: Error

**Success Output**: "✅ Entry {id} updated."
**Error Output**: "❗ {message}"

---

### 1.14 `prev` Command
**Purpose**: Start a new task based on the previous one

**No arguments or options**

**Edge Cases**:
- No previous task: "❗ No previous task found to start."

**Delegates to**: `start()` with last activity name

---

### 1.15 `memo` Command
**Purpose**: Manage global memos

**Arguments**:
- `text` (optional, positional): Memo text to add

**Options**:
- `-r` / `--remove` (type=int): Remove memo by ID
- `-e` / `--export` (Choice: csv|xlsx): Export all memos to a file

**Modes** (precedence: export > remove > add > list):
1. **Export mode** (--export): Exports all memos (see 2.6 `export_memos`)
2. **Remove mode** (--remove): Removes memo by ID
3. **Add mode** (text provided): Adds new memo
4. **List mode** (no args): Lists all memos

**Export Output**:
- Success: "✅ Successfully exported all memos to {path}"
- No memos: "❗ No memos to export."
- File written to `{project_dir}/exports/timetrack_memos_{timestamp}.{ext}` with
  columns `text`, `created_at`. Invalid format is rejected by Click's Choice.

**List Output**:
```
--- Memos ---
ID    Created              Note
----------------------------------------------------------------------
0     2025-01-31 10:00     Meeting notes...
----------------------------------------------------------------------
```

**Long-Memo Display**: Memo text is **not** truncated in list mode. Text longer
than the Note column width (45 chars) wraps onto continuation lines indented to
align under the Note column (indent = 27 chars). Example:
```
ID    Created              Note
----------------------------------------------------------------------
0     2025-01-31 10:00     This is a much longer memo that wraps onto
                           multiple aligned continuation lines
----------------------------------------------------------------------
```

**Edge Cases**:
- No memos: "No memos found."
- Invalid memo ID: "Invalid ID: {id}. Valid IDs: 0-{max}."
- Remove with no memos: "No memos found."
- Long memo (>45 chars): wrapped across lines, never truncated with "...".

**Success Output**: "✅ Memo added." / "✅ Memo removed: '{text}'"
**Error Output**: "❗ {message}"

---

### 1.16 `update` Command
**Purpose**: Update the application from git

**No arguments or options**

**Process**:
1. Check if git is installed
2. Verify this is a git repository (has .git directory)
3. Check for uncommitted changes
4. Check/configure git remote
5. Pull latest changes from origin/main
6. Detect installation method (pipx, pip, pip-editable)
7. Reinstall using appropriate method

**Edge Cases**:
- Git not installed: Suggests pip upgrade
- Not a git repo (PyPI install): Suggests pip upgrade
- Uncommitted changes: Error
- No remote configured: Adds default remote
- Git pull fails: Error
- Reinstall fails: Error

**Exit Code**: 1 on failure

**Success Output**: "✅ Updated successfully!\n{git_output}" or "✅ Already up to date."
**Error Output**: "❗ {message}"

---

### 1.17 `alias` Command Group
**Purpose**: Manage task aliases

**Subcommands**:

#### 1.17.1 `alias add`
**Arguments**:
- `alias_name` (required, positional): Alias name (must start with @)
- `activity` (required, positional): Full activity name

**Validation**:
- Alias must start with '@'

**Success Output**: "✅ Alias '{alias}' set to '{activity}'."
**Error Output**: "❗ Error: Alias must start with '@'."

#### 1.17.2 `alias remove`
**Arguments**:
- `alias_name` (required, positional): Alias to remove

**Edge Cases**:
- Alias not found: Error

**Success Output**: "✅ Alias '{alias}' removed."
**Error Output**: "❗ Error: Alias '{alias}' not found."

#### 1.17.3 `alias list`
**No arguments**

**Output**:
```
--- Configured Aliases ---
@work -> Working on project
@email -> Checking emails
```

**Empty Output**: "No aliases defined."

---

### 1.18 `dashboard` Command
**Purpose**: Generate the dashboard HTML locally (no deploy)

**Options**:
- `--days` (default=30, type=int): Number of trailing days to include.
- `--out` (default=`~/.timetrack/dashboard`): Output directory.

**Output**: Self-contained `index.html` (inline CSS/JS, no CDN). On success:
`✅ Dashboard written to <path>`.

---

### 1.19 `sync` Command
**Purpose**: Deploy the dashboard to a static host for viewing from anywhere

**Options**:
- `--install-cron` (flag): Also install a daily scheduled job (launchd on macOS, crontab on Linux).

**First run**: launches an interactive wizard:
- Confirms setup.
- Host: `vercel` (only backend in v1).
- Vercel token (from `vercel login` or pasted `VERCEL_TOKEN`).
- Project name (default `track-dash`).
- Optional custom domain (e.g. `track.yourdomain.com`).
- Optional passphrase protection (choice, not mandatory).
- Saves config (`config.json` → `sync`), then deploys.

**Later runs**: non-interactive; re-deploys to the same project → same URL.

**Success Output**: `✅ Dashboard live at: <url>`
**Not configured**: `❗ Sync is not set up. Run \`track sync\` to configure it first.`
**Deploy failure**: `❗ Deploy failed: <error>`

**Privacy**: with passphrase protection, data is AES-GCM encrypted client-side
(PBKDF2-HMAC-SHA256, 100k iterations, 256-bit key, 12-byte IV) before writing;
the browser decrypts after prompting for the passphrase. The host serves only
ciphertext.

---

## 2. CORE MODULES AND METHODS

### 2.1 Storage Module (`storage.py`)

**Class**: `Storage`

**Constructor**:
- `__init__(data_dir: Optional[Path] = None)`
- Creates data directory if it doesn't exist
- Sets up file paths for state, log, config, memos

**Atomic writes**: All `write_*` methods persist via the module-level
`_atomic_write(path, data)` helper, which writes to a temp file in the same
directory (`tempfile.mkstemp`), `flush()` + `os.fsync`, then `os.replace()` onto
the target. Guarantees the target file is never left half-written on
interruption (contains either the full old or full new contents); no `.tmp`
files are left behind, and the original is preserved if the write fails.

**State Operations**:
- `read_state() -> Optional[ApplicationState]`
  - Returns None if file doesn't exist
  - Returns None on JSON decode error or validation error
  
- `write_state(state: ApplicationState) -> None`
  - Writes JSON with indentation (atomically, see above)
  
- `delete_state() -> None`
  - Unlinks file if it exists

**Log Operations**:
- `read_log() -> TimeLog`
  - Returns empty TimeLog if file doesn't exist
  - Handles old format migration (date + time strings to datetime)
  - Skips malformed old entries
  - Returns empty TimeLog on JSON/validation errors
  
- `write_log(log: TimeLog) -> None`
  - Sorts entries by start_time before writing
  - Writes JSON with indentation (atomically)

**Config Operations**:
- `read_config() -> Config`
  - Returns empty Config if file doesn't exist
  - Returns empty Config on JSON/validation errors
  
- `write_config(config: Config) -> None`
  - Writes JSON with indentation (atomically)

**Memo Operations**:
- `read_memos() -> MemoList`
  - Returns empty MemoList if file doesn't exist
  - Returns empty MemoList on JSON/validation errors
  
- `write_memos(memos: MemoList) -> None`
  - Writes JSON with indentation (atomically)

---

### 2.2 Task Manager (`tasks.py`)

**Class**: `TaskManager`

**Constructor**:
- `__init__(storage: Storage)`

**Methods**:

#### `start(activity: str) -> Tuple[bool, str]`
- Checks if task already running (reads state)
- Returns error if task exists
- Creates new ApplicationState with current datetime
- Writes state to file

#### `stop() -> Tuple[bool, str]`
- Reads current state
- Returns error if no state exists
- Handles paused state: uses pause_start_time as end_time
- Handles running state: uses current time as end_time
- Calculates duration: (end - start) - total_paused_seconds
- Safeguard: ensures duration_minutes >= 0
- Creates TimeEntry
- Appends to log
- Deletes state file

#### `pause() -> Tuple[bool, str]`
- Returns error if no task running
- Returns error if already paused
- Calculates active time before pausing
- Sets status to "paused"
- Sets pause_start_time to now
- Writes state

#### `resume() -> Tuple[bool, str]`
- Returns error if no task running
- Returns error if not paused
- Calculates active time at moment of pausing
- Calculates pause duration: now - pause_start_time
- Adds to total_paused_seconds
- Sets status to "running"
- Clears pause_start_time
- Writes state

#### `status() -> str`
- Returns formatted status string
- Handles paused vs running states
- Calculates elapsed time accounting for pauses
- Truncates activity names to 50 chars
- Includes notes if present (truncated to 70 chars)

#### `add_note(note_text: str) -> Tuple[bool, str]`
- Returns error if no task running
- Appends note to state.notes list
- Writes state

#### `is_running() -> bool`
- Returns True if state file exists and is valid

#### `get_current_activity() -> str`
- Returns activity name from state
- Returns empty string if no task

---

### 2.3 Entry Manager (`entries.py`)

**Class**: `EntryManager`

**Constructor**:
- `__init__(storage: Storage)`

**Private Methods**:

#### `_get_entries_for_day(day_filter: str) -> Tuple[List[TimeEntry], Optional[date]]`
- Parses day filter using `parse_day_filter()`
- Returns ([], None) if parsing fails
- Filters log entries by date
- Sorts by start_time

**Public Methods**:

#### `get_log(day_filter: str) -> str`
- Validates date format
- Filters entries for target date
- Returns formatted table with IDs, times, activities, durations
- Includes notes under each entry
- Shows total time for the day
- Handles empty log and empty day cases

#### `add(activity, start_str, end_str, duration_str) -> Tuple[bool, str]`
- Replaces "today" and "yesterday" in time strings with actual dates
- Parses start time using dateutil
- Parses end time OR duration
- Validates end_time > start_time
- Calculates duration in minutes
- Creates TimeEntry
- Appends to log
- Sorts log by start_time

#### `backdate(duration_str, activity) -> Tuple[bool, str]`
- Parses duration
- Calculates start_time = now - duration
- Sets end_time = now
- Creates TimeEntry
- Appends and sorts log

#### `remove(entry_id, day_filter) -> Tuple[bool, str]`
- Gets entries for day
- Validates ID is in range
- Finds entry by matching start_time
- Removes from full log
- Writes log

#### `get_by_id(entry_id, day_filter) -> Tuple[Optional[TimeEntry], str]`
- Gets entries for day
- Validates ID
- Returns entry or None with error message

#### `edit(entry_id, day_filter, new_activity, new_start_str, new_end_str) -> Tuple[bool, str]`
- Gets original entry by ID
- Uses provided values or keeps original
- Parses new times if provided
- Validates end_time > start_time
- Calculates new duration
- Preserves original notes
- Replaces entry in log by matching start_time
- Writes log

#### `get_last_activity() -> Optional[str]`
- Reads log
- Returns activity of most recent entry
- Returns None if no entries

---

### 2.4 Alias Manager (`aliases.py`)

**Class**: `AliasManager`

**Constructor**:
- `__init__(storage: Storage)`

**Methods**:

#### `resolve_alias(activity: str) -> Optional[str]`
- Returns activity unchanged if not starting with @
- Looks up alias in config
- Returns None if alias not found

#### `add(alias: str, activity: str) -> Tuple[bool, str]`
- Validates alias starts with @
- Reads config
- Adds/updates alias
- Writes config

#### `remove(alias: str) -> Tuple[bool, str]`
- Reads config
- Returns error if alias not found
- Deletes alias
- Writes config

#### `list_all() -> str`
- Reads config
- Returns formatted list or "No aliases defined."

---

### 2.5 Memo Manager (`memos.py`)

**Class**: `MemoManager`

**Constructor**:
- `__init__(storage: Storage)`

**Methods**:

#### `add(text: str) -> Tuple[bool, str]`
- Creates Memo with current datetime
- Reads memos
- Appends new memo
- Writes memos

#### `list_all() -> str`
- Reads memos
- Returns formatted table with ID, Created, Note
- Wraps note text at 45 chars (`textwrap.wrap`); continuation lines are indented
  27 chars to align under the Note column. Notes are never truncated.
- Returns "No memos found." if empty

#### `remove(memo_id: int) -> Tuple[bool, str]`
- Reads memos
- Returns error if no memos
- Validates ID is in range 0 to len-1
- Removes memo at index
- Writes memos
- Returns truncated text of removed memo

---

### 2.6 Report Manager (`reports.py`)

**Class**: `ReportManager`

**Constructor**:
- `__init__(storage: Storage)`

**Methods**:

#### `generate_text_report(days: int = 7) -> str`
- Gets entries from last N days
- Groups by date (daily_hours)
- Groups by activity (activity_hours)
- Generates ASCII bar charts
- Calculates statistics (total, average, days, activities)
- Returns formatted string

#### `export_log(file_format: str) -> Tuple[bool, str]`
- Reads log
- Returns error if no entries
- Converts entries to dicts
- Joins notes with newlines
- Creates pandas DataFrame
- Creates exports/ directory
- Exports to CSV or XLSX with timestamp

#### `export_memos(file_format: str) -> Tuple[bool, str]`
- Reads memos
- Returns "No memos to export." if none
- Converts memos to dicts (columns: text, created_at)
- Creates pandas DataFrame
- Creates exports/ directory
- Exports to `timetrack_memos_{timestamp}.{ext}` (CSV or XLSX); returns
  "Unsupported format: {fmt}" for anything else
- Success: "Successfully exported all memos to {path}"

#### `report(days: int = 7) -> Tuple[bool, str]`
- Delegates to the text report generator
- Default: 7 days (or passed value)

---

### 2.7 Update Manager (`updater.py`)

**Class**: `UpdateManager`

**Constructor**:
- `__init__()`: Sets repo_dir to parent of timetrack package

**Private Methods**:

#### `_check_remote_exists() -> Tuple[bool, str]`
- Runs `git remote get-url origin`
- Returns (exists, url)

#### `_add_remote(remote_url: str) -> Tuple[bool, str]`
- Runs `git remote add origin {url}`
- Returns success/failure

#### `_detect_installation_method() -> str`
- Checks pipx list for timetrack-cli or track
- Checks pip show for editable install
- Returns: 'pipx', 'pip', 'pip-editable'

**Public Methods**:

#### `update() -> Tuple[bool, str]`
- Step 1: Check git is installed (fallback to pip upgrade)
- Step 2: Verify .git directory exists
- Step 3: Check for uncommitted changes
- Step 4: Check/add remote
- Step 5: Pull from origin/main
- Step 6: Detect and use installation method
  - pipx: reinstall timetrack-cli or install -e . --force
  - pip/pip-editable: install -e .
- Returns appropriate messages for each failure point

---

### 2.8 TimeTracker Facade (`facade.py`)

**Class**: `TimeTracker`

**Constructor**:
- `__init__()`: Initializes all managers

**Task Lifecycle Methods** (add emoji prefixes):
- `start(activity, force)`: Resolves aliases, handles force stop
- `stop()`: Delegates to TaskManager
- `pause()`: Delegates to TaskManager
- `resume()`: Delegates to TaskManager
- `status()`: Adds emoji prefixes based on state
- `add_note()`: Delegates to TaskManager
- `start_previous()`: Gets last activity, calls start()

**Entry Management Methods**:
- `get_log(day_filter)`: Delegates to EntryManager
- `add_entry(activity, start_str, end_str, duration_str)`: Delegates to EntryManager
- `backdate_entry(duration_str, activity)`: Delegates to EntryManager
- `remove_entry(entry_id, day_filter)`: Delegates to EntryManager
- `get_entry_by_id(entry_id, day_filter)`: Delegates to EntryManager
- `edit_entry(entry_id, day_filter, new_activity, new_start_str, new_end_str)`: Delegates to EntryManager

**Alias Management Methods**:
- `add_alias(alias, activity)`: Delegates to AliasManager
- `remove_alias(alias)`: Delegates to AliasManager
- `list_aliases()`: Delegates to AliasManager

**Memo Management Methods**:
- `add_memo(text)`: Delegates to MemoManager
- `list_memos()`: Delegates to MemoManager
- `remove_memo(memo_id)`: Delegates to MemoManager
- `export_memos(file_format)`: Delegates to ReportManager

**Report/Export Methods**:
- `export_log(file_format)`: Delegates to ReportManager
- `generate_text_report(days)`: Delegates to ReportManager
- `report(days)`: Delegates to ReportManager

**Dashboard & Sync Methods**:
- `get_sync_config() -> SyncConfig`: Returns current sync config.
- `configure_sync(**changes) -> (bool, str)`: Persists sync config fields.
- `generate_dashboard(out_dir, days) -> (bool, str)`: Generates local `index.html` (uses stored passphrase when `passphrase_protected`).
- `sync() -> (bool, str)`: Generates then deploys via the configured backend; stable URL.
- `install_cron() -> (bool, str)`: Installs daily scheduled job (launchd/crontab).

**Update Method**:
- `update()`: Delegates to UpdateManager

---

### 2.9 Utilities (`utils.py`)

**Functions**:

#### `parse_duration(duration_str: str) -> Optional[timedelta]`
- Pattern: `((?P<hours>\d+)h)?((?P<minutes>\d+)m)?`
- Supports: "1h", "30m", "1h30m", "90m"
- Returns None if no matches

#### `format_duration(duration: timedelta) -> str`
- Converts to total minutes
- Returns "Xh Ym" or "Ym" format

#### `format_minutes(minutes: int) -> str`
- Convenience wrapper: `format_duration(timedelta(minutes=minutes))`
- Returns "Xh Ym" (when >= 60) or "Ym" (e.g. 90 -> "1h 30m", 45 -> "45m", 0 -> "0m")
- Used for user-facing durations in `track log` and task status/stop/pause/resume messages

#### `truncate_text(text: str, max_length: int, suffix: str = "...") -> str`
- Returns original if <= max_length
- Otherwise truncates and adds suffix

#### `parse_day_filter(day_filter: str) -> Optional[date]`
- "today" -> date.today()
- "yesterday" -> date.today() - 1 day
- "DD-MM-YYYY" -> parsed date
- Returns None on ValueError

---

## 3. DATA MODELS

### 3.1 ApplicationState (`models.py`)
**Fields**:
- `activity: str` - Task name
- `start_time: datetime` - When task started
- `status: str = "running"` - "running" or "paused"
- `pause_start_time: Optional[datetime] = None` - When pause began
- `total_paused_seconds: float = 0.0` - Accumulated pause time
- `pause_reason: Optional[str] = None` - Optional reason for the current pause
- `notes: List[str] = Field(default_factory=list)` - Task notes

### 3.2 TimeEntry
**Fields**:
- `start_time: datetime`
- `end_time: datetime`
- `activity: str`
- `duration_minutes: int`
- `notes: List[str] = Field(default_factory=list)`

### 3.3 TimeLog
**Fields**:
- `entries: List[TimeEntry] = Field(default_factory=list)`

### 3.4 Config
**Fields**:
- `aliases: Dict[str, str] = Field(default_factory=dict)`

### 3.5 Memo
**Fields**:
- `text: str`
- `created_at: datetime`

### 3.6 MemoList
**Fields**:
- `memos: List[Memo] = Field(default_factory=list)`

---

## 4. FILE OPERATIONS

### 4.1 Data Directory
**Path**: `~/.timetrack/`
**Created**: On Storage initialization with `mkdir(parents=True, exist_ok=True)`

### 4.2 State File
**Path**: `~/.timetrack/state.json`
**Format**: JSON serialization of ApplicationState
**Created**: When task starts
**Modified**: On pause, resume, note add
**Deleted**: When task stops

### 4.3 Log File
**Path**: `~/.timetrack/timelog.json`
**Format**: JSON serialization of TimeLog
**Created**: On first entry add
**Modified**: On entry add, remove, edit
**Entries**: Sorted by start_time on write
**Migration**: Handles old format (date + time strings) to datetime

### 4.4 Config File
**Path**: `~/.timetrack/config.json`
**Format**: JSON serialization of Config
**Created**: On first alias add
**Modified**: On alias add, remove, or `track sync` setup

**Fields**:
- `aliases`: Dict[str, str]
- `sync`: SyncConfig block:
  - `configured` (bool): wizard completed.
  - `host` (str): deploy backend (v1: `vercel`).
  - `project` (str): host project name (`track-dash`).
  - `domain` (Optional[str]): custom domain.
  - `token` (Optional[str]): host API token (local only).
  - `passphrase_protected` (bool): whether data is encrypted.
  - `passphrase` (Optional[str]): stored locally so cron can re-encrypt.
  - `cron_installed` (bool): daily job installed.

### 4.5 Memos File
**Path**: `~/.timetrack/memos.json`
**Format**: JSON serialization of MemoList
**Created**: On first memo add
**Modified**: On memo add, remove

### 4.6 Export Directory
**Path**: `{project_dir}/exports/`
**Created**: On export with `mkdir(parents=True, exist_ok=True)`
**Files**: `timetrack_export_{timestamp}.csv` or `.xlsx`

### 4.7 Reports Directory
No HTML report directory is created. Reports are rendered as text directly to the terminal via `track report`.

### 4.8 Dashboard Directory
**Path**: `~/.timetrack/dashboard/`
**Created**: On `track dashboard` or `track sync` (generate step)
**Files**: `index.html` (self-contained; deployed to the host)

---

## 5. VALIDATION RULES

### 5.1 Time Parsing
**Start/End Time Formats**:
- `today 10am`, `today 14:00`
- `yesterday 10am`
- `25-07-2025 14:00`
- ISO format: `2025-07-25T14:00:00`
- Uses dateutil.parser with `dayfirst=True`

**Duration Format**:
- Pattern: `^(\d+h)?(\d+m)?$`
- Examples: `1h`, `30m`, `1h30m`, `90m`
- Minimum: Must have at least hours or minutes

**Date Filter Format**:
- `today`
- `yesterday`
- `DD-MM-YYYY` (e.g., `25-07-2025`)

### 5.2 Time Validation
- End time must be after start time
- Duration calculation: rounds to nearest minute
- Negative durations are set to 0 (safeguard)

### 5.3 ID Validation
- Entry IDs are day-specific (0-indexed)
- Valid range: 0 to (number of entries for day - 1)
- Memo IDs are global (0-indexed)
- Valid range: 0 to (number of memos - 1)

### 5.4 Alias Validation
- Must start with `@`
- Case-sensitive
- Stored in config.aliases dict

### 5.5 Activity Names
- No specific validation
- Can contain any string
- Resolved from alias if starts with @

---

## 6. EDGE CASES AND ERROR CONDITIONS

### 6.1 File System Errors
- Permission denied on data directory creation
- Permission denied on file read/write
- Disk full
- Corrupted JSON files (handled by returning empty/default)
- Missing data directory (auto-created)

### 6.2 Concurrent Access
- Multiple processes reading/writing state
- Race conditions on start/stop

### 6.3 Time Edge Cases
- Daylight saving time transitions
- Entries spanning midnight
- Future dates
- Very old dates
- Zero-duration entries
- Negative duration prevention

### 6.4 State Inconsistencies
- State file exists but is corrupted (return None)
- Task paused but no pause_start_time (error on stop)
- Pause/resume without state file

### 6.5 Empty Data
- Reading empty log
- Reading empty config
- Reading empty memos
- Removing from empty list
- Editing non-existent entry

### 6.6 Boundary Conditions
- Entry ID = 0 (first entry)
- Entry ID = max (last entry)
- Entry ID = -1 (invalid)
- Entry ID > max (invalid)
- Memo ID boundaries

### 6.7 Format Migration
- Old format entries with separate date and time fields
- Malformed old entries (skipped)
- Mixed old and new format in same log

### 6.8 Update Edge Cases
- Git not in PATH
- .git directory missing (PyPI install)
- Uncommitted changes
- No remote configured
- Git pull fails (network, conflicts)
- Reinstall fails

### 6.9 Export/Report Edge Cases
- Empty log
- No entries in date range
- Very long activity names (truncation)
- Notes with newlines (joined with \n)
- Export write errors

---

## 7. USER INTERACTIONS

### 7.1 Interactive Prompts
**Edit Command**:
- Prompt: "Activity" with current value as default
- Prompt: "Start Time" with current ISO format as default
- Prompt: "End Time" with current ISO format as default

### 7.2 Output Formatting
**Emojis**:
- ✅ Success
- ❗ Error
- ⚪ Neutral/Info
- 🟢 Active/Running/Started
- ⏸️ Paused

**Text Truncation**:
- Activity names: 42-50 chars (varies by context)
- Notes: 45-70 chars (varies by context)
- Memos: 30-45 chars (varies by context)

### 7.3 Table Formatting
**Log Table**:
- ID: 5 chars left-aligned
- Start/End: 10 chars left-aligned (HH:MM:SS)
- Activity: 45 chars left-aligned
- Duration: 10 chars right-aligned
- Separator line: 82 chars

**Memos Table**:
- ID: 5 chars left-aligned
- Created: 20 chars left-aligned (YYYY-MM-DD HH:MM)
- Note: remaining space
- Separator line: 70 chars

### 7.4 Progress Indicators
**ASCII Bar Charts** (text report):
- Width: 30 chars for daily, 25 for activity
- Character: `#` for value, `-` for empty
- Scaled relative to max value

---

## 8. CROSS-CUTTING CONCERNS

### 8.1 Timezone Handling
- Uses local system time (datetime.now())
- All times stored in local timezone
- No explicit timezone conversion

### 8.2 Sorting
- Log entries sorted by start_time on write
- Daily entries sorted chronologically for display
- Activities sorted by hours (descending) in reports

### 8.3 Duration Calculations
- Total seconds -> round to minutes
- Active time = (end - start) - total_paused_seconds
- Pause duration = now - pause_start_time

### 8.4 State Transitions
```
Start -> Running -> Stop -> Logged
Running -> Pause -> Paused -> Resume -> Running
Paused -> Stop -> Logged (with pause_start_time as end)
```

---

## 9. TEST CATEGORIES SUMMARY

### Unit Tests Required For:
1. **Storage Module**: All CRUD operations, error handling, migration
2. **Task Manager**: Start/stop/pause/resume/status/note lifecycle
3. **Entry Manager**: Add/edit/remove/backdate/get operations
4. **Alias Manager**: Resolve/add/remove/list operations
5. **Memo Manager**: Add/remove/list operations
6. **Report Manager**: Text report generation, CSV/XLSX export
7. **Update Manager**: Git operations, installation detection
8. **Utils**: Parse functions, formatting, truncation
9. **Models**: Validation, serialization

### Integration Tests Required For:
1. **CLI Commands**: All commands with various option combinations
2. **End-to-End Workflows**: Full task lifecycle
3. **Error Handling**: All error conditions
4. **File Operations**: Concurrent access, corruption recovery
5. **Alias Resolution**: Integration with start command
6. **State Persistence**: State survives across operations

### Edge Case Tests Required For:
1. Empty data scenarios
2. Invalid inputs
3. Boundary conditions
4. File corruption
5. Time edge cases (DST, midnight, future dates)
6. Concurrent access
7. Migration scenarios

---

## 10. DEPENDENCIES

### Required:
- `click` - CLI framework
- `pydantic` - Data validation and serialization
- `dateutil` - Flexible date/time parsing
- `pandas` - Data export (CSV/XLSX)
- `openpyxl` - Excel file writing

### Testing:
- `pytest` - Test framework
- `freezegun` - Datetime mocking
- `pytest-cov` - Coverage reporting

---

## 11. FILE LOCATIONS

### Source Files:
- `/home/saksham/Desktop/projects/Timetracker/timetrack/cli.py` - CLI commands
- `/home/saksham/Desktop/projects/Timetracker/timetrack/models.py` - Data models
- `/home/saksham/Desktop/projects/Timetracker/timetrack/core/storage.py` - File I/O
- `/home/saksham/Desktop/projects/Timetracker/timetrack/core/tasks.py` - Task lifecycle
- `/home/saksham/Desktop/projects/Timetracker/timetrack/core/entries.py` - Entry management
- `/home/saksham/Desktop/projects/Timetracker/timetrack/core/aliases.py` - Alias management
- `/home/saksham/Desktop/projects/Timetracker/timetrack/core/memos.py` - Memo management
- `/home/saksham/Desktop/projects/Timetracker/timetrack/core/reports.py` - Reports & export
- `/home/saksham/Desktop/projects/Timetracker/timetrack/core/updater.py` - Self-update
- `/home/saksham/Desktop/projects/Timetracker/timetrack/core/facade.py` - Main API
- `/home/saksham/Desktop/projects/Timetracker/timetrack/core/utils.py` - Utilities
- `/home/saksham/Desktop/projects/Timetracker/timetrack/core/constants.py` - Constants

### Data Files:
- `~/.timetrack/state.json` - Current task state
- `~/.timetrack/timelog.json` - Completed entries
- `~/.timetrack/config.json` - Aliases configuration
- `~/.timetrack/memos.json` - Global memos

### Output Directories:
- `{project_dir}/exports/` - CSV/XLSX exports

---

*End of Test Specification*
