# Gobindas Graphics Business Management System

A standalone, offline Windows desktop application for small-business management.
Built with Python 3.14, PySide6 (Qt Widgets), and a layered MVVM / application
service architecture.

**Current status: Phase 7B Business Profile correction complete.** The project
contains the technical foundation, the database layer, the first-launch setup
wizard, the backup/restore/scheduled-runner/relocation infrastructure, the
refined native desktop UI, and the corrected business profile with managed logos,
version history, and audit events. No other business modules or sample data exist
yet.

## Implemented scope

Phase 1:

- Reproducible Python virtual environment and pinned dependencies.
- Application package structure for UI, domain, and core services.
- Runnable desktop shell: sidebar navigation, top bar, content area, status bar.
- Light and dark themes with runtime switching and persistence.
- Application configuration stored separately from business data.
- INR currency formatting with Indian digit grouping.
- Rotating file logging, correlation IDs, and a global exception hook.
- Single-instance guard.
- Unit, UI, and startup tests.

Phase 2:

- SQLite database foundation using SQLAlchemy 2 and Alembic.
- Injected absolute database path with no default location and no C: fallback.
- Explicit database creation, startup schema checks, and refusal of newer,
  unknown, older, or uninitialized schemas.
- WAL, foreign-key enforcement, bounded connection pool, and safe shutdown.
- Explicit-commit unit of work and repository foundation.
- Database health diagnostics and integrity checks.
- INR `Money` value object with integer-paise storage rules.
- Headless migration/health CLI.

Phase 3:

- Native PySide6 first-launch setup wizard (welcome, location, validation,
  directory review, confirmation, initialization, completion).
- Native folder picker and a read-only-until-confirmed location validator.
- Fixed, removable, and unknown local drives supported; UNC, mapped network,
  optical, protected Windows, installation-directory, and drive-root locations
  refused.
- Safe additive creation of `Database`, `Backups/{Automatic,Manual,Safety}`,
  `Attachments`, and `Exports/{PDF,Excel}`; existing folders and files preserved.
- Database creation through `MigrationManager.create_database()`, with identity,
  Alembic revision, and full health verification.
- Existing healthy databases are connected without being overwritten; unknown,
  corrupt, uninitialized, or newer databases are refused.
- Atomic `data_root` and `database_path` persistence that preserves INR, theme,
  logging, and other settings.
- Missing-drive, corrupt-config, and incomplete-config recovery dialog with
  Retry / Locate existing data / Start new setup / Exit. No C: fallback and no
  replacement database is ever created implicitly.

Phase 4:

- SQLite Online Backup API snapshots for manual, automatic, and safety backups
  (never ordinary file copies of a live database).
- Independent verification before publish: full integrity/foreign-key checks,
  application identity, schema revision, SHA-256 checksum, and JSON sidecar
  metadata; temporary/incomplete files are never published as successful backups.
- Backup history from managed metadata/files with handling for missing files and
  malformed metadata.
- Cross-process backup-operation lock shared by backup, restore, relocation, and
  upgrade; stale locks are recovered only after the owning process is proven dead.
- Manual backup, history, verification status, progress, and restore UI in the
  native PySide6 backup view.
- Headless `python -m app.tools.backup` runner for scheduled execution, with
  stable exit codes and retention applied after a successful run.
- Windows Task Scheduler registration/update/removal (verified after creation),
  daily 10:00 PM default schedule, configurable enable/time/retention, and
  startup catch-up that avoids duplicate same-day backups.
- Automatic-backup retention with safety/manual protection and protection of the
  newest/last verified backups.
- Staged restore workflow: re-verify candidate, create and verify safety backup,
  acquire lock, close runtime, stage/replace, reopen and verify, with rollback
  and recovery-required blocking on rollback failure.
- Database relocation: validate destination, safety backup, SQLite Online Backup
  API destination snapshot, full verification, atomic config update, reopen; old
  database/config preserved on failure and old data root never deleted.
- Pre-upgrade safety-backup gate in `UpgradeService` and the maintenance CLI;
  normal startup still never migrates automatically.

Phase 5:

- Token-driven light and dark themes with Qt palette synchronisation; every QSS
  length is emitted with an explicit `px` unit.
- Refined shell with accessible status labels, latest verified backup status,
  `F5` refresh, and restored window geometry/state/navigation via `QSettings`.
- Scrollable dashboard and backup views with token spacing and honest empty
  states; no fake business figures, charts, or seed data.
- Reusable `StatusBadge`, `EmptyState`, `Toast`, `DetailCard`, `make_button()`,
  and `set_dialog_size()` components.
- Consistent setup, recovery, restore-confirmation, backup-settings, and fatal
  error dialogs with explicit defaults, tab order, and accessible names.
