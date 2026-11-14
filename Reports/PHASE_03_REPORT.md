# PHASE 03 REPORT — Database Location Selection & First-Launch Setup Wizard

## 1. Phase number and title

**Phase 3 — Database Location Selection & First-Launch Setup Wizard**

Gobindas Graphics Business Management System

## 2. Completion date

**2026-11-14**

## 3. Implementation summary

Phase 3 adds the native PySide6 first-launch setup workflow and the safe startup
classification that protects an existing business data location.

Delivered:

- First-launch detection with `SETUP_REQUIRED`, `RECOVERY_REQUIRED`, and `READY`
  startup modes.
- A seven-page native setup wizard: welcome, location, validation, directory
  review, confirmation, initialization progress, and completion.
- Native folder picker with the absolute selected path always visible.
- A read-only location validator covering path syntax, absoluteness, drive
  availability/type, UNC and mapped-network refusal, protected and
  installation-folder refusal, drive-root refusal, read/write probing, free
  space, and existing-database detection.
- Additive creation of `Database`, `Backups/{Automatic,Manual,Safety}`,
  `Attachments`, and `Exports/{PDF,Excel}` with preservation of existing files
  and empty-directory-only cleanup on failure.
- Database creation through the Phase 2 `MigrationManager.create_database()`.
- Safe adoption of an existing healthy database; refusal of unknown, corrupt,
  uninitialized, older, and newer databases without modification.
- Atomic `data_root` and `database_path` persistence through the existing
  `AppConfig`/`ConfigService`, preserving INR and all other settings.
- A blocking recovery dialog with Retry, Locate existing data, Start new setup,
  and Exit. No C: fallback and no replacement database.
- Startup integration and a headless `--smoke-test` path that never opens a
  window.
- Dashboard and status-bar reporting of the verified database location.
- 102 additional tests, for **341 passing tests** total.

No backup, restore, scheduled runner, business table, business profile,
authentication, or business module is implemented.

## 4. Files created

Phase 3 production files:

- `app/infrastructure/filesystem/__init__.py`
- `app/infrastructure/filesystem/drives.py`
- `app/infrastructure/filesystem/layout.py`
- `app/infrastructure/filesystem/scaffold.py`
- `app/infrastructure/filesystem/validation.py`
- `app/services/setup_service.py`
- `app/services/startup_service.py`
- `app/ui/dialogs/setup_wizard.py`
- `app/ui/dialogs/recovery_dialog.py`
- `app/ui/viewmodels/setup_viewmodel.py`

Phase 3 test files:

- `tests/test_setup_layout.py`
- `tests/test_setup_drives.py`
- `tests/test_setup_validation.py`
- `tests/test_setup_scaffold.py`
- `tests/test_setup_service.py`
- `tests/test_setup_viewmodel.py`
- `tests/test_setup_wizard.py`
- `tests/test_startup_service.py`
- `tests/test_recovery_dialog.py`

Report:

- `Reports/PHASE_03_REPORT.md`

`app/services/__init__.py` and `app/infrastructure/filesystem/__init__.py` are
package markers. No new third-party dependency was added.

## 5. Files modified

Phase 3 modifications:

- `README.md` — Phase 3 scope, startup behavior, configuration paths, recovery,
  structure, and next phase.
- `app/app_context.py` — `from_parts()` composition and verified database path.
- `app/core/config.py` — optional `data_root`, cross-field validation,
  `with_database_location()`, `load_with_status()`, quarantine status, atomic
  serialization.
- `app/core/constants.py` — data-root layout names, database filename, minimum
  free space, version `0.2.0`.
- `app/core/exceptions.py` — `SetupError`.
- `app/core/paths.py` — updated location documentation.
- `app/main.py` — setup/recovery/ready startup, smoke behavior, wizard and
  recovery orchestration, verified database hand-off.
- `app/ui/main_window.py` — optional verified database/data root, status-bar
  reporting.
