# PHASE 04 REPORT — BACKUP, RESTORE & DATABASE RELOCATION

| Field | Value |
| --- | --- |
| Phase | 04 — Backup, restore, and scheduled runner |
| Completion date | 2026-11-16 |
| Status | Implementation and automated verification complete in this environment; manual Windows integration drill not executed |

## 1. Implementation summary

Phase 4 builds on the Phase 1–3 foundation (PySide6 shell, injected SQLite/SQLAlchemy/Alembic database lifecycle, verified data root/config, and startup recovery) without redesigning the application. The implementation adds:

- SQLite Online Backup API snapshots for automatic, manual, and safety backups with independent verification, SHA-256 checksums, and JSON sidecar metadata published atomically after success.
- Cross-process operation locking for backup, restore, relocation, and upgrade, with stale-lock recovery only when the owning process is proven inactive.
- Backup history/state handling that tolerates missing files and malformed metadata without treating them as verified restore candidates.
- Manual backup and data-protection UI (native PySide6 backup view, schedule/settings dialog, restore confirmation dialog) with background execution for long operations.
- Headless backup runner (`python -m app.tools.backup`, stable exit codes) and Windows Task Scheduler integration (create/update/query/remove with post-action verification, no silent success on rejection).
- Startup catch-up evaluation/execution for missed automatic backups that avoids duplicate successful same-day backups and respects lock contention.
- Managed retention for automatic backups with protection for manual/safety backups and verified-backup preservation rules.
- Staged restore workflow with eligibility re-verification, verified safety backup, runtime shutdown/reopen, atomic replacement, rollback, and recovery-required blocking if rollback cannot guarantee a usable database.
- Verified database relocation using SQLite Online Backup API, destination validation (reusing Phase 3 location validation), atomic config update, and preservation of the old database/config/data root on failure.
- Pre-upgrade safety-backup gate for maintenance-driven schema changes (`UpgradeService` / migration tool path). Normal application startup still never migrates automatically.

No seeders or sample business data were run or created. Existing configuration/database paths are not silently changed; relocation updates config only after destination verification.

## 2. Files created

- `app/domain/backup.py`
- `app/infrastructure/backup/__init__.py`
- `app/infrastructure/backup/directories.py`
- `app/infrastructure/backup/hashing.py`
- `app/infrastructure/backup/history.py`
- `app/infrastructure/backup/lock.py`
- `app/infrastructure/backup/markers.py`
- `app/infrastructure/backup/metadata.py`
- `app/infrastructure/backup/naming.py`
- `app/infrastructure/backup/retention.py`
- `app/infrastructure/backup/snapshot.py`
- `app/infrastructure/backup/state.py`
- `app/infrastructure/backup/task_scheduler.py`
- `app/services/backup_service.py`
- `app/services/backup_workspace.py`
- `app/services/catch_up_service.py`
- `app/services/database_runtime.py`
- `app/services/relocation_service.py`
- `app/services/restore_service.py`
- `app/services/retention_service.py`
- `app/services/schedule_service.py`
- `app/services/upgrade_service.py`
- `app/tools/backup.py`
- `app/ui/dialogs/backup_settings_dialog.py`
- `app/ui/dialogs/restore_confirmation_dialog.py`
- `app/ui/formatting.py`
- `app/ui/viewmodels/backup_viewmodel.py`
- `app/ui/viewmodels/task_runner.py`
- `app/ui/views/backup_view.py`
- `tests/backup_helpers.py`
- `tests/test_backup_catch_up.py`
- `tests/test_backup_domain.py`
- `tests/test_backup_infrastructure.py`
- `tests/test_backup_runner.py`
- `tests/test_backup_scheduler.py`
- `tests/test_backup_service.py`
- `Reports/PHASE_04_REPORT.md`

Untracked prompt/artifact files present in the workspace were not modified or removed by this phase work: `Prompt/PHASE 04 — BACKUP, RESTORE & DATABASE RELOCATION.md`, `opencode.json`.

## 3. Files modified

