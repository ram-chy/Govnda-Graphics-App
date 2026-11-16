# PHASE 04 — BACKUP, RESTORE & DATABASE RELOCATION

## Project

Gobindas Graphics Business Management System

## Objective

Implement a reliable, production-oriented backup and recovery system for the
existing standalone Windows application.

The application currently uses:

- Python
- PySide6 / Qt Widgets
- SQLite
- SQLAlchemy 2
- Alembic
- Existing Phase 1–3 architecture and services

Phase 4 must build on the existing implementation. Do not redesign the
application or introduce another database architecture.

**Work carefully. Data safety is more important than implementation speed.**

---

# 1. Mandatory instructions

Before changing anything:

1. Read the following project documentation:
   - `docs/BLUEPRINT.md`
   - `docs/ARCHITECTURE.md`
   - `docs/DATABASE_SCHEMA.md`
   - `docs/BACKUP_STRATEGY.md`
   - `docs/SECURITY_AND_DATA_PROTECTION.md`
   - `docs/DEVELOPMENT_ROADMAP.md`
   - `README.md`
2. Read `Reports/PHASE_01_REPORT.md`, `Reports/PHASE_02_REPORT.md`, and
   `Reports/PHASE_03_REPORT.md`.
3. Inspect the existing database, configuration, startup, migration, filesystem,
   and application-shutdown implementations.
4. Inspect the existing tests and understand the current database lifecycle.
5. Inspect Git status, branches, and recent commit history before editing.
6. Preserve all existing work, including uncommitted changes.
7. Do not commit, amend, reset, rebase, or push Git changes.
8. Do not run seeders or create sample business data.
9. Do not delete existing files or database contents.
10. Do not silently change existing configuration or database paths.

If the existing implementation differs from the documentation, investigate and
document the difference before making architectural changes.

Use official documentation when necessary to verify Python, SQLite, Windows Task
Scheduler, PySide6, and PyInstaller behavior.

Do not assume a feature works merely because its code exists. Test it.

---

# 2. Phase 4 scope

Implement these capabilities:

1. SQLite-safe database backup.
2. Backup verification and metadata.
3. Backup history.
4. Manual backup from the application.
5. Automatic scheduled backup.
6. Windows Task Scheduler integration.
7. Startup catch-up for missed backups.
8. Backup retention.
9. Safe restore workflow.
10. Safety backup before restoration.
11. Restore verification and rollback.
12. Database relocation to another approved local drive or folder.
13. Pre-upgrade safety-backup gate.
14. Recovery-dialog integration where appropriate.

Do not implement business modules, accounting, sales, purchases, inventory,
customer management, or speculative business-profile functionality.

---

# 3. SQLite backup engine

## 3.1 Required backup method

Use SQLite's Online Backup API.

Use the existing SQLite/Python database infrastructure wherever possible.

Never implement a live database backup using ordinary file copying.

The implementation must correctly handle SQLite WAL mode and active database
connections.

Requirements:

- Obtain a consistent database snapshot.
- Handle active application connections safely.
- Handle WAL transactions correctly.
- Avoid corrupt or incomplete backups.
- Close temporary connections reliably.
- Use explicit transaction and connection lifecycle management.
- Avoid blocking the GUI during long operations.
- Report progress and meaningful errors.

Use the Python SQLite backup interface or an equivalent verified implementation.

Do not replace the existing SQLAlchemy database layer.

## 3.2 Backup types

Support three backup types:

| Type      | Directory            |
| --------- | -------------------- |
| Automatic | `Backups/Automatic/` |
| Manual    | `Backups/Manual/`    |
| Safety    | `Backups/Safety/`    |

Use unique, sortable filenames.

Suggested format:

`BusinessManagement_YYYY-MM-DD_HH-MM-SS_TYPE.db`

Do not overwrite an existing backup.

If a filename collision occurs, generate a unique alternative.

## 3.3 Backup completion requirements

A backup must not be marked successful until all required verification passes.

The backup process should:

1. Acquire a backup-operation lock.
2. Validate the source database and configured location.
3. Create a temporary backup file in the destination directory.
4. Use SQLite Online Backup API to generate the snapshot.
5. Close the destination connection.
6. Verify the resulting database.
7. Run SQLite integrity checks.
8. Run foreign-key checks.
9. Verify the application identity.
10. Verify the expected schema revision.
11. Calculate SHA-256.
12. Generate metadata.
13. Atomically publish the completed backup.
14. Release the lock.

