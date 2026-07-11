# Issues / Feature Backlog

This file tracks planned work. Items are picked off one-by-one (replicate →
debug → fix). Nothing here is being worked on until explicitly selected.

---

## 1. Interactive "easy mode" for adding tasks
Add an interactive "easy mode" for adding tasks.

### Status
**✅ Done** — implemented, tested (unit + manual CLI), docs updated.

### Outcome / verification
- `tests/test_easy_mode.py` added: 6 tests (end-time path, duration path,
  invalid-start re-prompt, empty-activity re-prompt, preset activity,
  non-interactive backward compat). **All pass.**
- Full suite: 150 passed, 4 **pre-existing** failures in `test_facade.py`
  (date-parsing/`today`/`yesterday` handling + report) — confirmed failing on
  the unmodified code too, **not** caused by this change. Tracked separately
  (see note below).
- Manual smoke test via the installed `track` binary (isolated temp HOME):
  `track add` with no args guides through activity → start → end/duration and
  logs correctly; `track log` shows the entries with correct durations.
- CLI tests isolate storage by monkeypatching `timetrack.core.constants` **and**
  `timetrack.core.storage` module-level paths (Storage imports them by value),
  so the real `~/.timetrack` is never touched.

> **Note (separate bug, out of scope for item 1):** `EntryManager.add` swaps
> `today`/`yesterday` substitution into `YYYY-MM-DD` then `dateutil.parse(...,
> dayfirst=True)` produces wrong months (e.g. "today 10am" → month 10). This
> breaks `test_facade.py` report/entry tests and affects manual use. Recommend
> a dedicated fix (likely drop `dayfirst` for ISO-style substituted strings or
> parse `today`/`yesterday` as `date` objects).

### Clarification (confirmed with user)
- **Trigger:** No-arg `track add` launches the interactive prompts.
- **Fields prompted:** Activity name, Start time, and End time OR duration (notes excluded).
- **Confirmation:** Save directly after collecting inputs (no yes/no confirm step).

### Replication (current behavior)
- `add` is defined in `timetrack/cli.py:25`. It takes a **required** positional
  `activity` and a **required** `--start` option, plus optional `--end`/`--for`
  (mutually exclusive).
- Invoking `track add` with no args currently **fails** at the Click layer
  (missing required argument `ACTIVITY` and required option `--start`), so there
  is no interactive path today.
- The actual work is delegated `cli.py:37` → `TimeTracker.add_entry`
  (`core/facade.py:187`) → `EntryManager.add` (`core/entries.py:135`), which
  already parses start/end/duration and validates `end > start`.

### Findings / edge cases to handle ("debug")
1. `activity` and `--start` must become **optional** so the command can run
   with zero args and fall into easy mode. Must keep backward compatibility:
   `track add "X" --start ...` still works non-interactively.
2. Need a clean rule for when easy mode triggers: enter interactive mode when
   `--start` is NOT supplied (with or without an activity argument). If
   `activity` is already given, skip the activity prompt.
3. Within easy mode, prompt for start time, then ask the user to choose
   **end time** vs **duration** (mirror the mutual-exclusion rule in
   `EntryManager.add`). Re-prompt on invalid input rather than failing silently.
4. Reuse the existing `EntryManager.add` / `TimeTracker.add_entry` for the final
   save — do not duplicate parsing/validation logic.
5. Optional nicety: offer the last logged activity as the default for the
   activity prompt (via `EntryManager.get_last_activity`).
6. Docs/tests: update `README.md` (add a new "Easy Mode" subsection under the
   `add` command) and `TEST_SPECIFICATION.md` (1.1 add-mode / 2.3 new helper).

### Plan / implementation steps
1. **`timetrack/cli.py`** — make `activity` optional (`required=False`) and
   `--start` optional (`required=False`). At the top of `add()`, detect easy
   mode: `if not start_str:` → run a new helper `run_easy_mode(activity)`.
2. **`timetrack/cli.py`** — add `run_easy_mode(initial_activity=None)` that uses
   `click.prompt` to collect: activity (default = last activity if available),
   start time, then a choice of end/duration, then calls `tracker.add_entry(...)`.
   Loop on validation errors returned by `add_entry`.
3. **`core/facade.py` / `core/entries.py`** — no signature changes needed;
   easy mode reuses `add_entry`. (Optionally expose `get_last_activity` already
   present in `EntryManager`.)
4. **Tests** — add to `tests/test_managers.py` or a new `test_easy_mode.py`:
   simulate prompts with `click.testing.CliRunner` + `input=`; assert a log
   entry is created and invalid input is re-prompted. Use `temp_data_dir`
   fixture (never real `~/.timetrack`).
5. **Docs** — update `README.md` and `TEST_SPECIFICATION.md` for the easy-mode
   flow and its outputs.
6. **Verify** — `pytest` and a manual `track add` (no args) smoke test.

### Files touched
- `timetrack/cli.py` (modify `add`, add `run_easy_mode`)
- `tests/` (add easy-mode tests)
- `README.md`, `TEST_SPECIFICATION.md` (docs)