- `README.md`
- `app/app_context.py`
- `app/core/config.py`
- `app/core/constants.py`
- `app/core/exceptions.py`
- `app/infrastructure/database/migrations.py`
- `app/main.py`
- `app/services/startup_service.py`
- `app/tools/migrate.py`
- `app/ui/main_window.py`
- `docs/ARCHITECTURE.md`
- `docs/BACKUP_STRATEGY.md`
- `docs/DEVELOPMENT_ROADMAP.md`
- `docs/SECURITY_AND_DATA_PROTECTION.md`
- `tests/test_backup_infrastructure.py` (Ruff E501 line-length fix only)
- `tests/test_backup_scheduler.py` (Ruff E501 line-length fix only)

## 4. Dependencies added and reasons

No new third-party runtime dependencies were added in this phase. The implementation uses the existing Python/stdlib stack (`sqlite3` Online Backup API, `hashlib`, `json`, `subprocess`/`schtasks.exe`, filesystem APIs), existing project libraries (SQLAlchemy/Alembic, PySide6), and existing dev tools (pytest, Ruff).

## 5. Backup architecture

- **Domain** (`app/domain/backup.py`): backup types/status/records, catch-up decision rules, retention selection rules, and time parsing/sorting helpers (pure, no I/O/Qt).
- **Application/services** (`app/services/backup_service.py`, `backup_workspace.py`, `retention_service.py`, `catch_up_service.py`, `schedule_service.py`, `restore_service.py`, `relocation_service.py`, `upgrade_service.py`, `database_runtime.py`): use cases and orchestration, fail-closed behavior, lock-aware operations, and runtime reopen/shutdown coordination.
- **Infrastructure** (`app/infrastructure/backup/*`): managed directories, naming/paths, SQLite snapshot and verification, hashing, metadata read/write, history scan, durable state/markers, cross-process lock, retention executor, and Windows Task Scheduler adapter.
- **Presentation** (`app/ui/views/backup_view.py`, `app/ui/viewmodels/backup_viewmodel.py`, `app/ui/dialogs/*`, `app/ui/viewmodels/task_runner.py`): native PySide6 UI and background task execution; no SQLite backup logic embedded in widgets.

## 6. SQLite Online Backup API implementation

- Backups are created via `sqlite3.Connection.backup(...)` into a temporary file in the destination backup directory (never by copying a live database file). WAL content is included by the snapshot.
- Source is validated before snapshot; destination is independently reopened and verified after snapshot.
- Verification includes `quick_check`, `integrity_check`, `foreign_key_check`, application identity, and schema revision checks (implementation in `app/infrastructure/backup/snapshot.py` and service orchestration in `app/services/backup_service.py`).
- The published backup path and metadata are created only after verification and checksum calculation succeed; temporary files from failed attempts are cleaned up and not presented as successful backups.

## 7. Backup metadata and integrity verification

- Each published backup has a JSON sidecar metadata file (atomic write). Metadata includes file/type, timestamps, app version, application identity, schema revision, source and backup sizes, SHA-256 checksum, verification/integrity/foreign-key/operation results, and trigger/duration context.
- Metadata is validated before it is trusted (`app/infrastructure/backup/metadata.py`). Backups with missing/invalid metadata or failed verification are not treated as verified restore candidates.
- History (`app/infrastructure/backup/history.py`) surfaces file-existence and metadata trust state (including missing/malformed/unverified cases) for the UI.

## 8. Locking and concurrency behavior

- `app/infrastructure/backup/lock.py` implements an exclusive cross-process lock file in the managed backup area containing owner diagnostics (PID, process name, operation, timestamps/token context as implemented).
- Backup, restore, relocation, and upgrade flows acquire the same protection; callers that already hold the lock use explicit assume-locked paths only in controlled service-internal cases.
- Stale-lock recovery is never based on age alone; reclaim requires proof that the recorded owner process is not active (Windows-aware liveness checks). Unreadable/corrupt lock states fail closed rather than breaking exclusivity.
- Automated tests cover contention and stale-lock recovery scenarios.

## 9. Manual backup UI

- `BackupView` / `BackupViewModel` provide manual backup creation, current database location/status, last backup/verification information, backup history, progress, success/failure feedback, refresh, open-backup-folder, schedule settings, relocation, and restore actions for eligible backups.
- Long-running operations run via the shared background task runner (`task_runner.py`), keeping the UI responsive.
- Restore requires explicit confirmation (`RestoreConfirmationDialog`) and operates only on verified/eligible backups re-checked by the service before replacement.