Temporary or incomplete files must never appear as successful backups.

If any step fails:

- Mark the operation failed.
- Preserve useful diagnostics.
- Clean up only temporary files created by that operation.
- Do not damage the source database.
- Do not report success.

## 3.4 Backup metadata

Every completed backup must have a corresponding metadata file.

Use JSON unless the existing architecture provides a better documented solution.

Include:

- Backup filename.
- Backup type.
- Creation timestamp.
- Application version.
- Database application identity.
- Schema revision.
- Source database path.
- Source database size.
- Backup file size.
- SHA-256 checksum.
- Verification result.
- SQLite integrity-check result.
- Foreign-key-check result.
- Backup operation result.

Never store passwords, credentials, or unnecessary sensitive information in
backup metadata.

Metadata must be validated before it is trusted.

A backup without valid metadata or verification must not be treated as a
verified restore candidate.

## 3.5 Backup history

Provide backup history without introducing unnecessary business tables.

Use metadata files or an appropriate infrastructure-level history mechanism.

Display:

- Backup date and time.
- Backup type.
- Filename.
- File size.
- Verification status.
- Schema revision.
- Result.

History must handle missing files, malformed metadata, and interrupted
operations safely.

Do not assume that a metadata record proves the backup file still exists or
remains valid.

---

# 4. Backup locking and concurrency

Implement a cross-process backup-operation lock.

The lock must prevent conflicting backup, restore, relocation, and upgrade
operations.

Requirements:

- Prevent two simultaneous backup operations.
- Prevent backup from conflicting with restore or relocation.
- Prevent restore or relocation while another protected operation is running.
- Handle process crashes.
- Detect stale locks safely.
- Never automatically remove a lock merely because it is old.
- Verify whether the owning process is still active before recovering a stale
  lock.
- Record enough information to diagnose abandoned operations.

Test concurrency and stale-lock recovery.

Do not rely only on an in-memory Python boolean or Qt application state.

---

# 5. Manual backup UI

Add a native PySide6 backup-management screen or dialog using the existing UI
architecture.

Provide:

- Create Manual Backup action.
- Current database location.
- Last successful backup.
- Backup history.
- Backup verification status.
- Backup progress.
- Success and failure feedback.
- Refresh history.
- Open backup folder.
- Restore action for eligible verified backups.

Use background workers for operations that may take time.

The UI must remain responsive.

Do not expose destructive operations as one-click actions.

Require explicit confirmation before restoring a backup.

Follow the existing green-based Light Mode and professional Dark Mode design.

Keep the interface clean and consistent with the existing application.

---

# 6. Automatic scheduled backup

## 6.1 Default schedule

Default automatic backup time:

**Every day at 10:00 PM local Windows time.**

Allow the user to configure:

- Enable/disable automatic backups.
- Backup time.
- Retention period.
- Last successful backup.
- Last attempted backup.
- Last failure information.

Default retention:

**30 days.**

Do not assume the application will remain open at 10 PM.

## 6.2 Windows Task Scheduler

Implement a lightweight backup runner that can operate independently of the main
GUI.

Use Windows Task Scheduler to execute the runner daily.

The runner must:

- Load the existing application configuration.
- Locate the configured database.
- Verify that the configured drive is available.
- Acquire the cross-process operation lock.
- Perform the backup.
- Verify the backup.
- Record the outcome.
- Write useful logs.
- Exit with meaningful status codes.

The main GUI must not be required to run the scheduled backup.

Do not create a Windows service unless a documented technical requirement makes
it necessary.

Do not store Windows passwords or credentials in application configuration.

Choose a safe Task Scheduler execution mode and clearly document any Windows
account/session limitations.

## 6.3 Schedule management

Provide safe installation, update, and removal of the scheduled task.

Requirements:

- Use the Windows Task Scheduler interface or supported Windows scheduling
  mechanisms.
- Avoid duplicate scheduled tasks.
- Identify the task using a stable application-specific name.
- Verify that task creation/update actually succeeded.
- Report failure to the user.
- Never silently claim scheduling is enabled if Task Scheduler rejected the
  operation.

The scheduling implementation must work with the packaged application
architecture planned for later PyInstaller distribution.

Do not hardcode a development-only Python executable path into the production
task.

