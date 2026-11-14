# BACKUP_STRATEGY — Gobindas Graphics Business Management System

| Field | Value |
| --- | --- |
| Document | BACKUP_STRATEGY.md |
| Version | 1.2 |
| Date | 2026-11-14 |
| Status | Draft for review — backup not implemented; Phase 3 data-root setup is complete |
| Priority | Core product feature |
| Related | BLUEPRINT.md, ARCHITECTURE.md, DATABASE_SCHEMA.md, SECURITY_AND_DATA_PROTECTION.md |

## 1. Principles

1. **The database is the business.** Backup is a first-class workflow, not a utility hidden in a menu.
2. **Never copy a live SQLite file.** Use the Online Backup API so WAL content is included and the snapshot is consistent.
3. **Verify before trusting.** A backup is not "done" until it opens, passes integrity checks, and its hash is recorded.
4. **Never overwrite.** Every backup gets a unique, descriptive filename.
5. **Never silently fall back.** If the configured database or backup location is unavailable, the app says so and stops.
6. **Restore is guarded.** It validates first, creates a safety backup, stages the restore, and keeps a rollback copy.
7. **The scheduler is best-effort.** A missed scheduled run is caught up at next startup; the UI must never pretend a backup happened.
8. **Local is not off-site.** The UI and documentation must state the limits clearly.

## 2. Folder layout

The user chooses a **business data root**, for example `D:\GobindasBusiness`:

```text
D:\GobindasBusiness\
├── Database\
│   ├── BusinessManagement.db
│   ├── BusinessManagement.db-wal        (while running)
│   ├── BusinessManagement.db-shm        (while running)
│   └── rollback\                         (temporary pre-restore copies)
├── Backups\
│   ├── Automatic\
│   │   ├── BMS_auto_2026-11-12_220003.db
│   │   └── BMS_auto_2026-11-12_220003.db.meta.json
│   ├── Manual\
│   │   ├── BMS_manual_2026-11-12_153012.db
│   │   └── BMS_manual_2026-11-12_153012.db.meta.json
│   ├── Safety\
│   │   └── BMS_pre_restore_2026-11-12_160000.db
│   └── .backup.lock
├── Attachments\
└── Exports\
    ├── PDF\
    └── Excel\
```

Rules:

- The database location is independent of the installation directory.
- The data root may be on D:, E:, or another local drive; a network share is not supported for live use.
- The configuration file lives **outside** this tree in `%APPDATA%\GobindasBMS\config.json`.
- Backups are stored on the same drive by default. The UI recommends a second destination on a different physical device.
- `-wal` and `-shm` are live runtime sidecars, not backup files. They may disappear
  after a clean checkpoint; a valid backup must be produced through the Online
  Backup API while the database is open.

## 3. Configuration

### 3.1 Application config (outside the data folder)

`%APPDATA%\GobindasBMS\config.json` — atomic writes, schema version, no secrets:

```json
{
  "schema_version": 1,
  "currency_code": "INR",
  "currency_symbol": "₹",
  "currency_decimal_places": 2,
  "currency_grouping": "indian",
  "theme": "system",
  "log_level": "INFO",
  "data_root": "D:\\GobindasBusiness",
  "database_path": "D:\\GobindasBusiness\\Database\\BusinessManagement.db"
}
```

- Paths are absolute and validated on load.
- `database_path` must reside under `data_root`; if not, the config is invalid.
- A legacy config that stores only `database_path` remains loadable and uses no
  `data_root`.
- A corrupt config is moved to `config.corrupt-<timestamp>.json` and the recovery
  flow starts; business data is never touched.
- Secrets (passwords, encryption keys) must never be stored in this file.
- Phase 3 writes `data_root` and `database_path` atomically after the database is
  created and verified. The config schema version remains `1` because
  `data_root` is an optional backward-compatible field.
- `backup.*` and `last_schema_revision` remain Phase 4 fields and are not written
  yet. Future backup settings must extend this same file, not a competing one.