- Backup UI states for empty, unavailable, busy, verified-only restore, success
  toast, non-modal read warning, and modal decision errors.

Phase 7A and Phase 7B:

- Single per-installation business profile with mandatory business name, address,
  phone, email, footer message, and managed logo.
- Optional secondary phone, website, and registration number.
- Managed logo storage with PNG/JPG/JPEG content validation, 5 MB limit, safe
  `Logos/` references, and failure-safe replacement.
- Immutable profile version history and durable audit events with no ordinary audit UI.
- Settings page with inline validation, logo selection/preview, history viewing,
  empty/status states, and non-modal save feedback.
- Reversible `0002_business_profile` and `0003_business_profile_requirements`
  Alembic migrations; existing profile values are preserved by the Phase 7B backfill.
- Backup sidecars can embed managed logo files; restore and relocation preserve
  `Logos/` and roll back on failure.

Explicitly not implemented (later phases): authentication, tax/business document
details, bank details, general attachments, customers, suppliers, products, sales,
purchases, inventory, accounting, expenses, and reports. No seeders or sample
business data exist.

## Requirements

| Item | Value |
| --- | --- |
| OS | Windows 10 22H2 or Windows 11, 64-bit |
| Python | CPython 3.14.6 (tested; 3.13 is allowed by `pyproject.toml`) |
| Desktop framework | PySide6 6.12.0 |
| Database | SQLite via SQLAlchemy 2.1.8 and Alembic 1.20.1 |

No system-wide Python packages are used. All commands below run from the
repository root `D:\Development\Gobindas Graphics`.

## Environment setup

PowerShell:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

If script execution is blocked for the current session, either run
`Set-ExecutionPolicy -Scope Process Bypass` or call the interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

`requirements.txt` contains the exact runtime versions. `requirements-dev.txt`
adds pytest and ruff. `pyproject.toml` contains compatible version ranges for
the same stack.

## Running the application

```powershell
.\.venv\Scripts\python.exe -m app.main
```

A headless startup self-check (starts the shell, verifies it initialises, then
exits after about one second) is available for verification:

```powershell
.\.venv\Scripts\python.exe -m app.main --smoke-test
```

Normal startup creates only the settings and log folders. On a clean profile it
shows the first-launch setup wizard; cancelling leaves no database and no saved
location. After setup, startup verifies the saved drive, folder, database file,
identity, and Alembic revision before the main window opens. A missing drive or
invalid configuration shows a blocking recovery dialog instead of creating a
fallback database.

### Desktop UI behaviour

- The theme can be switched from the top bar; the choice remains in
  `%APPDATA%\GobindasBMS\config.json`.
- The main window restores its previous size, state, and selected page on the
  next launch. Saved geometry is ignored if it does not fit a connected screen.
- `F5` refreshes the active page when that page exposes a `refresh()` hook.
- Status badges communicate pass, warning, error, and information with text,
  border shape, and accessible names, not color alone.
- Routine successes show a brief toast; a failed backup-history read shows a
  warning in the status area; errors requiring a decision remain modal.
- The backup view enables **Restore selected backup** only for a selected
  verified entry. Manual backup and refresh are disabled while an operation is
  running.
- Qt uses `PassThrough` high-DPI scaling with layout-based resizing; no global
  font or widget scaling multiplier is applied. Offscreen programmatic smoke
  checks ran at scale factors 1, 1.25, and 1.5. Real Windows visual/DPI
  walkthroughs remain outstanding.