## 6.4 Startup catch-up

When the application starts:

- Check whether an automatic backup was due.
- Check whether a successful backup already exists for the current scheduled
  date.
- If the scheduled backup was missed, attempt a catch-up backup.
- Avoid duplicate backups when the scheduled runner already completed
  successfully.
- Respect the operation lock.
- Do not block the UI while performing catch-up.
- Record failed attempts and allow a later retry.

Define the date/time comparison carefully and use local Windows time
consistently.

---

# 7. Backup retention

Implement configurable retention with a default of 30 days.

Requirements:

1. Inspect backup files and their metadata.
2. Identify eligible expired backups.
3. Never delete incomplete or unrelated user files.
4. Never delete files outside the application's backup directories.
5. Never delete the only remaining verified backup.
6. Never delete a backup currently involved in an operation.
7. Never delete a backup before a newer replacement is fully verified.
8. Preserve safety backups while a protected operation is in progress.
9. Record retention activity in logs.

Treat automatic, manual, and safety backups carefully.

Do not automatically apply the same deletion policy to all three categories
without evaluating the recovery implications.

The user must be able to retain manual backups independently of automatic
retention.

Document the final retention behavior clearly.

---

# 8. Safe restore workflow

Restore is a high-risk operation.

Implement it as a staged, reversible process.

## 8.1 Restore eligibility

Only offer restore for a backup that:

- Exists.
- Has valid metadata.
- Has a matching SHA-256 checksum.
- Passes SQLite integrity verification.
- Passes foreign-key verification.
- Has the expected application identity.
- Has a supported schema revision.
- Is not currently locked by another operation.

Do not restore arbitrary SQLite files.

Do not automatically restore an unsupported database revision.

## 8.2 Restore confirmation

Before restore:

Display:

- Selected backup filename.
- Backup date.
- Backup type.
- Backup size.
- Source schema revision.
- Current database location.
- Warning that current database contents will be replaced.

Require explicit confirmation.

## 8.3 Restore process

Implement this sequence:

1. Acquire the global database-operation lock.
2. Verify the current configured database.
3. Verify the selected backup again.
4. Create a verified safety backup of the current database.
5. Confirm that the safety backup is fully usable.
6. Prevent new application database operations.
7. Close active database sessions and connections cleanly.
8. Stage the selected backup in a temporary location on the same volume as the
   destination database.
9. Verify the staged database and checksum.
10. Prepare a rollback copy or equivalent recoverable replacement strategy.
11. Replace the current database using a safe filesystem operation.
12. Reopen the database through the existing database infrastructure.
13. Run full database health checks.
14. Verify application identity and schema revision.
15. Confirm the application can read and write.
16. Report success only after verification.
17. Release the operation lock.

## 8.4 Restore failure and rollback

If replacement or post-restore verification fails:

- Restore the previous database using the prepared rollback copy.
- Verify the restored previous database.
- Preserve the safety backup.
- Record the failure and rollback result.
- Never leave the application silently using an empty or unverified database.
- Do not delete the selected backup.

If rollback itself fails, block normal startup and show a clear
recovery-required state.

Do not automatically open a damaged or partially restored database.

## 8.5 Application lifecycle

During restore:

- Disable conflicting application actions.
- Close database-dependent windows or prevent new database requests.
- Ensure all SQLAlchemy sessions are closed.
- Dispose the database engine.
- Recreate the database connection after successful replacement.
- Ensure the main application does not retain stale connections.

Test Windows file-locking behavior.

---

# 9. Database relocation

Implement a user-controlled workflow to move the existing database to another
approved data root.

This is not a simple file copy.

Use SQLite Online Backup API to produce a verified destination snapshot.

## 9.1 Relocation workflow

1. Display the current data root and database path.
2. Allow the user to select a new destination folder.
3. Reuse the Phase 3 location validator.
4. Validate destination drive, folder permissions, available space, and path.
5. Warn if the destination is removable.
6. Reject network and UNC paths.
7. Reject the current database folder and unsuitable protected locations.
8. Acquire the global operation lock.
9. Create and verify a safety backup.
10. Create the new destination folder structure additively.
11. Create the destination database using SQLite Online Backup API.
12. Verify destination identity, schema, integrity, foreign keys, checksum, and
    read/write capability.