### 3.2 Backup metadata sidecar

Each backup has `<backup>.meta.json`, written after verification:

```json
{
  "meta_version": 1,
  "file_name": "BMS_auto_2026-11-12_220003.db",
  "mode": "automatic",
  "created_at_utc": "2026-11-12T16:00:03Z",
  "app_version": "1.0.0",
  "schema_revision": "0007_sales",
  "source_database_bytes": 48234496,
  "backup_bytes": 48234496,
  "sha256": "…64 hex characters…",
  "integrity_check": "ok",
  "foreign_key_check": "ok",
  "duration_ms": 1830,
  "windows_user": "Ram",
  "app_instance_id": "…",
  "trigger": "scheduled"
}
```

- The sidecar is advisory; a backup is still usable if the sidecar is missing, but the UI marks it "unverified metadata".
- `backup_runs` in the database mirrors history for the UI; the sidecars remain authoritative if the database is lost.

## 4. Backup file naming

```text
BMS_<mode>_<YYYY-MM-DD>_<HHMMSS>.db
mode: auto | manual | pre_restore | pre_migration
```

- Local time is used in the filename for human recognition; the sidecar stores UTC.
- If a filename collision occurs (two backups in the same second), append `_2`, `_3`, never overwrite.
- No spaces; ASCII only; sortable by name within a mode.

## 5. Backup process (authoritative)

Used by manual backups and the scheduled runner.

### 5.1 Preflight

1. Verify the source database file exists and is readable.
2. Verify the destination folder exists, is writable, and is on an accessible drive.
3. Check free space: require at least `source_size × 1.2 + 50 MB`; warn if below `source_size × 2`.
4. Check the database is not zero bytes and has a valid SQLite header.
5. Acquire the backup lock (`Backups\.backup.lock`); if held, exit with "already running" (not an error).

### 5.2 Create the temporary snapshot

6. Open the source with `sqlite3` in read-only mode (`file:...?mode=ro`).
7. Open a destination file in the **same folder as the final backup** with a `.tmp` suffix.
8. Run `source.backup(destination, pages=256, progress=...)` (Online Backup API). This is consistent even while the app is running.
9. Close the destination; `fsync` the file and its directory where supported.
10. Reopen the temporary file read-only and run:
    - `PRAGMA quick_check` and `PRAGMA integrity_check` (must return `ok`);
    - `PRAGMA foreign_key_check` (must return no rows);
    - read `alembic_version`, `PRAGMA application_id`, `PRAGMA user_version`;
    - confirm `business_profile` exists and is readable (when the schema is old, skip gracefully);
    - compare `page_count`/size > 0.
11. Compute SHA-256 of the temporary file.
12. Compare the backup's schema revision with the source; a backup may be older than the app but never newer than the app understands (a newer backup is still stored; restore will refuse it).

### 5.3 Publish

13. Rename `.tmp` → final unique filename using an exclusive operation (fail rather than overwrite).
14. `fsync` the directory so the rename is durable.
15. Write the `.meta.json` sidecar atomically (temp + replace).
16. Record success in `backup_runs` (best effort; if the database is unavailable, skip).
17. Delete the temporary file on any failure.
18. On failure, write a diagnostic entry and a failure marker (see §9).

### 5.4 Duration and I/O

- Backups run in a background worker in the GUI and as a headless process for scheduled runs.
- The GUI shows progress (bytes copied) and does not block navigation.
- Backups are serialized by the lock; two backups never run at once.
- A long backup does not hold a write transaction in the GUI; the Online Backup API uses a read transaction internally.

### 5.5 Manual backup