## Testing and linting

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check app tests
```

Or run both with the helper script:

```powershell
.\scripts\check.ps1
```

UI tests use Qt's `offscreen` platform plugin, so they run without
opening windows. The startup tests launch the real entry point in a subprocess
with isolated `APPDATA` and `LOCALAPPDATA` folders.

## Database maintenance

The headless tool requires an explicit absolute database path. `init` is the only
command that creates a file, and it refuses to overwrite an existing one.

```powershell
.\.venv\Scripts\python.exe -m app.tools.migrate --database "D:\GGBMS\gobindas.db" init
.\.venv\Scripts\python.exe -m app.tools.migrate --database "D:\GGBMS\gobindas.db" status
.\.venv\Scripts\python.exe -m app.tools.migrate --database "D:\GGBMS\gobindas.db" upgrade
.\.venv\Scripts\python.exe -m app.tools.migrate --database "D:\GGBMS\gobindas.db" history
.\.venv\Scripts\python.exe -m app.tools.migrate --database "D:\GGBMS\gobindas.db" check --full
```

Startup never migrates automatically and never creates a database. A newer,
unknown, older, or uninitialized schema is refused until an explicit maintenance
action is taken. `upgrade`/`downgrade` through the maintenance path run the
Phase 4 pre-upgrade safety-backup gate (verified database, global lock, verified
Safety backup) before any schema change; a backup failure stops the change.

The baseline contains no application tables. The only table is Alembic's
`alembic_version`; file identity is stored in `PRAGMA application_id` and
`PRAGMA user_version`.

## Backups

Manual backups, backup history, schedule settings, restore, and relocation are
available from the Backup view in the application. The headless runner creates
one verified backup of the configured database and is the entry point for
Windows Task Scheduler:

```powershell
.\.venv\Scripts\python.exe -m app.tools.backup
.\.venv\Scripts\python.exe -m app.tools.backup --scheduled
.\.venv\Scripts\python.exe -m app.tools.backup --scheduled --config "%APPDATA%\GobindasBMS\config.json"
```

Stable exit codes: `0` verified backup published, `1` backup failed, `2`
missing/unusable configuration, `3` operation lock held. A frozen build accepts
`--run-backup` so the packaged executable can run the scheduled backup without
the GUI. Backups, restore, relocation, and upgrades refuse to run when the
configured drive is missing or another protected operation holds the lock.

## Configuration and logs

| Item | Location |
| --- | --- |
| Configuration | `%APPDATA%\GobindasBMS\config.json` |
| Logs | `%LOCALAPPDATA%\GobindasBMS\logs\app.log` |
| Business data | Chosen at first launch; `data_root` and `database_path` in `config.json` hold the absolute selected paths |

The configuration file is created by the first-launch setup (or the first
settings change, such as switching the theme). It is written atomically. An
invalid file is preserved as `config.corrupt-<timestamp>.json`; the recovery
dialog then offers Retry, Locate existing data, Start a new setup, or Exit, so a
damaged file cannot destroy the previous content or silently replace the
business location.

Logging rotates at 5 MB with five retained files. Logs contain timestamps,
levels, module names, correlation IDs, and error details. They must not contain
personal or financial payloads.

## Default currency

- Code: **INR**
- Symbol: **₹**
- Decimal places: **2**
- Grouping: **Indian** (`₹1,25,000.50`)

Formatting lives in `app/core/formatting.py` and is separate from calculation
logic. It accepts `Decimal`, `int`, or numeric strings and rejects `float`
values explicitly, so display code cannot introduce binary rounding errors.

```python
from decimal import Decimal
from app.core.formatting import format_money

format_money(Decimal("1250.50"))       # ₹1,250.50
format_money(Decimal("125000.50"))     # ₹1,25,000.50
format_money(Decimal("-1000000"))      # -₹10,00,000.00
```

The active currency is read from `AppConfig.currency`, so changing it later
does not require changing formatting call sites.

> **Confirmed currency decision:** INR is the default currency. The Phase 1
> implementation, `docs/BLUEPRINT.md` (A-05, Q-01), and
> `docs/DATABASE_SCHEMA.md` now agree on INR with 2 decimal places.

## Project structure

```text
app/
├── __init__.py
├── main.py                     # Composition root and entry point
├── app_context.py              # Explicit startup wiring
├── core/
│   ├── config.py               # AppConfig, validation, atomic config service
│   ├── constants.py            # Fixed application constants
│   ├── exceptions.py           # Application exception hierarchy
│   ├── formatting.py           # INR / Indian-grouping display formatting
│   ├── logging_config.py       # Rotating logging and correlation IDs
│   ├── error_handling.py       # Global excepthook
│   ├── paths.py                # %APPDATA% / %LOCALAPPDATA% paths
│   └── single_instance.py      # Named Windows mutex guard
├── domain/
│   ├── backup.py               # Backup/retention/catch-up domain rules
│   └── value_objects/
│       ├── currency.py         # Currency descriptor and INR default
│       └── money.py            # INR value object and integer-paise conversion
├── infrastructure/
│   ├── backup/                 # Snapshot, lock, metadata, history, scheduler, markers
│   ├── database/
│   │   ├── base.py             # Declarative base, naming convention, identity
│   │   ├── config.py           # Injected absolute database configuration
│   │   ├── engine.py           # Engine, PRAGMAs, Database lifecycle
│   │   ├── errors.py           # Driver error classification
│   │   ├── health.py           # Health and integrity diagnostics
│   │   ├── migrations.py       # Alembic manager and startup policy
│   │   ├── repository.py       # Generic repository foundation
│   │   └── session.py          # Explicit-commit unit of work
│   └── filesystem/
│       ├── drives.py           # Windows drive type, capacity, free space
│       ├── layout.py           # Approved data-root layout and file names
│       ├── scaffold.py         # Additive directory creation and safe cleanup
│       └── validation.py       # Read-only location validation and write probe
├── services/
│   ├── backup_service.py       # Verified backup creation and publishing
│   ├── backup_workspace.py     # Backup service wiring for GUI/runner
│   ├── catch_up_service.py     # Startup missed-backup evaluation/execution
│   ├── database_runtime.py     # Reopen/replace runtime for restore/relocation
│   ├── relocation_service.py   # Verified database relocation workflow
│   ├── restore_service.py      # Staged restore with rollback
│   ├── retention_service.py    # Managed retention application
│   ├── schedule_service.py     # Schedule settings and Task Scheduler sync
│   ├── setup_service.py        # Validate → scaffold → initialize → persist
│   ├── startup_service.py      # Setup / recovery / ready startup assessment
│   └── upgrade_service.py      # Pre-upgrade safety-backup gate
├── tools/
│   ├── backup.py               # Headless scheduled/manual backup runner
│   └── migrate.py              # Headless migration/health CLI
└── ui/
    ├── main_window.py          # Shell, navigation, session persistence, F5
    ├── components/             # Sidebar, top bar, cards, controls, feedback
    │   ├── controls.py         # make_button, set_dialog_size, DetailCard
    │   └── feedback.py         # StatusBadge, EmptyState, Toast, show_toast
    ├── dialogs/                # Setup, recovery, backup settings, restore dialogs
    ├── themes/                 # Tokens, token-driven QSS, runtime theme manager
    ├── viewmodels/             # QtCore-only view models
    └── views/                  # Dashboard and backup views