13. Prepare rollback information.
14. Update `AppConfig.data_root` and `AppConfig.database_path` atomically.
15. Re-read the configuration and verify it.
16. Reopen the application database from the new location.
17. Run full health checks.
18. Report success only after the new location is confirmed operational.

## 9.2 Relocation failure

If any step fails:

- Preserve the old database.
- Preserve the old configuration.
- Do not delete the old data root.
- Remove only newly created empty directories or temporary files belonging to
  the failed operation.
- Keep any useful safety backup.
- Report the failure clearly.

The old database must remain usable until the new location has been fully
verified.

Do not automatically delete the old database after successful relocation.

The user may manually remove the old copy later after verifying the new
location.

---

# 10. Pre-upgrade safety-backup gate

Phase 3 intentionally refuses unsupported or older database revisions.

Phase 4 must introduce a safe foundation for future schema upgrades.

Before any supported schema upgrade:

1. Verify the existing database.
2. Acquire the global operation lock.
3. Create a Safety backup.
4. Verify the Safety backup.
5. Only then allow the upgrade process to proceed.

If the backup fails, the upgrade must not run.

Do not silently enable automatic migrations during normal application startup.

Do not implement speculative schema changes or new business tables in this
phase.

If the existing migration infrastructure cannot safely support this gate without
a larger migration redesign, implement the safe backup prerequisite and document
the remaining limitation rather than bypassing protection.

---

# 11. Configuration and data protection

Preserve the existing configuration structure and backward compatibility.

Do not casually change:

- `data_root`
- `database_path`
- INR currency configuration
- Theme settings
- Logging configuration
- Existing schema/version fields

Add only the settings required for backup scheduling and retention.

Use atomic configuration writes.

Keep configuration outside the business data root.

Never silently switch to another database path.

If the configured drive is missing:

- Do not create another database.
- Do not run a backup against an unintended location.
- Do not change configuration.
- Record the failure.
- Display or log a clear recovery message.

SQLite remains unencrypted by default. Do not claim that backup encryption or
database encryption exists unless it is actually implemented and verified.

Do not upload backups to cloud services or external servers.

Do not assume a different drive letter means a separate physical disk.

---

# 12. Architecture and code quality

Keep the existing modular-monolith architecture.

Separate responsibilities appropriately:

- Domain: backup and operation state/rules where appropriate.
- Application: backup, restore, retention, scheduling, and relocation use cases.
- Infrastructure: SQLite backup API, filesystem, hashing, metadata, locking,
  Task Scheduler, and logs.
- Presentation: PySide6 screens, dialogs, ViewModels, progress and confirmation.

Business logic must remain independent of PySide6.

Avoid putting SQLite backup logic directly inside UI classes.

Use dependency injection or the project's existing composition approach.

Use `Decimal` for financial calculations where relevant. Do not introduce floats
into financial code.

Use type hints and meaningful exception classes.

Do not add unnecessary third-party dependencies.

If a new dependency is genuinely needed, document why and verify compatibility
with the existing Python environment.

---

# 13. Testing requirements

Use temporary directories and temporary SQLite databases.

Never run destructive tests against the user's real business database.

Add comprehensive automated tests.

## 13.1 Backup tests

Test:

- Online Backup API snapshot.
- Active WAL database backup.
- Concurrent database activity.
- Backup integrity.
- Foreign-key verification.
- SHA-256 calculation.
- Metadata creation and validation.
- Filename collision handling.
- Interrupted backup.
- Insufficient disk space.
- Missing destination drive.
- Permission failure.
- Stale temporary files.
- Lock contention.
- Stale-lock recovery.
- No source database modification.

## 13.2 Scheduler tests

Test:

- Task creation.
- Task update.
- Duplicate prevention.
- Task removal.
- Invalid schedule configuration.
- Runner configuration loading.
- Runner exit codes.
- Missing drive.
- Failed backup.
- Missed schedule catch-up.
- Duplicate catch-up prevention.
- Runner execution when the main application is closed.

Mock Windows Task Scheduler interactions where appropriate, but also provide a
manual Windows integration-test procedure.

## 13.3 Retention tests

Test:

- Expired automatic backups.
- Retained manual backups.
- Safety-backup protection.
- Last verified backup protection.
- Invalid metadata.
- Missing backup files.
- Active operation protection.
- Retention failure.
- No deletion outside managed backup directories.

## 13.4 Restore tests

Test:

- Valid restore.
- Invalid checksum.
- Corrupt backup.
- Unsupported schema revision.
- Invalid metadata.
- Active database connections.
- WAL handling.
- Safety backup creation.
- Replacement failure.
- Post-restore integrity failure.
- Successful rollback.
- Failed rollback.
- Configuration preservation.
- Application startup after restore.

## 13.5 Relocation tests

Test:

- Valid destination.
- Existing destination folders.
- Insufficient space.
- Unavailable drive.
- Removable drive warning.
- Network-path rejection.
- Backup failure.
- Destination verification failure.
- Configuration-write failure.
- Successful relocation.
- Old database preservation.
- Rollback after failure.

## 13.6 Regression

Run the complete existing test suite.

Do not reduce or weaken existing Phase 1–3 tests to make Phase 4 pass.

Run Ruff and all applicable project checks.

Perform a real Windows smoke test for:

- Manual backup.
- Scheduled task registration.
- Runner execution.
- Restore.
- Relocation.
- Missing-drive recovery.

If a real Windows integration test cannot be performed in the current
environment, clearly mark it as not executed. Do not claim it passed based only
on mocks.

---

# 14. Documentation updates

Update the existing documentation:

- `docs/ARCHITECTURE.md`
- `docs/BACKUP_STRATEGY.md`
- `docs/SECURITY_AND_DATA_PROTECTION.md`
- `docs/DEVELOPMENT_ROADMAP.md`
- `README.md`

Document:

- Backup lifecycle.
- Metadata format.
- Backup verification.
- Locking strategy.
- Automatic schedule.
- Task Scheduler behavior.
- Retention policy.
- Restore and rollback.
- Relocation.
- Pre-upgrade backup gate.
- Failure and recovery behavior.
- Any remaining limitations.

Do not remove historical Phase 1–3 information.

---

# 15. Mandatory Phase 4 report

Create:

`Reports/PHASE_04_REPORT.md`

The report must include:

1. Phase number and title.
2. Completion date.
3. Implementation summary.
4. Files created.
5. Files modified.
6. Dependencies added and reasons.
7. Backup architecture.
8. SQLite Online Backup API implementation.
9. Backup metadata and integrity verification.
10. Locking and concurrency behavior.
11. Manual backup UI.
12. Task Scheduler integration.
13. Automatic backup and catch-up behavior.
14. Retention rules.
15. Restore workflow.
16. Rollback behavior.
17. Relocation workflow.
18. Pre-upgrade safety gate.
19. Automated tests executed.
20. Exact test results.
21. Ruff and other quality-check results.
22. Actual Windows integration tests performed.
23. Known limitations.
24. Outstanding issues.
25. Deviations from approved documentation.
26. Phase 5 readiness assessment.

Include actual command output or concise factual results where appropriate.

Never invent successful test results.

Clearly distinguish automated tests, mocked tests, and manually executed Windows
tests.

---

# 16. Acceptance criteria

Phase 4 is complete only when:

- Manual backups use SQLite Online Backup API.
- Completed backups are independently verified.
- Metadata and SHA-256 checks are implemented.
- Backup operations are protected by cross-process locking.
- Backup history is available.
- Automatic backup can run while the main GUI is closed.
- Task Scheduler integration is verified.
- Missed backups are handled safely.
- Retention cannot delete the only verified backup.
- Restore creates a verified safety backup first.
- Restore is staged and supports rollback.
- Relocation preserves the old database until the new location is verified.
- Configuration updates are atomic.
- Pre-upgrade operations cannot bypass the safety-backup gate.
- Existing Phase 1–3 behavior remains intact.
- All tests pass.
- Ruff passes.
- Documentation is updated.
- `Reports/PHASE_04_REPORT.md` is complete.

If any critical acceptance criterion cannot be met, do not claim Phase 4 is
complete. Explain the blocker and provide evidence.

---

# 17. Final execution rule

Work methodically.

Do not rush implementation.

Do not expand the scope.

Do not make unapproved business or data-storage decisions.

Do not delete existing user data.

Do not commit or push.

Do not run seeders.

After completing Phase 4:

1. Run all verification commands.
2. Review the final Git diff.
3. Check for accidental changes or generated user data.
4. Save the mandatory report.
5. Summarize implementation and test results.
6. List any outstanding risks or limitations.

**STOP after Phase 4. Wait for the owner's review and explicit authorization
before beginning Phase 5.**