## 10. Task Scheduler integration

- `app/infrastructure/backup/task_scheduler.py` integrates with Windows Task Scheduler via `schtasks.exe` using generated XML task definitions (no stored password, InteractiveToken/LeastPrivilege model as implemented).
- Registration/update/removal are verified by querying task state after the operation; failures are reported (no silent "enabled" on rejection). Duplicate/stale task handling uses the stable application-specific task identity.
- `ScheduleService` validates and persists settings atomically in config, synchronizes the scheduler, and avoids claiming success if registration/save cannot be completed consistently.

## 11. Automatic backup and catch-up behavior

- Default schedule is daily at 22:00 local time (configurable enable/time/retention in settings). The headless runner can execute while the GUI is closed.
- Runner loads existing config, resolves the configured database, acquires the operation lock, performs/records a verified backup, applies retention after success, and exits with stable codes (`0` success, `1` failure, `2` config, `3` locked).
- Packaged execution path is supported via `--run-backup` dispatch in `app/main.py` to `app.tools.backup`.
- Startup catch-up (`CatchUpService`) evaluates due/missed state using local schedule, durable state/history, and guards to prevent duplicate successful backups for the same scheduled context; lock contention is handled safely and can be retried later.

## 12. Retention rules

- `RetentionService` / retention executor apply configured retention to managed automatic backups under the operation lock.
- Manual and safety backups are not treated the same as automatic backups for deletion; verified/newest/last-safe protections and managed-directory constraints prevent unsafe deletion.
- Retention failures/errors do not invalidate an already published verified backup. Behavior is covered by automated retention/domain/infrastructure tests.

## 13. Restore workflow

- `RestoreService.prepare` re-verifies the selected managed backup: file existence, managed-path/name checks, metadata validity/match, checksum, size consistency, full integrity/foreign-key/identity checks, and supported schema revision.
- Restore acquires the global lock, verifies the current database, creates and verifies a Safety backup, closes active runtime connections/engine, stages the selected backup, prepares rollback, replaces the live database safely, reopens and verifies, and reports success only after verification.
- Replacement/post-restore failures trigger rollback using the prepared copy and preserve safety backups/diagnostics.

## 14. Rollback behavior

- Failed restore attempts attempt rollback to the previous usable database and verify it before clearing the recovery path.
- If rollback cannot guarantee a safe database, recovery-required markers/state block normal startup rather than silently opening a damaged or partially restored database.
- Relocation failures preserve the old database and old configuration; only operation-created temporary/empty artifacts are cleaned where safe.

## 15. Relocation workflow

- `RelocationService` validates the destination using the existing Phase 3 location validator and rejects unsafe/invalid targets (including existing destination database conflicts and current-location reuse as implemented).
- Under lock: create/verify Safety backup, prepare destination layout additively, create destination database via SQLite Online Backup API, verify identity/schema/integrity/foreign keys/checksum/writability, update `AppConfig.data_root`/`database_path` atomically, re-read config, reopen and health-check the new location.
- On failure: preserve old database/config, keep useful safety backup, and avoid automatic deletion of the old data root.

## 16. Pre-upgrade safety gate

- `UpgradeService` requires a verified current database, acquires the global operation lock, creates and independently verifies a Safety backup, and only then applies Alembic upgrade/downgrade (maintenance path).
- If verification/backup fails, the schema change does not run.
- Normal application startup remains non-migrating and continues to refuse unsafe schema states; no speculative schema/business-table changes were introduced.

## 17. Automated tests executed

Commands executed from repository root (`D:\Development\Gobindas Graphics`):

```powershell
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m pytest -q
```

Automated Phase 4-related test modules present/executed in the suite include:

- `tests/test_backup_domain.py`
- `tests/test_backup_infrastructure.py`
- `tests/test_backup_service.py`
- `tests/test_backup_runner.py`
- `tests/test_backup_scheduler.py`
- `tests/test_backup_catch_up.py`

(Full suite also includes existing Phase 1–3 tests; no Phase 1–3 tests were removed or weakened.)

## 18. Exact test results