migrations/                     # Alembic environment and version scripts
alembic.ini                     # Script location; URL injected at runtime
tests/                          # pytest unit, UI, database, and startup tests
scripts/check.ps1               # Lint + test helper
docs/                           # Approved project documentation
Reports/                        # Phase completion reports
```

`app/repositories` and `app/modules` are intentionally absent until the phases
that need them. The scheduled runner is implemented as `app/tools/backup.py`
(headless, no Qt).

## Architecture rules in force

- Views hold no business logic; view models never import `QtWidgets`.
- Domain code imports no Qt, SQLAlchemy, Alembic, or `sqlite3`.
- Core infrastructure imports no Qt or database libraries.
- Database and filesystem infrastructure import no Qt or UI code.
- Application services import no Qt or UI code; the wizard calls them from a
  worker thread and marshals results back to the GUI thread.
- Money is never handled through `float`; persistence uses integer paise.
- The database path is injected as an absolute path; it is never guessed,
  defaulted, created implicitly, or silently switched. Only the explicit setup
  wizard and the explicit maintenance CLI may create a database file.
- Configuration and logs live outside the future business data folder.
- Dependencies are passed explicitly through `AppContext`; there is no global
  service locator.

These boundaries are checked by `tests/test_architecture.py`.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| `ModuleNotFoundError: PySide6` | Activate `.venv` or use `.\.venv\Scripts\python.exe`. |
| App exits immediately | Check `%LOCALAPPDATA%\GobindasBMS\logs\app.log`. |
| "already running" message | Only one GUI instance is allowed; close the existing window. |
| Theme resets after restart | Check that `%APPDATA%\GobindasBMS` is writable; see the log for a save error. |
| Invalid configuration | The old file is kept as `config.corrupt-*.json`; the recovery dialog offers Locate existing data, Start a new setup, Retry, or Exit. |
| Missing drive at startup | Reconnect the drive and choose Retry, or locate the existing data. The app never creates a replacement database. |
| Setup cancelled | The application exits without creating a database or saving a location; run it again to retry. |
| Tests cannot open a display | Set `QT_QPA_PLATFORM=offscreen` (the test suite sets it automatically). |

## Documentation

- `docs/BLUEPRINT.md` - product scope and open questions
- `docs/ARCHITECTURE.md` - technical architecture and Phase 1–5 implementation records
- `docs/DEVELOPMENT_ROADMAP.md` - phase plan and completion status
- `docs/UI_UX_BLUEPRINT.md` - UI direction, final design system, and limitations
- `docs/BACKUP_STRATEGY.md`, `docs/SECURITY_AND_DATA_PROTECTION.md`,
  `docs/DATABASE_SCHEMA.md` - backup, security, and schema references
- `Reports/PHASE_01_REPORT.md` - Phase 1 completion report
- `Reports/PHASE_02_REPORT.md` - Phase 2 completion report
- `Reports/PHASE_03_REPORT.md` - Phase 3 completion report
- `Reports/PHASE_04_REPORT.md` - Phase 4 completion report
- `Reports/PHASE_05_REPORT.md` - Phase 5 completion report

## Next phase

Review `Reports/PHASE_05_REPORT.md` and explicitly authorize the next phase. Do
not start Phase 6 authentication, master data, or any business phase without owner
review/approval. Phase 5 preserved the verified backup, restore, scheduling,
relocation, and migration-safety foundations established in earlier phases.
Real Windows visual/DPI walkthroughs and the Phase 4 manual integration drill
remain outstanding release-verification tasks.