- `app/ui/views/home_view.py` — configured/unconfigured database status.
- `app/ui/themes/qss.py` — setup and recovery dialog styling.
- `docs/ARCHITECTURE.md` — startup lifecycle, setup responsibilities, validation,
  persistence, initialization, recovery, Phase 3 record.
- `docs/BACKUP_STRATEGY.md` — final layout ownership, actual config shape,
  missing-drive behavior, Phase 4 integration points.
- `docs/SECURITY_AND_DATA_PROTECTION.md` — validation policy, UNC policy,
  configuration protection, overwrite prevention, recovery behavior.
- `docs/DATABASE_SCHEMA.md` — unchanged baseline and Phase 3 initialization
  record.
- `docs/DEVELOPMENT_ROADMAP.md` — Phase 3 completion, DoD, and Phase 4
  dependencies.
- `tests/test_architecture.py` — Qt-free service boundary.
- `tests/test_config.py` — data root, legacy config, load status, outside-root
  rejection, INR preservation.
- `tests/test_main_window.py` — configured database reporting.
- `tests/test_startup.py` — Phase 3 subprocess startup/smoke coverage.

Note: the repository baseline commit is Phase 1. Phase 2 work was still
uncommitted when Phase 3 started. The final commit therefore also publishes the
previously completed Phase 2 files and report; Phase 2 work was not modified to
make Phase 3 pass.

## 6. Dependencies added and reasons

**None.**

Phase 3 reuses:

- PySide6 6.12.0 for the native wizard, dialogs, and worker-thread signals.
- SQLAlchemy 2.1.8 and Alembic 1.20.1 through the Phase 2 database layer.
- Python standard-library `pathlib`, `shutil`, `tempfile`, `os`, `ctypes`, and
  `sqlite3`-independent abstractions already present.
- pytest for the test suite.

No backup, encryption, or scheduling dependency was introduced.

## 7. First-launch workflow

1. The composition root configures logging, creates the Qt application, and
   acquires the single-instance guard.
2. `ConfigService.load_with_status()` reports `MISSING`, `LOADED`, or
   `RECOVERED`.
3. `StartupService.assess()` classifies the environment:
   - no saved location → `SETUP_REQUIRED`;
   - corrupt/incomplete configuration, invalid location, missing drive/folder/
     database, permission failure, identity mismatch, or unsupported revision →
     `RECOVERY_REQUIRED`;
   - verified database → `READY`.
4. On first launch the setup wizard opens before any main window.
5. The user chooses an absolute data root, validates it, reviews the folders and
   database file, and explicitly confirms.
6. The wizard creates the folders, creates or safely adopts the database, runs
   full health verification, and atomically saves the location.
7. The completion page opens the application. The same verified `Database`
   instance is handed to `AppContext`; the file is not reopened through a second
   unverified path.
8. Cancelling before initialization exits with no database, no data-root folder,
   and no saved location. The next launch offers setup again.
9. Subsequent launches skip the wizard and run Phase 2 startup verification.
10. A missing drive or damaged configuration opens the blocking recovery dialog
    instead of the wizard or an empty database.

## 8. Folder selection implementation

- `QFileDialog.getExistingDirectory()` provides the native Windows folder picker.
- The selected path is displayed in full in a selectable text field and repeated
  in the confirmation summary.
- The user can browse again, type/paste an absolute path, or go back.
- `DataRootLayout` fixes the database filename as
  `<root>/Database/BusinessManagement.db`.
- The data root is always distinct from the database file and from the
  installation directory.
- No current-working-directory or installation-relative path is ever used.
- The folder is not created until validation passes and the user confirms.

## 9. Drive and folder validation

`DataLocationValidator` returns named checks with pass/info/warning/error status.

Implemented checks:

- non-empty, valid path syntax and absolute path;
- UNC rejection and mapped-network-drive rejection;
- named-directory requirement (drive root alone is refused);
- drive availability;
- drive type: fixed, removable, unknown-with-warning; optical, network, and
  unavailable refused;