- `ruff check app tests` (initial): **failed** with 2 `E501` line-too-long errors in `tests/test_backup_infrastructure.py:343` and `tests/test_backup_scheduler.py:71`.
- Fix applied: formatting-only line wraps in those two tests (no behavior changes).
- `ruff check app tests` (after fix): **`All checks passed!`** (exit code 0).
- `pytest -q`: **`428 passed in 19.95s`** (exit code 0).

## 19. Ruff and other quality-check results

- Ruff: **pass** (`All checks passed!`).
- `scripts/check.ps1` exists; it runs `python -m ruff check app tests` and `python -m pytest`. The equivalent commands were executed directly in this session with the results above.
- No other project quality-check commands were identified beyond Ruff and pytest in the inspected scripts/config.

## 20. Actual Windows integration tests performed

No real/manual Windows integration tests were executed in this session. The following were **not executed** and must not be treated as passed based on mocks:

- Manual GUI backup/restore/relocation flows and UI responsiveness on a real Windows desktop session.
- Real Windows Task Scheduler registration/update/removal verification through the application's UI/workflow on this machine.
- Runner execution with the main application closed via an actual scheduled task trigger.
- End-to-end restore/restart behavior and missing-drive recovery in a live Windows session.
- Manual drill per `docs/BACKUP_STRATEGY.md` §12.2.

Automated scheduler tests in the suite use mocked runner/scheduler interactions as appropriate.

## 21. Known limitations

- Manual Windows integration drill and real Task Scheduler end-to-end execution were not performed in this session; release confidence for those flows requires recorded manual verification.
- Startup recovery dialog does not expose a direct "Restore from backup" action; restore is performed from the Backup view for verified managed backups. Recovery-required/incomplete-operation states block unsafe startup and direct the user to recovery using safety backups.
- `keep_minimum` retention count is governed by internal defaults/constants rather than a user-facing configuration field; schedule UI exposes enable/time/retention-days.
- Backup filenames/metadata naming follow the implemented `BusinessManagement_..._<TYPE>.db` / `.meta.json` convention, which differs from earlier illustrative `BMS_*` examples in draft documentation.
- No separate PyInstaller backup-runner spec was added; packaged scheduled execution relies on the main executable `--run-backup` dispatch.
- `opencode.json` is present as an untracked workspace file and was not modified or committed.

## 22. Outstanding issues

- No failing automated tests or Ruff checks remain.
- Manual Windows integration verification is outstanding and should be completed/recorded before relying on scheduler/restore/relocation as release-drilled behavior.
- Documentation outside the files updated in this phase may still contain historical Phase 4 "pending" language; core Phase 4 docs (README, roadmap, backup strategy, architecture, security) were updated for accuracy.

## 23. Deviations from approved documentation

- Backup filename pattern implemented as `BusinessManagement_YYYY-MM-DD_HH-MM-SS_TYPE.db` with collision suffixes (not the `BMS_<mode>_...` example). Metadata sidecar naming follows `<backup>.meta.json`.
- Configurable persisted backup settings are `backup_enabled`, `backup_time`, and `backup_retention_days`; durable last-success/attempt/failure information is kept in managed backup state/markers rather than config fields.
- Some draft-planned artifact names/paths and UI affordances (e.g. dedicated `%LOCALAPPDATA%...\backup.log` / `backup_last_error.json`, general manual-backup deletion from history, separate backup runner spec) are not implemented exactly as illustrated; actual behavior is documented above.
- Restore is fully implemented as a service/UI workflow but not surfaced as a one-click action in the startup recovery dialog.

## 24. Phase 5 readiness assessment

**Ready for owner review and explicit authorization of Phase 5**, with the following caveats:

- Automated protection logic, service workflows, runner, scheduler integration code, and full pytest/Ruff verification are in place.
- Manual Windows integration tests (real Task Scheduler run while GUI closed, GUI restore/relocation/missing-drive recovery, and §12.2 drill) must be executed and recorded to fully satisfy operational confidence for those Windows-specific flows.
- Phase 5 UI work must preserve the established data-protection invariants: no live DB file copies, no silent fallbacks/path changes, verified backups before schema changes, staged/locked restore and relocation, and no automatic startup migrations.

**STOP after Phase 4.** No Phase 5 work was started.