- The user starts it from the Backup screen or `Ctrl+B`; the app suggests `Backups\Manual\` but allows choosing another local folder (including a different drive).
- An external destination is validated with the same preflight rules (exists, writable, free space, not a UNC live path). The backup is created on the destination volume so the final rename is atomic.
- The mode is `manual`, files are never overwritten, and manual backups are never auto-deleted by retention.
- The UI reports progress, then shows the filename, size, duration, and verification result with an **Open folder** action.
- If the destination is unavailable or fails verification, the backup is not published and the user can retry with another folder.
- A manual backup is recommended (and prompted) before restore, relocation, migration, or a bulk import, even though the app also creates its own safety copy.

## 6. Automatic daily backup

### 6.1 Requirements (confirmed)

- Default time 22:00; user-configurable.
- Runs with the main application closed.
- Missed backups are detected at startup and caught up.
- Overlapping jobs are prevented.
- Failures are reported clearly.

### 6.2 Windows Task Scheduler integration

- Task name: `GobindasBMS\DailyBackup` (folder + task).
- Action: `"<InstallDir>\GobindasBMS-Backup.exe" --scheduled --config "<%APPDATA%\GobindasBMS\config.json>"`.
- Trigger: daily at the configured time.
- Principal: the current Windows user, `InteractiveToken` (no stored password), `LeastPrivilege`.
- Settings: `StartWhenAvailable=true`, `MultipleInstancesPolicy=IgnoreNew`, `ExecutionTimeLimit=PT1H`, `DisallowStartIfOnBatteries=false`, `StopIfGoingOnBatteries=false`.
- The task is created/updated **by the application** after the user enables automatic backups, using an exported XML imported with `schtasks /Create /XML`. This gives control over the settings above.
- The app verifies the task exists and matches the configured time; if not, it shows a warning with a **Repair schedule** action.

Illustrative XML core (final XML is versioned with the app):

```xml
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-11-12T22:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>C:\Program Files\GobindasBMS\GobindasBMS-Backup.exe</Command>
      <Arguments>--scheduled --config "%APPDATA%\GobindasBMS\config.json"</Arguments>
    </Exec>
  </Actions>
</Task>
```

The executable path above is illustrative; the app substitutes its actual install path when generating the XML (per-user installs use `%LOCALAPPDATA%\Programs\...`).

### 6.3 Known limitation

A per-user task with `InteractiveToken` runs only when that user is logged on. If the PC is off or the user is logged out at 22:00, the task does not run at that moment. Windows may run it when the user next logs on if `StartWhenAvailable` is honored, but this is not guaranteed for all configurations.

**Mitigation:** on every application start, the app computes whether an automatic backup is due (see §6.4) and runs a catch-up backup in the background. This is the supported fallback if Task Scheduler cannot be used at all (e.g., policy restrictions). The Settings screen states the limitation in plain language.

A Windows service or stored-password task is deliberately not used: it adds privilege, credential, and deployment complexity that is not justified for a single-user desktop app.

### 6.4 Catch-up logic

At startup, after the database is open and the window is visible:

```text
last_success = latest successful automatic backup timestamp
due_time     = today at configured time
if backup.enabled is false: skip
if last_success is none:
    schedule a catch-up after a short idle delay (e.g., 60 s)
else if now >= due_time and last_success < due_time:
    schedule a catch-up
else if now - last_success >= 36 hours:
    schedule a catch-up (covers clock changes and missed days)
```

- Catch-up runs once per app session; failures do not retry in a loop.
- If a backup is currently running (lock held), skip and let it finish.
- If the database is in a read-only state or a migration is pending, do not start catch-up until the app is healthy.
- If the last success is older than 7 days, show a prominent warning on the dashboard and in the status bar.

### 6.5 Overlap prevention

- Exclusive lock file `Backups\.backup.lock` created with `O_CREAT | O_EXCL`.
- Lock content: PID, process name, start time UTC, mode.
- A stale lock (process not alive or older than 6 hours) may be reclaimed with a log entry.
- Task Scheduler's `IgnoreNew` and the lock are independent safeguards.
- Restore takes the same lock; it refuses to run while a backup is active.

## 7. Retention

Defaults: **30 days**, keep at least **5** automatic backups. Manual and safety backups are never auto-deleted unless the user explicitly chooses cleanup.

Algorithm (automatic backups only):

```text
candidates = automatic backups sorted by created_at ascending
protected  = newest valid backup
keep_set   = backups newer than (now - retention_days)
keep_set  |= newest N backups (keep_minimum)
for each candidate not in keep_set:
    re-check it is not the only valid backup and not the newest valid
    delete sidecar first, then backup file
    record deletion in the log and backup history