- protected Windows/system/program folder refusal;
- installation-directory refusal (executable directory, PyInstaller bundle,
  repository root);
- existing folder must be a readable directory, not a file;
- missing folder allowed only when the nearest existing ancestor is readable and
  writable;
- unique temporary write probe: create, write, flush, close, remove, verify;
- free-space inspection with actual bytes displayed; minimum 1 MiB for initial
  setup, not presented as a database-size forecast;
- path-length warning;
- existing database warning vs. folder-at-database-path error.

A removable drive is accepted with a warning that it must remain connected.
The validator does not assume that a different drive letter is a different
physical disk.

Test doubles cover fixed/removable/unknown/network/optical/unavailable drives,
read-only and unwritable folders, low space, UNC paths, installation paths,
protected folders, and missing parents.

## 10. Directory structure

Setup creates exactly:

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

Creation is additive and sequential. Existing directories are accepted. A file
where a directory is required is a hard error and is never deleted. On failure,
only empty directories created by that attempt are removed, deepest first;
non-empty and pre-existing directories are kept.

## 11. Database initialization process

`SetupService.initialize()`:

1. Revalidates the root and obtains `DataRootLayout`.
2. Scaffolds the approved folders.
3. If `BusinessManagement.db` exists, opens it through the Phase 2 startup
   verification path and adopts it only when identity, revision, and health pass.
4. Otherwise constructs an absolute `DatabaseConfig` and calls
   `MigrationManager.create_database()`.
5. Applies the existing `0001_baseline` revision.
6. Runs `DatabaseDiagnostics.check(full=True)`; requires file, identity,
   revision, quick check, foreign-key check, integrity check, and read/write
   capability.
7. Returns the open `Database`, migration status, health report, and scaffold
   result.

Not used: `Base.metadata.create_all()`, manual Alembic inserts, extra tables,
automatic upgrades, or a second database implementation.

Existing database protection:

- Healthy, recognized, expected-revision database → adopted without changes.
- Unknown `application_id`, corrupt file, uninitialized schema, older schema, or
  newer schema → refused with an explanation.
- Existing file is never overwritten, truncated, repaired, or migrated by setup.

## 12. Configuration persistence

- `AppConfig.data_root` is an optional absolute path.
- `AppConfig.database_path` remains the explicit absolute SQLite path.
- Both paths must resolve consistently: when both exist, the database must be
  inside the data root.
- Legacy configs with only `database_path`, or with `null` fields, remain valid.
- The config file stays outside the data root at
  `%APPDATA%\GobindasBMS\config.json`.
- `ConfigService.save()` validates, writes to a temporary file in the same
  directory, flushes/fsyncs, atomically replaces, and leaves no `.tmp` files.
- Setup re-reads the saved file and compares both paths and all preserved fields
  before reporting success.
- Persistence happens only after database creation and verification.
- If persistence fails, `SetupPersistenceError` carries the still-open verified
  database so the user can retry the save; the database is not deleted.
- A corrupt file is preserved as `config.corrupt-<timestamp>.json` and its
  original bytes are kept.

## 13. Recovery and missing-drive behavior

`RecoveryDialog` reports the specific reason and the saved database path, data
root, and quarantine path where applicable. It offers:

| Action | Result |
| --- | --- |
| **Retry** | Re-runs startup assessment; succeeds if the drive/permission problem is fixed |
| **Locate existing data...** | Native folder picker; validates identity, revision, and health before accepting; never creates a file |
| **Start a new setup...** | Runs the setup wizard for a new location |
| **Exit** | Closes without changing configuration or creating anything |

Guarantees:

- No fallback database is created.
- No saved path is changed silently.
- No empty replacement database is opened.
- The main window is never shown before verification.
- Restore from backup is intentionally absent until Phase 4 can verify and stage
  it safely.

Smoke-test behavior:

- setup required → exit `0` with `Setup required` and no window;
- any recovery condition → exit `1` with the reason logged;
- healthy configured database → shell opens and the smoke test exits cleanly.