## 2. Improve the update tracking feature
Improve the update tracking feature.

### Status
**⏭️ Skipped for now** — reason: requirement is too vague. "Improve the update
tracking feature" doesn't specify what to improve (self-update flow in
`updater.py`? version tracking? update-available notifications?). Revisit once
the desired behavior is clarified.

## 3. Fix memo display truncation
Fix the memo display so longer text isn't cut off.

### Status
**✅ Done** — implemented, tested (unit + manual CLI), docs updated.

### Root cause
`MemoManager.list_all` (`core/memos.py`) truncated the Note to 45 chars via
`truncate_text(memo.text, 45)`, adding "...". Since Note is the **last** column,
truncation served no alignment purpose and hid content.

### Fix (confirmed approach with user: wrap under Note column)
- Replaced truncation with `textwrap.wrap(text, width=45)`; the first wrapped
  line prints on the ID/Created row, and continuation lines are indented 27
  chars (`MEMO_NOTE_INDENT`) to align under the Note column. Full text is always
  shown.
- `truncate_text` is still used by `remove()` (short confirmation string), so
  the import stays.

### Verification
- Added `tests/test_managers.py::TestMemoManager::test_list_long_memo_not_truncated`
  and `test_list_long_memo_wraps_and_aligns`. All memo tests pass (8).
- Manual CLI smoke (isolated HOME): long memo wraps across aligned lines, no
  ellipsis.
- Full suite: 146 passed, 4 pre-existing `test_facade.py` date-parsing failures
  (unrelated). Pre-existing ruff warnings (unused imports) remain in
  `test_managers.py` — not introduced here; `memos.py` passes ruff clean.

### Files touched
- `timetrack/core/memos.py` (wrap instead of truncate)
- `tests/test_managers.py` (2 new tests)
- `README.md`, `TEST_SPECIFICATION.md` (docs)

## 4. Log durations in hours / clearer units
Display log durations in hours instead of minutes (or make the unit clearer).

### Status
**✅ Done** — implemented, tested (unit + manual CLI), docs updated.

### Problem
`track log` showed each entry's Duration as raw minutes (`{n} min`, e.g.
"90 min"), and several task messages said "{n} minutes", while the log total
already used the clearer "Xh Ym" form — inconsistent and hard to read for long
durations.

### Fix (scope confirmed with user: log column + task messages)
- Added `utils.format_minutes(minutes: int)` → wraps `format_duration` so int
  minutes render as "1h 30m" / "45m" / "0m".
- `entries.py`: per-entry Duration column and the daily total now use
  `format_minutes` (removed the ad-hoc "X minutes" branch).
- `tasks.py`: stop/pause/resume messages and status output (Active/Paused Task)
  now use `format_minutes` instead of "{n} minutes".

### Verification
- New unit tests: `test_utils.py::TestFormatMinutes` (4) and
  `test_managers.py::test_get_log_durations_use_hour_format` (asserts no raw
  " min", presence of "1h 0m"/"30m"). All pass.
- Manual CLI (isolated HOME): log shows "1h 30m"/"20m", total "1h 50m"; status
  "0m so far"; stop "Logged 0m."
- Full suite: 146 passed + 4 pre-existing `test_facade.py` date-parse failures
  (unrelated).

### Files touched
- `timetrack/core/utils.py` (add `format_minutes`)
- `timetrack/core/entries.py`, `timetrack/core/tasks.py` (use it)
- `tests/test_utils.py`, `tests/test_managers.py` (tests)
- `README.md`, `TEST_SPECIFICATION.md` (docs)

## 5. Command to track emails
Add a command to track emails.

### Status
**⏭️ Skipped** — reason: requirement is too vague (original author unsure of
intent). Unclear whether it means a shortcut to start/log time on an "Email"
activity vs. counting emails processed. Revisit when the desired behavior is
defined.

## 6. Command to track sync operations
Add a command to track sync operations.

### Status
**⏭️ Skipped** — reason: too vague (same ambiguity as item 5). Revisit when the
desired behavior is defined.

## 7. Consider SQLite instead of JSON storage
Consider using SQLite instead of JSON for storage.

### Status
**💬 Discussion / decision recorded** — no migration now (per user: open for
discussion, not to be migrated asap).

### Current design
- 4 JSON files (`state.json`, `timelog.json`, `config.json`, `memos.json`).
- Every op does a full read → mutate → full rewrite; `write_log` re-sorts and
  rewrites the whole log on each append (`storage.py:124`).
- Writes use `Path.write_text` (`storage.py:73,125,153,181`) — **not atomic**;
  a crash mid-write can corrupt a file.
- Day filters and reports load everything and filter in Python.

### Scale reality
Personal time tracker: ~thousands of entries/year (~a few MB at 10k entries).
O(n) rewrite cost is negligible at this scale.

### SQLite pros
- Atomic/durable transactions + crash safety.
- O(1) appends (no full rewrite/re-sort).
- Indexed date/activity queries.
- Real concurrency handling (JSON has no locking; two `track` processes can
  clobber each other).