```

Rules:

- Never delete a backup unless at least one **verified** newer backup exists.
- If verification is unavailable during cleanup, keep the file.
- Deletion failures are logged and non-fatal.
- Retention never applies to `Manual\` or `Safety\`.
- The UI shows current usage and offers "Clean up old automatic backups" with a preview.
- A retention change never deletes immediately; the next scheduled/cleanup run applies it.

### 7.1 Backup history

The Backup screen lists, newest first: mode (automatic/manual/safety), created time, size, duration, verification result, destination, and schema revision. Filters cover mode and date. Actions: open folder, verify again, restore (with preflight), and delete (manual/safety only, with typed confirmation). Automatic entries are read-only. Missing files are shown as "unavailable" rather than silently disappearing. History is read from `backup_runs` when the database is healthy and reconciled with sidecar files at startup; if the database is lost, the UI can browse a backup folder directly.

## 8. Restore workflow

Restore is the highest-risk operation. It must be explicit, verified, and recoverable.

### 8.1 State machine

```text
IDLE
  → PREFLIGHT (select file, validate, confirm)
  → SAFETY_BACKUP (mandatory; abort on failure)
  → CLOSE_CONNECTIONS (stop workers, dispose engine, checkpoint)
  → STAGE (copy to Database\restore_staging.db, fsync, verify)
  → SWAP (move live aside, remove stale -wal/-shm, atomic replace)
  → VERIFY (open, integrity_check, foreign_key_check, revision check)
  → RESTART (relaunch app)
  → SUCCESS