## 14. INR configuration preservation

INR remains:

- code `INR`;
- symbol `₹`;
- 2 decimal places;
- Indian digit grouping.

The setup updates only `data_root` and `database_path`. It builds the saved
configuration from the existing `AppConfig`, so currency, theme, logging, and
schema version are preserved. Tests explicitly assert after successful setup:

```text
saved.currency_code == "INR"
saved.currency_symbol == "₹"
saved.currency_decimal_places == 2
```

`with_database_location()` also preserves theme and log level. The Phase 2
`Money` integer-paise implementation was not changed. No `float` was introduced.

## 15. Tests executed

Commands:

```powershell
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pytest --collect-only -q
```

Phase 3 test areas:

- first launch, setup-required, cancel, and healthy reopen;
- wizard navigation, validation gating, review, confirmation, progress, failure,
  and completion hand-off;
- fixed/removable/invalid/relative/missing-parent/non-directory/read-only/
  unwritable/UNC/installation/protected/drive-root locations;
- free-space reporting and low-space failure;
- exact directory set, existing folders/files, partial failure, safe cleanup;
- database initialization, baseline revision, identity, health, existing healthy
  adoption, unknown/corrupt/uninitialized/newer refusal, no overwrite;
- config absolute paths, data root, legacy config, null fields, outside-root
  rejection, atomic writes, re-read verification, corrupt recovery, persistence
  failure recovery, INR preservation;
- startup modes, missing drive, no fallback, smoke behavior;
- recovery dialog choices and no filesystem side effects;
- Phase 1 and Phase 2 regressions;
- import boundaries: services and filesystem infrastructure are Qt-free.

## 16. Actual test results

```text
ruff check app tests
All checks passed!

pytest
341 passed in 15.60s

pytest --collect-only -q
341 tests collected in 0.17s
```

Phase 3 test file counts:

| Test file | Tests |
| --- | ---: |
| `test_setup_layout.py` | 6 |
| `test_setup_drives.py` | 6 |
| `test_setup_validation.py` | 23 |
| `test_setup_scaffold.py` | 7 |
| `test_setup_service.py` | 11 |
| `test_setup_viewmodel.py` | 6 |
| `test_setup_wizard.py` | 7 |
| `test_startup_service.py` | 13 |
| `test_recovery_dialog.py` | 7 |

Additional coverage was added to `test_config.py` (+10), `test_startup.py`
(Phase 3 rewrite), `test_main_window.py` (+1), and `test_architecture.py` (+1),
for 102 additional tests over the 239 Phase 2 tests.

## 17. Application startup verification

### 17.1 Migration and integrity CLI

Command:

```powershell
python -m app.tools.migrate --database "<temp>\GGBMS\db\BusinessManagement.db" init
python -m app.tools.migrate --database "<temp>\GGBMS\db\BusinessManagement.db" status
python -m app.tools.migrate --database "<temp>\GGBMS\db\BusinessManagement.db" history
python -m app.tools.migrate --database "<temp>\GGBMS\db\BusinessManagement.db" check --full
```

Actual result:

```text
state:   up_to_date
current: 0001_baseline
head:    0001_baseline
0001_baseline (down: base) - Baseline schema identity.
status:  healthy
message: The database is healthy.
  file: exists
  connection: ok
  foreign_keys: ok
  application_id: ok
  quick_check: ok
  foreign_key_check: ok
  integrity_check: ok
  read_write: ok
  migration: up_to_date
  size: 12288 bytes
  schema revision: 0001_baseline
```

### 17.2 Isolated smoke matrix

Each scenario used fresh `APPDATA`/`LOCALAPPDATA` folders and a unique mutex:

| Scenario | Exit | Database files created | Log evidence |
| --- | ---: | --- | --- |
| Clean profile | 0 | none | `Setup required` |
| Healthy configured database | 0 | existing verified file only | `Database ready`, `Main window shown` |
| Corrupt configuration | 1 | none | `recovery required`; corrupt file preserved |
| Newer schema | 1 | existing file only | `newer than this application understands` |
| Uninitialized database | 1 | existing file only | `must be migrated` |
| Missing drive | 1 | none | `recovery required`, drive not available |

No scenario created a fallback database. A source search for hard-coded `C:\`
paths returned no matches, and `AppConfig.database_path` still defaults to `None`.

### 17.3 Existing database protection

Tests verify that a healthy baseline database is adopted without modification,
and that unknown, corrupt, uninitialized, older, and newer databases are refused
without changing file bytes or revision. No test or startup path overwrites an
existing database.

## 18. Known limitations

- Backup, restore, retention, scheduled backup, and relocation are not
  implemented (Phase 4).
- Automatic migration/upgrade is still refused; Phase 4 must add the verified
  safety-backup gate.
- Business profile fields/tables are not approved and are not implemented.
- Live OneDrive/Dropbox/Google Drive folders are not automatically detected;
  the documentation and setup copy warn against live sync. Automatic detection
  is a later hardening item.
- The recovery dialog has no restore action until Phase 4 can verify and stage a
  restore.
- SQLite files remain unencrypted; BitLocker/Windows account security are the
  primary controls (Q-18).
- The `Backups` directories exist but are empty and do not constitute a backup.

## 19. Outstanding issues

No blocker remains for Phase 3.

Open decisions carried forward:

- business-profile field list and approval (later phase);
- encryption at rest (Q-18);
- sync-client detection/warning hardening;
- backup destination/off-site policy (Q-21/Q-25), owned by Phase 4;
- code signing (Q-19), packaging phase.

## 20. Deviations from approved documentation

1. **Restore-existing-backup branch deferred.** The roadmap listed a possible
   Phase 3 placeholder. The Phase 3 prompt explicitly forbids faking restore and
   assigns restore to Phase 4. No restore UI or claim was added.
2. **Business-profile setup deferred.** The roadmap listed minimum confirmed
   fields, but no field list is approved. No speculative fields or table were
   created.
3. **Configuration schema version stays `1`.** `data_root` was added as an
   optional backward-compatible field, with legacy configs still valid, rather
   than incrementing the schema version for a non-breaking addition.
4. **Wizard implementation shape.** The wizard is a custom `QDialog` with
   `QStackedWidget` and a `QThread` worker rather than `QWizard` or
   `QThreadPool`. This matches the native multi-page requirement and keeps long
   initialization off the GUI thread.
5. **Minimum free space is 1 MiB.** It is a documented safety minimum for the
   empty baseline, not a capacity forecast; actual free space is displayed.

All other behavior follows ARCHITECTURE.md, BACKUP_STRATEGY.md,
SECURITY_AND_DATA_PROTECTION.md, DATABASE_SCHEMA.md, and DEVELOPMENT_ROADMAP.md.

## 21. Phase 4 readiness assessment

Phase 4 can proceed after owner review and explicit authorization.

Ready:

- Verified data root and exact `Backups/{Automatic,Manual,Safety}` layout.
- Explicit absolute `data_root` and `database_path` in the existing config.
- Open/verified `Database` lifecycle and clean shutdown.
- Startup classification and blocking recovery flow that never falls back.
- Existing location validator for a destination preflight.
- No fake restore, no hidden path change, and no implicit database creation.

Phase 4 must add:

- SQLite Online Backup API snapshot and verification;
- sidecar metadata, hash, history, and retention;
- manual backup UI and history;
- backup lock and stale-lock recovery;
- scheduled runner and Task Scheduler integration;
- startup catch-up and failure markers;
- restore staging, safety backup, replacement, verification, and rollback;
- pre-upgrade safety backup gate;
- database relocation workflow;
- fault-injection tests and the manual drill.

**Phase 3 is complete. Stop here until the Phase 3 report is reviewed and
Phase 4 is explicitly authorized.**