- `sqlite3` is stdlib — no new dependency.

### SQLite cons
- Rewrite `Storage` + JSON→SQLite migration + large test-surface updates.
- Lose human-readable / git-diffable / hand-editable data (a real convenience
  here).
- Ongoing schema-migration concerns.
- Overkill for current scale.

### Decision
1. **Do not migrate now** — scale doesn't justify it; readable JSON is a feature.
2. **Cheap high-value fix regardless:** make JSON writes atomic (temp file +
   `os.replace`) to remove the current corruption risk. (Proposed as a separate
   small item — not yet done.)
3. **Revisit SQLite if/when:** multi-device sync, very large datasets, concurrent
   access, or richer querying/reporting appear. `Storage` is already documented
   as a swappable backend, so a future `SQLiteStorage` behind a small interface
   (keeping JSON import/export) is the clean path.

## 7a. Atomic JSON writes (spun off from item 7)
Make all JSON persistence crash-safe.

### Status
**✅ Done** — implemented, tested, docs updated.

### Problem
Every `write_*` in `storage.py` used `Path.write_text`, which truncates the
target then streams new content. A crash/power-loss/full-disk mid-write could
corrupt or empty the file — and the file is fully rewritten on every
add/stop/edit.

### Fix
- Added `_atomic_write(path, data)` in `storage.py`: writes to a temp file in the
  same dir (`tempfile.mkstemp`), `flush()` + `os.fsync`, then `os.replace()` onto
  the target (atomic on POSIX & Windows). Cleans up the temp file and re-raises
  on failure, leaving the original intact.
- Routed `write_state`, `write_log`, `write_config`, `write_memos` through it.

### Verification
- `tests/test_storage.py::TestAtomicWrite` (5): exact content, overwrite, no
  temp-file leftovers, original preserved when `os.replace` fails, and Storage
  writes leave no `.tmp` files. All pass.
- Full suite: 156 passed + 4 pre-existing `test_facade.py` date-parse failures.

### Files touched
- `timetrack/core/storage.py`, `tests/test_storage.py`, `TEST_SPECIFICATION.md`

## 8. Add a pause reason
Add a pause reason when pausing tracking.

### Status
**✅ Done** — implemented, tested (unit + manual CLI), docs updated.

### Scope (confirmed with user)
Ephemeral + optional: `track pause [REASON]` saves an optional reason on the
paused state and shows it in `track status`; cleared on resume. Not written to
the final log entry. Reason is never mandatory.

### Implementation
- `models.py`: added `ApplicationState.pause_reason: Optional[str] = None`
  (backward compatible — old state files default to None).
- `tasks.py`: `pause(reason=None)` stores the trimmed reason (blank → None) and
  appends " Reason: {reason}" to the pause message; `resume()` clears it;
  `status()` appends " - Reason: {reason}" to the paused line when set.
- `facade.py`: `pause(reason=None)` passes it through.
- `cli.py`: `pause` gains an optional positional `REASON` argument.

### Verification
- New tests in `test_managers.py`: pause with/without/blank reason, resume clears
  reason, status shows reason (5). All pass.
- Manual CLI (isolated HOME): reason shows in pause message and status, absent
  when omitted, cleared after resume.
- Full suite: 161 passed + 4 pre-existing `test_facade.py` date-parse failures.

### Files touched
- `timetrack/models.py`, `timetrack/core/tasks.py`, `timetrack/core/facade.py`,
  `timetrack/cli.py`, `tests/test_managers.py`, `README.md`,
  `TEST_SPECIFICATION.md`

## 9. "Memo Expert" feature
Add a "Memo Expert" feature.

### Status
**✅ Done** — interpreted as **"Memo Export"** (user confirmed the title was a
typo). Implemented, tested, docs updated.

### Implementation
- `reports.py`: added `export_memos(file_format)` mirroring `export_log` — reads
  memos, builds a pandas DataFrame (columns `text`, `created_at`), writes
  `exports/timetrack_memos_{timestamp}.{csv|xlsx}`. Returns "No memos to export."
  when empty and "Unsupported format" for bad formats.
- `facade.py`: added `export_memos(file_format)` delegating to ReportManager.
- `cli.py`: `track memo` gains `-e/--export` (Choice csv|xlsx). Mode precedence:
  export > remove > add > list.

### Verification
- New tests in `test_managers.py`: export empty, csv, xlsx, invalid format (4);
  csv/xlsx tests clean up the generated file. All pass.
- Manual CLI (isolated HOME): csv/xlsx export succeed with correct content;
  empty reports the error; invalid format rejected by Click's Choice.
- Full suite: 165 passed + 4 pre-existing `test_facade.py` date-parse failures.

### Files touched
- `timetrack/core/reports.py`, `timetrack/core/facade.py`, `timetrack/cli.py`,
  `tests/test_managers.py`, `README.md`, `TEST_SPECIFICATION.md`

## 10. Start tracking with a specified start time
Allow tracking to start with a specified start time.

---

_Added: 2026-07-11 — source: pasted backlog list._