Any failure after SAFETY_BACKUP → ROLLBACK → report; original DB restored if needed.
```

### 8.2 Preflight

1. The user selects a backup from history or browses to a file.
2. Validate: file exists, non-zero, SQLite header, readable; run `quick_check`/`integrity_check` and `foreign_key_check` on a **copy or read-only connection**, never the live DB.
3. Verify the sidecar hash if present; a mismatch is a hard warning requiring explicit confirmation.
4. Check schema revision: if newer than the app supports, refuse and tell the user to update the app.
5. Verify it is a GGBMS database (`application_id`/expected tables) and show business name/date so the user can confirm the right file.
6. Explain exactly what will happen and require confirmation.
7. Check free space on the database volume: require at least `selected_backup_size × 2 + 100 MB` to hold the staged copy, the rollback copy, and the safety backup's temporary file.

### 8.3 Safety backup

- Create a verified backup of the current database in `Backups\Safety\` with mode `pre_restore`.
- If the safety backup fails, **abort**. Never restore without a rollback copy.
- If the current DB is unreadable, the user may still restore, but the UI must state that the pre-restore state cannot be backed up and require an explicit typed confirmation.

### 8.4 Close, stage, swap

1. Stop background workers; ask the user to close open editors; block navigation.
2. Dispose the SQLAlchemy engine and all connections.
3. Run `PRAGMA wal_checkpoint(TRUNCATE)` if possible.
4. Copy the selected backup to `Database\restore_staging.db` on the same volume as the live DB.
5. `fsync`, then verify the staged copy again (hash + `integrity_check`).
6. Rename the live DB to `Database\rollback\BusinessManagement_<timestamp>.db` (same volume).
7. Delete stale `BusinessManagement.db-wal` and `BusinessManagement.db-shm` **only after all connections are closed and the live file is moved aside**.
8. `os.replace(staging, live)` (atomic on the same volume).
9. `fsync` the directory.

### 8.5 Verification and reopen

- Open the restored DB (new engine), run `integrity_check`, `foreign_key_check`, and read the Alembic revision.
- If the revision is older than the app head, do **not** migrate during restore; report that the app will migrate on next start after a new safety backup.
- If verification fails: restore the rollback copy, delete the bad live file, clear WAL/SHM, report failure, keep both files for diagnosis.
- On success: relaunch the application (ADR-014). The restarted app opens the restored DB and shows a success notice with the backup timestamp.
- Keep the rollback copy until a successful startup has been observed; then retain for 7 days or until the next manual cleanup.

### 8.6 What restore must never do

- Restore over a live open database.
- Delete the only copy of the current data.
- Silently migrate a restored older schema in the same operation.
- Restore a file from an unknown source without a warning.
- Claim success before the reopened DB passes checks.

## 9. Failure handling

| Failure | Detection | Behaviour |
| --- | --- | --- |
| Destination drive missing | path checks / `OSError` | Fail with "drive unavailable"; no fallback location |
| Disk full | `OSError`, free-space preflight | Abort before rename; delete `.tmp`; show free-space requirement |
| Permission denied | `OSError` | Abort; suggest a folder the user owns or run installer per-user |
| Database locked | `sqlite3.OperationalError` | Retry once with a short delay; if still locked, fail with "close other copies" |
| Backup file corrupt | `integrity_check` ≠ ok | Delete `.tmp`; never publish; log checksum/context |
| Interrupted backup | orphan `.tmp` | Clean stale `.tmp` files older than 24 h at next run; never treat as backup |
| Overlapping run | lock exists | Secondary run exits cleanly; not an error |
| Task Scheduler rejected | `schtasks` exit code | Keep automatic backup disabled; show fallback notice; use startup catch-up |
| Clock change / DST | scheduler/date logic | Catch-up uses elapsed time with a 36 h guard; no duplicate same-day backups |
| Restore interrupted | startup sees staging/rollback files | Detect and offer recovery; never auto-complete a partial restore |
| Source DB missing at restore | path check | Offer "Locate database"; do not create a new one |
| Backup on removable drive removed | path check | Keep history in DB; mark file unavailable; offer locate |
| App closed during restore | startup marker | On next start, detect `restore_in_progress` marker and complete/rollback before opening the UI |

Diagnostic artifacts:

- `%LOCALAPPDATA%\GobindasBMS\logs\backup.log` — runner log, rotated.
- `%LOCALAPPDATA%\GobindasBMS\backup_last_error.json` — last runner failure (timestamp, code, message, path), read by the GUI at startup and then acknowledged.
- `backup_runs` table — durable history while the DB is healthy.
- An in-progress marker file in the data root for restore crash recovery.

## 10. Database relocation

Changing the database location uses backup/restore mechanics, not a file move.

1. Validate the new folder: writable, local drive, enough free space (≥ 2× DB), not the installation directory, not a UNC path.
2. Create the new folder structure there.
3. Take a verified backup directly into the new location's `Backups\Manual\` (Online Backup API).
4. Verify the new copy (`integrity_check`, `foreign_key_check`, revision, business identity).
5. Optionally open the new copy read-only and verify row counts for key tables.
6. Write a relocation marker, update config atomically, and restart the app.
7. Keep the old database and folders intact until the user confirms the new location works; provide a "Remove old copy" action with typed confirmation (Phase 2+).
8. If any step fails, the config remains unchanged and the app keeps using the old location.

The old location must never be deleted automatically.

## 11. Missing-drive behaviour

When the configured data root is unavailable:

1. Do not create directories or a new database elsewhere.
2. Show a blocking dialog containing:
   - the configured database path and data root;
   - the specific reason (drive letter absent, folder missing, permission denied, database file missing, identity mismatch, unsupported revision);
   - **Retry**;
   - **Locate existing data** (browse; validate identity and revision before accepting);
   - **Start a new setup** (explicit new location);
   - **Exit**.
3. Log the event with the correlation ID.
4. If the drive reappears while the dialog is open, Retry succeeds and startup continues.
5. If the user selects a different drive/database, validate `application_id` and schema revision; never attach a mismatched business database silently.
6. The application does not open the main window until the database is verified.
7. **Restore from backup** is intentionally absent until Phase 4 can verify and
   stage a restore safely. It must not be faked in the recovery dialog.

The Phase 3 implementation of this flow is recorded in ARCHITECTURE.md §18.8.

## 12. Verification and drills

### 12.1 Automated tests

- Unit: filename generation, retention selection, lock handling, catch-up decision logic, metadata serialization.
- Integration: backup a temp DB → verify hash/size/integrity → restore into a new location → compare table counts and checksums of key tables.
- Fault injection: destination read-only, disk full (mock), corrupt temp file, interrupted rename, stale WAL, missing sidecar, newer schema revision.
- Concurrency: run two backup processes; assert one succeeds and one exits cleanly; GUI + runner overlap.
- Migration: backup before upgrade, upgrade temp DB, restore backup, verify pre-upgrade revision.

### 12.2 Manual drill (required before release)

1. Create a database with representative data.
2. Run a manual backup; verify history and sidecar.
3. Modify data; restore the backup; confirm the old state and the safety backup.
4. Kill the runner mid-backup (Task Manager); verify no corrupt `.db` is published and the next run succeeds.
5. Disconnect/remove the data drive; verify the blocking error and no fallback.
6. Restore a backup from a read-only folder (copy first) and from a path with spaces.
7. Verify Task Scheduler runs with the app closed and the user logged on.
8. Verify catch-up after a simulated missed backup.
9. Measure duration for a 500 MB database; record the result.

## 13. Security limitations (must be communicated)

- A backup on the same disk does not survive disk failure, theft, fire, ransomware, or accidental deletion of the folder.
- A different drive letter may be the same physical disk. The UI must not imply safety just because the path is `D:`.
- SQLite files are **not encrypted** by default. Anyone with file access can read them.
- Backups contain the same business data and inherit folder permissions.
- Recommended: BitLocker on the data drive, NTFS permissions limited to the Windows user, and a periodic copy to a separate physical device kept offline.
- Encryption at rest is an open requirement (Q-18); if added, it must cover both database and backups and must have a documented key-recovery process.
- Avoid syncing a live SQLite database through OneDrive/Dropbox while the app is running; sync only verified backups, and only when the app is closed.

## 14. Recovery objectives

| Metric | Target |
| --- | --- |
| RPO (automatic) | ≤ 24 hours |
| RPO (with manual pre-close backup) | as low as the last manual backup |
| RTO (verified local restore) | ≤ 15 minutes |
| Backup verification | 100% of created backups before publish |
| Retention | 30 days automatic, minimum 5, manual kept |

## 15. Acceptance criteria

- [ ] A scheduled backup runs with the main application closed while the user is logged on.
- [ ] A missed backup is detected at startup and caught up without blocking the UI.
- [ ] Two backup attempts cannot run concurrently.
- [ ] Every published backup passes `integrity_check` and `foreign_key_check`.
- [ ] No backup file is ever overwritten.
- [ ] Retention never deletes the last or newest valid backup, and never touches manual/safety backups.
- [ ] Restore always creates a verified safety backup first (or requires explicit typed confirmation when impossible).
- [ ] Restore restores WAL content and leaves no stale `-wal`/`-shm` files.
- [ ] A failed restore leaves the original database usable and reports what happened.
- [ ] Missing drive produces a blocking, actionable message and never a silent fallback.
- [ ] Relocation updates config only after destination verification and keeps the old copy.
- [ ] Backup history shows mode, timestamp, size, verification, and destination.
- [ ] The UI states that local backups are not off-site protection.
- [ ] Manual drill in §12.2 has been executed and recorded.

## 16. Open questions

| ID | Question | Impact |
| --- | --- | --- |
| Q-18 | Encryption at rest / encrypted backups? | Backup format, restore, key recovery |
| Q-21 | Off-site/second-device backup requirement? | Extra destination UI, reminders |
| Q-19 | Code signing? | SmartScreen warnings on both exes |
| Q-25 | Should automatic backups also write to a second destination? | Runner logic, failure semantics |
| Q-26 | Should the app warn/exit if no verified backup exists for N days? | UX policy |

## 17. Phase 2 database compatibility (2026-11-13)

Backup and restore are **not implemented** in Phase 2. The foundation was built to
make the approved backup design implementable without rework:

- **Online Backup API ready.** The database is a normal SQLite file opened by
  SQLAlchemy, so a future backup runner can use `sqlite3.Connection.backup()`.
  Runtime code never holds an exclusive lock and sets no
  `PRAGMA locking_mode=EXCLUSIVE`.
- **WAL understood.** WAL is enabled with `synchronous=FULL`. The application
  performs a best-effort passive checkpoint on clean shutdown and then disposes
  the engine. A backup taken from the live file must still use the Online Backup
  API so WAL content is included.
- **Safe shutdown seam.** `AppContext.close()` disposes the engine from the entry
  point's `finally` block. The future restore workflow can reuse this to ensure no
  pooled connection touches a replaced file.
- **Identity check.** `PRAGMA application_id = 1195525971` identifies a Gobindas
  database before a backup or restore is accepted.
- **No automatic migration.** Phase 2 startup refuses a schema that needs an
  upgrade because the pre-upgrade verified safety backup does not exist yet.
  Phase 4 adds that backup gate.
- **No destructive behaviour.** Health checks and startup checks never delete,
  recreate, repair, or relocate a database.

Phase 4 must add: Online Backup API snapshot, verification (`integrity_check`,
hash, open test), sidecar metadata, retention, restore staging, and the
pre-upgrade safety backup.

## 18. Phase 3 setup compatibility (2026-11-14)

Backup and restore are still **not implemented** in Phase 3. The data-root
workflow now creates and owns the folder layout that Phase 4 will use.

### 18.1 Final Phase 3 layout and ownership

The setup wizard creates exactly:

```text
<data_root>/
├── Database/
│   └── BusinessManagement.db
├── Backups/
│   ├── Automatic/
│   ├── Manual/
│   └── Safety/
├── Attachments/
└── Exports/
    ├── PDF/
    └── Excel/
```

- `<data_root>` is chosen explicitly by the owner; it is never derived from the
  working directory, the installation directory, or `C:`.
- `database_path` in the configuration is the absolute path to
  `<data_root>/Database/BusinessManagement.db`.
- `data_root` and `database_path` are owned by the setup wizard and are written
  atomically only after the database passes identity, revision, and health
  checks.
- The configuration file remains outside the data root at
  `%APPDATA%\GobindasBMS\config.json`.
- Existing folders and files are preserved. Setup removes only empty
  directories that it created during a failed attempt.
- The layout directories are created even though backup is not implemented, so
  Phase 4 does not need to migrate or guess paths.

### 18.2 WAL sidecar implications

- The live database uses WAL; `-wal` and `-shm` appear while the application is
  open. They are runtime artifacts, not backups.
- Setup verification checks identity, revision, and health but does not copy the
  database. No file is treated as a backup in Phase 3.
- A future backup must use the SQLite Online Backup API while the database is
  open so WAL content is included.
- Clean shutdown checkpoints WAL best-effort and disposes the engine. The Phase 3
  composition root keeps the same shutdown path.

### 18.3 Future backup runner integration points

Phase 4 can reuse:

- `DataRootLayout` for `backups_dir`, `automatic_backups_dir`,
  `manual_backups_dir`, and `safety_backups_dir`.
- `AppConfig.data_root` and `AppConfig.database_path`, both loaded and validated
  by the existing `ConfigService`.
- The open `Database` lifecycle and verified file for the Online Backup API.
- `StartupService`/`AppContext` for the app-closed and app-open runner cases.
- The location validator for a future destination check, without changing the
  live database path.

Phase 4 must add the backup lock, Online Backup snapshot, verification, sidecar
metadata, retention, restore staging, and the pre-upgrade safety backup. No
Phase 3 code claims those capabilities.
