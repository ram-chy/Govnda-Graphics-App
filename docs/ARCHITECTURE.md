# ARCHITECTURE — Gobindas Graphics Business Management System

| Field | Value |
| --- | --- |
| Document | ARCHITECTURE.md |
| Version | 1.4 |
| Date | 2026-11-17 |
| Status | Phases 1–5 implemented; Phase 5 owner review pending |
| Audience | Developers, reviewer, future maintainers |
| Related | BLUEPRINT.md, DATABASE_SCHEMA.md, BACKUP_STRATEGY.md, DEVELOPMENT_ROADMAP.md |

## 1. Architecture goals

1. Keep the desktop UI thin and replaceable in principle without touching business rules.
2. Keep financial logic exact, testable, and independent of Qt and SQLAlchemy.
3. Keep the runtime simple: one process for the GUI, one lightweight process for scheduled backups, one local SQLite file.
4. Make failure modes visible and data loss difficult.
5. Avoid abstractions that do not pay for themselves in a single-user desktop app.

## 2. Stack and verified compatibility

### 2.1 Confirmed stack

Python, PySide6 (Qt Widgets), MVVM/presentation–service separation, SQLite, SQLAlchemy 2, Alembic, Pydantic, Decimal-based money, PyQtGraph, ReportLab, OpenPyXL, Python logging, pytest, PyInstaller, Inno Setup, Git. These are fixed by the brief; changes require an approved ADR.

### 2.2 Version policy

- Pin exact versions in `requirements.txt` (and compatible ranges in `pyproject.toml`) after a Phase 1 install-and-smoke-test.
- Use one Python minor version for development and for the release build.
- Do not upgrade dependencies during a release-hardening phase.
- Record the tested combination in this document when Phase 1 locks it.

### 2.3 Compatibility verification (2026-11-12, PyPI metadata)

| Package | Latest at review | Python support declared | Notes |
| --- | --- | --- | --- |
| PySide6 | 6.12.0 | >=3.10,<3.16 incl. 3.14 | Windows wheel is `cp310-abi3-win_amd64`; ABI3 works on 3.14 |
| SQLAlchemy | 2.1.8 | >=3.11 incl. 3.14 | SQLAlchemy 2 API mandatory |
| Alembic | 1.20.1 | >=3.10 incl. 3.14 | |
| Pydantic | 2.14.3 | >=3.10 incl. 3.14 | v2 API |
| PyQtGraph | 0.14.0 | >=3.10 | Pure Python; needs NumPy 2.x |
| NumPy | 2.5.4 | >=3.12 incl. 3.14 | Transitive via PyQtGraph |
| ReportLab | 5.1.0 | >=3.9,<4.0? (declared `<4` in metadata) | **Resolve before pinning**; see risk R-04 |
| OpenPyXL | 3.1.5 | >=3.8 | No 3.14 classifier, but pure Python; smoke test required |
| pytest | 9.2.0 | >=3.10 incl. 3.14 | Dev only |
| PyInstaller | 6.22.3 | >=3.8,<3.16 incl. 3.14 | Build-time only |

**Decision:** target **CPython 3.14.6** (installed). Fallback: CPython 3.13.x if any runtime/build issue appears in Phase 1. Python 3.15 is deliberately avoided as too new for a production desktop build.

**Caveat on ReportLab:** PyPI metadata for 5.1.0 reports `requires_python = "<4,>=3.9"`, which is a malformed-looking ceiling but does not exclude 3.14. The Phase 1 smoke test must import ReportLab and generate a one-page PDF. If it fails, pin the newest 4.x release that works and record the change.

**Phase 1 result (2026-11-13):** the smoke test passed on CPython 3.14.6 with ReportLab 5.1.0, which generated a valid one-page PDF. ReportLab 5.1.0 is therefore the pinned Phase 1 version; no 4.x fallback is required (AQ-07 resolved). The installed versions match the table above exactly.

### 2.4 Runtime dependency policy

- Runtime dependencies are limited to: PySide6, SQLAlchemy, Alembic, Pydantic, PyQtGraph, ReportLab, OpenPyXL.
- The backup runner must depend only on the Python standard library (see ADR-010).
- Development dependencies: pytest, pytest-qt (optional), and a linter/formatter chosen in Phase 1.
- No `requests`, no web framework, no async runtime, no extra ORM, no UI toolkit beyond Qt.

## 3. Architectural decisions (ADRs)

Status values: **Accepted** = required by the brief; **Proposed** = needs owner approval; **Deferred** = decided later.

### ADR-001 — Python 3.14 on x64 Windows
- **Status:** Proposed.
- **Decision:** Build and ship with CPython 3.14.6, 64-bit.
- **Rationale:** Installed already; all required packages declare 3.14 support; released October 2025, so mature by the project start.
- **Alternatives:** 3.13 (more conservative; available via Laragon), 3.15 (too new).
- **Consequences:** Must run a full dependency-in-one-venv install and PyInstaller smoke test in Phase 1.

### ADR-002 — Layered modular monolith
- **Status:** Accepted (brief).
- **Decision:** One deployable application with modules as folders, no services, APIs, or message bus.
- **Rationale:** Single-user desktop; lowest operational cost; clean boundaries still enforceable by imports.
- **Consequences:** Module boundaries are conventions plus import lint checks, not process boundaries.

### ADR-003 — Domain entities separate from ORM models
- **Status:** Proposed.
- **Decision:** `app/domain` contains plain Python dataclasses and value objects with no Qt, no SQLAlchemy, and no I/O. `app/infrastructure/database/orm` contains SQLAlchemy mappings. Repositories translate between them.
- **Rationale:** Financial rules and invariants remain unit-testable without a database; schema changes do not leak into business code.
- **Alternatives:** (a) use ORM models everywhere — less code, but couples rules to SQLAlchemy; (b) full DDD aggregates — too heavy for this size.
- **Consequences:** Explicit mapping code for each aggregate. Reporting may bypass the domain with read-only SQL/ORM queries returning DTOs.
- **Review trigger:** If mapping overhead exceeds ~20% of module code, revisit this ADR with measurements.

### ADR-004 — MVVM with Qt-aware ViewModels
- **Status:** Proposed.
- **Decision:** Views are `QWidget`/`QMainWindow` subclasses with no business logic. ViewModels are `QObject` subclasses exposing read-only `Property`/signals and command methods. ViewModels may import QtCore, but never QtWidgets. ViewModels call application services and map results to display state.
- **Rationale:** Qt signals/slots are the native binding mechanism; a hand-written observer layer adds no value.
- **Consequences:** ViewModels are not portable to another UI toolkit; business rules stay portable in the domain.

### ADR-005 — Exact money as scaled integers
- **Status:** Accepted (brief requires no floating point); detailed policy proposed.
- **Decision:** Never store money as `REAL`/float. Store integer minor units; use `Decimal` in domain calculations; convert at boundaries. See DATABASE_SCHEMA.md §4.
- **Rationale:** Exactness, stable equality, predictable rounding, SQLite affinity safety.
- **Consequences:** Every calculation path must use the money/quantity value objects; tests enforce no float in financial modules.

### ADR-006 — Repository + Unit of Work
- **Status:** Proposed.
- **Decision:** One SQLAlchemy `Session` per unit of work, created by a `UnitOfWork` context manager in the application layer. Repositories receive the session; services own commit/rollback. One use case = one short transaction.
- **Rationale:** Prevents partial postings, simplifies testing, keeps transactions short for SQLite.
- **Alternatives:** Session-per-view (stale data, long transactions), global session (thread hazards).
- **Consequences:** No lazy loading after commit; services must load everything they need inside the UoW and return DTOs.

### ADR-007 — Alembic migrations bundled and applied at startup
- **Status:** Implemented for the maintenance path in Phase 4. Revision inspection and refusal policy are live; schema changes run through a verified safety-backup gate before Alembic is applied. Normal startup still never migrates automatically.
- **Decision:** Migrations live in `migrations/` and are shipped inside the frozen app. On startup, the app reads the current revision and refuses unsafe states. For supported maintenance-driven upgrades/downgrades, the application verifies the current database, acquires the global operation lock, creates and verifies a Safety backup, and only then applies the schema change. Automatic startup migration remains disabled.
- **Rationale:** Desktop installs cannot rely on a developer running migrations manually; schema and app versions must move together.
- **Phase 2 behaviour:** A newer or unknown revision refuses startup. A missing or older revision also refuses startup because no verified pre-upgrade backup exists yet; the operator runs `python -m app.tools.migrate upgrade` explicitly. Startup never upgrades silently.
- **Consequences:** Migration scripts must be path-independent (programmatic `Config`, absolute script location via `sys._MEIPASS` when frozen). Failed upgrades abort startup and preserve the backup.

### ADR-008 — SQLite connection profile
- **Status:** Implemented in Phase 2.
- **Decision:** Every connection sets `PRAGMA foreign_keys=ON`, `busy_timeout=5000` (configurable), `journal_mode=WAL`, `synchronous=FULL`, `wal_autocheckpoint=1000`, `temp_store=MEMORY`, `trusted_schema=OFF`. `foreign_keys` must be enabled per connection via an event hook; the hook also verifies that WAL and foreign keys actually took effect.
- **Rationale:** Referential integrity, crash safety, concurrent readers, short writer waits. `trusted_schema=OFF` blocks schema objects that could execute unsafe functions.
- **Trade-off:** `synchronous=FULL` is slower than `NORMAL`; for a financial desktop app, durability wins. Re-evaluate with measurements if write latency is unacceptable.
- **Consequences:** WAL sidecar files (`-wal`, `-shm`) exist while running; backups must use the Online Backup API, never a file copy. A passive checkpoint runs at shutdown before the engine is disposed.

### ADR-009 — Configuration outside the data folder
- **Status:** Proposed.
- **Decision:** Store machine configuration in `%APPDATA%\GobindasBMS\config.json` (atomic write, schema version, no secrets). Logs go to `%LOCALAPPDATA%\GobindasBMS\logs`. Business files live only in the user-selected data folder.
- **Rationale:** Meets the brief's requirement that location config is independent of the business database; survives application reinstall.
- **Alternatives:** Registry (harder to inspect/backup), database (cannot locate the database), INI beside the exe (blocked by Program Files permissions).
- **Consequences:** Config must be validated and recoverable; a corrupt config triggers a repair flow, not data loss.

### ADR-010 — Backup runner uses stdlib `sqlite3` only
- **Status:** Proposed.
- **Decision:** The backup core is implemented against Python's `sqlite3` (Online Backup API, `integrity_check`) with no SQLAlchemy/Qt imports. Both the GUI and `GobindasBMS-Backup.exe` call it. The runner is packaged separately without Qt.
- **Rationale:** Scheduled backup must work with the app closed, start fast, and have a minimal failure surface.
- **Consequences:** Backup code cannot use ORM models; it reads only the config and the database file.

### ADR-011 — Two executables
- **Status:** Proposed.
- **Decision:** Ship `GobindasBMS.exe` (GUI) and `GobindasBMS-Backup.exe` (headless). Both use the same Python package.
- **Rationale:** A headless runner avoids launching Qt from Task Scheduler and keeps the scheduled task footprint small.
- **Consequences:** Two PyInstaller specs; shared version metadata; installer places both.

### ADR-012 — Task Scheduler, current user, with catch-up fallback
- **Status:** Proposed.
- **Decision:** Register a per-user scheduled task that runs the backup runner at the configured time, only when the user is logged on. On every app start, if the last successful automatic backup is older than the configured interval and a backup is due, run a catch-up backup.
- **Rationale:** Avoids storing a Windows password or installing a service; acceptable for a workstation app.
- **Consequences:** If the PC is off or the user is logged out at 22:00, the backup happens later. This limitation must be shown in the UI and documented.

### ADR-013 — Single-instance application, separate backup lock
- **Status:** Proposed.
- **Decision:** The GUI holds a named mutex (`Local\GobindasBMS.App`) and refuses a second instance. Backup operations hold an exclusive lock file in the data folder (`Backups\.backup.lock`) so GUI and runner cannot overlap.
- **Rationale:** SQLite allows one writer; overlapping backups waste I/O and can confuse verification.
- **Consequences:** A stale lock file must be detected by owner PID/age and recovered safely.

### ADR-014 — Restore then restart
- **Status:** Proposed.
- **Decision:** Restore is performed with all application database connections disposed; after verification the app relaunches itself. The staged restore keeps a rollback copy until the new database passes `integrity_check` and opens successfully.
- **Rationale:** Guarantees no cached connections or stale pages touch the replaced file, while satisfying "reopen only after successful verification".
- **Consequences:** The user sees a short restart; failure leaves the original file and a safety backup intact.

### ADR-015 — Synchronous use cases, background workers for long work
- **Status:** Proposed.
- **Decision:** Application services are synchronous. ViewModels call them directly when the expected duration is short (< 200 ms) and via `QThreadPool`/`QRunnable` with signals for backup, restore, migration, export, import, and large reports.
- **Rationale:** No async complexity; SQLite local reads are fast; the UI must not freeze.
- **Consequences:** Workers must not touch widgets; results return as immutable DTOs; cancellation is cooperative.

### ADR-016 — Pydantic at the application boundary
- **Status:** Proposed.
- **Decision:** Pydantic models validate raw input from the UI (form payloads, imports) and shape read DTOs. Domain value objects remain the authority for money and business invariants.
- **Rationale:** Concise validation with clear field errors; avoids hand-written validation code without letting Pydantic replace domain rules.
- **Consequences:** Errors are translated into a UI-friendly `ValidationError` structure.

### ADR-017 — Theming via QSS and design tokens
- **Status:** Implemented in Phase 1; extended with the final tokenized design system in Phase 5 (§19).
- **Decision:** A token module defines colors/spacing/typography; a small generator produces QSS for light and dark themes. Theme switching is runtime, no restart.
- **Rationale:** Qt Widgets has no native design-token system; centralized QSS avoids per-widget styling drift.
- **Consequences:** Custom-painted widgets must read tokens, not hard-coded colors.

### ADR-018 — Rotating file logging per process
- **Status:** Proposed.
- **Decision:** `logging` with `RotatingFileHandler` (5 MB × 5) in `%LOCALAPPDATA%\GobindasBMS\logs`; separate files for GUI and backup runner; console handler only in development.
- **Rationale:** Diagnosable failures without external infrastructure; bounded disk usage.
- **Consequences:** No financial payloads or personal data in logs; correlation IDs for backup runs.

### ADR-019 — PyInstaller onedir + Inno Setup
- **Status:** Proposed.
- **Decision:** Build with PyInstaller `--onedir` (faster start, easier plugin handling), then package with Inno Setup. Exclude unused Qt modules, ship Qt plugins explicitly, embed version metadata and icons.
- **Rationale:** `--onefile` extracts to temp on every launch and complicates antivirus behaviour.
- **Consequences:** Installer is larger on disk but starts faster; must test on a clean Windows VM without Python.

## 4. System overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Presentation (app/ui, app/modules/*/views)                           │
│  QMainWindow, Views, Dialogs, Widgets, QSS themes, Qt models         │
│  ── signals/slots ──▶ ViewModels (QtCore only)                       │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ calls use cases, receives DTOs
┌───────────────────────────────▼──────────────────────────────────────┐
│ Application (app/services, app/modules/*/services)                   │
│  Use cases, validation, UnitOfWork, transaction orchestration        │
└───────────────┬──────────────────────────────┬───────────────────────┘
                │ domain objects               │ repository protocols
┌───────────────▼──────────────┐  ┌────────────▼───────────────────────┐
│ Domain (app/domain)          │  │ Infrastructure (app/infrastructure)│
│  Entities, value objects,    │  │  SQLAlchemy ORM, repositories,     │
│  rules, calculators          │  │  DB engine, Alembic, backup,       │
│  No Qt, no SQLAlchemy, no IO │  │  exports, logging, scheduler       │
└──────────────────────────────┘  └────────────┬───────────────────────┘
                                               │ sqlite3 / files
                                        ┌──────▼──────┐
                                        │ SQLite file │
                                        └─────────────┘
```

### 4.1 Dependency rules

Allowed:

- UI → ViewModels → application services → domain + repository protocols.
- Infrastructure → domain (mapping) and application interfaces.
- Application → domain, repository protocols, infrastructure only via composition root.

Forbidden:

- Domain → UI, SQLAlchemy, Alembic, PySide6, `sqlite3`, filesystem.
- ViewModels/Views → SQLAlchemy sessions or repositories directly.
- Repositories → Qt or services.
- Module A importing module B's repository; use B's service.
- Business rules inside Qt slots/widgets.
- `float` in money, price, tax, or quantity calculations.

These rules are enforced by code review plus a lightweight import test in Phase 1 (e.g., `pytest` walking `app.domain` imports).

### 4.2 Runtime composition

`app/main.py` is the composition root:

1. Configure logging and crash handling.
2. Acquire the single-instance guard.
3. Load the configuration with a status of `MISSING`, `LOADED`, or `RECOVERED`.
4. Classify startup as `SETUP_REQUIRED`, `RECOVERY_REQUIRED`, or `READY`.
5. Run the blocking setup wizard or recovery dialog when required.
6. For an existing database, verify the drive, folder, file, identity, revision,
   and health before opening it.
7. Build the open `Database` and `AppContext` from the verified parts.
8. Create ViewModels and the main window, then start the Qt event loop.

No global mutable service locator. Dependencies are passed explicitly; a small `AppContext` dataclass holds the wiring.

## 5. Layer responsibilities

### 5.1 Presentation

- Windows, dialogs, reusable widgets, table models, delegates.
- Formatting of money/dates for display; input parsing to raw values.
- Keyboard shortcuts, focus order, accessibility names.
- No SQL, no business decisions, no direct file IO.

### 5.2 ViewModels

- Expose state (loading, rows, totals, errors) via Qt properties/signals.
- Translate UI intent into service calls.
- Map service DTOs to display rows; format with locale rules.
- Own validation *presentation* (field-level messages) while domain/application own validation *rules*.
- Never import `PySide6.QtWidgets`.

### 5.3 Application services

- One public method per use case (`create_invoice`, `record_payment`, `run_manual_backup`).
- Validate input DTOs (Pydantic) and authorization (when added).
- Open a `UnitOfWork`, load aggregates, invoke domain rules, persist, commit, return DTO.
- Emit audit records within the same transaction when required.
- Translate infrastructure exceptions into application errors.

### 5.4 Domain

- Value objects: `Money`, `Quantity`, `UnitPrice`, `Rate`, `Address`, `DocumentNumber`.
- Entities and invariants: invoice totals, allocation of payments, stock movement effects, rounding.
- Pure functions/calculators with explicit inputs and outputs.
- No persistence, no clock/network; time and IDs are injected.

### 5.5 Infrastructure

- SQLAlchemy engine/session, ORM mappings, repository implementations.
- Alembic environment and version scripts.
- SQLite backup/restore/verification.
- Config file IO, logging setup, file storage.
- PDF/Excel export writers.
- Task Scheduler integration.
- Clock/ID generators.

## 6. MVVM implementation approach

### 6.1 ViewModel shape

```python
class InvoiceListViewModel(QObject):
    rowsChanged = Signal()
    stateChanged = Signal()
    errorRaised = Signal(str)

    def __init__(self, service: SalesQueryService) -> None:
        super().__init__()
        self._service = service
        self._rows: list[InvoiceRow] = []
        self._loading = False

    @Property(bool, notify=stateChanged)
    def loading(self) -> bool: ...

    def load(self, page: int = 1) -> None: ...
```

Rules:

- ViewModels do not inherit widgets and are testable with `pytest-qt` or plain Qt event loops.
- Long operations go through `app/ui/workers.py`; worker results are delivered on the GUI thread.
- Views bind one-way (VM → view) and send commands (view → VM).
- No direct widget references inside ViewModels; use signals and observable properties.
- Table data is exposed as immutable row DTOs, not ORM objects.

### 6.2 Navigation shell

- `QMainWindow` with a left sidebar (`QListWidget`-based navigation or a custom `NavButton` list), a top context bar, and a `QStackedWidget` content area.
- Modules register a navigation entry and a lazy view factory. Views are created on first navigation (startup time) and cached.
- Deep links (e.g., open invoice from dashboard) go through a `NavigationService` interface implemented by the shell.
- Each module owns its views, viewmodels, and service facade; no cross-module widget imports.

### 6.3 State and errors

- Each ViewModel models `idle / loading / ready / empty / error` explicitly.
- Validation errors map to fields; unexpected errors show a user-safe dialog with a correlation ID and log the details.
- Retry is explicit; no infinite retry loops.

## 7. Database access strategy

### 7.1 Engine and sessions

- One `Engine` per database path, created at startup, disposed on shutdown/restore.
- `Session` per unit of work; `expire_on_commit=False` only if DTO mapping happens before commit; prefer mapping inside the transaction.
- Connections are short-lived. No session is stored on a widget or a long-lived service.
- Read-only screens use a fresh session per query and return DTOs.
- Phase 2 implementation: `QueuePool(pool_size=2, max_overflow=0, pool_pre_ping=True)` with an explicit `check_same_thread=False` policy. The small bound makes a second concurrent writer wait instead of multiplying connections.

### 7.2 Unit of Work

```python
with uow:
    invoice = repo.get(...)
    domain.post(invoice)
    repo.save(invoice)
    audit.record(...)
    uow.commit()
```

- Context manager rolls back on exception.
- Nesting is forbidden; a service method is one transaction.
- Audit and business mutations share the transaction.
- No dialogs, file IO, PDF generation, or long calculations inside a transaction.
- Phase 2 implementation: `UnitOfWork` commits only on an explicit `commit()` call. Leaving the block without committing rolls back. Exceptions roll back before propagating. The session always closes and returns its connection to the pool.

### 7.3 Query strategy

- Lists: explicit projections (columns/DTOs), not full entities.
- Pagination: `LIMIT/OFFSET` for modest offsets; keyset pagination for large tables where needed.
- Indexes defined from known filters (date, party, status, document number).
- SQL aggregation for reports, returning DTOs; never load 100k rows into Python to sum them.
- N+1 queries are treated as defects; use `selectinload` deliberately or projections.

### 7.4 Migrations

- Alembic is the only way schema changes ship.
- Migration scripts are reviewed, reversible where practical, and tested on a copy of a realistic database.
- Startup applies migrations after creating a verified safety backup.
- Downgrades are not automatic; a failed upgrade stops the app and points to the safety backup.
- Phase 2 implementation: the baseline revision `0001_baseline` is intentionally empty apart from database identity PRAGMAs. `Base.metadata.create_all()` is never used in production. Startup refuses newer, unknown, older, and uninitialized revisions instead of changing them automatically until Phase 4 introduces the safety-backup gate.

## 8. Lifecycle

### 8.1 GUI startup

| Step | Action | Failure behaviour |
| --- | --- | --- |
| 1 | Install excepthook, start log | Continue with stderr fallback |
| 2 | Single-instance mutex | Focus existing instance or exit |
| 3 | Load config with status | Missing → setup wizard; corrupt → recovery dialog with the original file preserved |
| 4 | Classify startup | No location → setup; incomplete/corrupt/unavailable → recovery; verified → ready |
| 5 | Setup wizard (first launch) | Cancel exits with no database and no saved location; failure stays on the progress page with a safe retry path |
| 6 | Recovery dialog | Retry / Locate existing data / Start new setup / Exit; never creates a fallback database |
| 7 | Validate configured data root and drive | Blocking recovery; no directory or file is created |
| 8 | Open configured database; verify file, identity, connection PRAGMAs, and health | Blocking recovery; never auto-create or substitute another file |
| 9 | Compare Alembic revision | Newer/unknown → refuse; older/uninitialized → refuse until Phase 4 adds a verified safety backup and upgrade |
| 10 | Build services/viewmodels/window | Fatal error dialog with log ID |
| 11 | Load dashboard | Show verified status only; errors contained |
| 12 | Event loop | — |

### 8.2 GUI shutdown

1. Ask ViewModels to flush/confirm unsaved forms.
2. Stop workers cooperatively; wait with a timeout and log.
3. Dispose engine (`engine.dispose()`), checkpoint WAL if appropriate.
4. Release single-instance mutex.
5. Flush logs.

### 8.3 Backup runner lifecycle

1. Parse minimal args (`--scheduled`, `--config PATH`).
2. Configure logging.
3. Acquire backup lock; exit `0` with a log line if another backup is running.
4. Read config; if backup disabled or unconfigured, exit `0`.
5. Verify DB path and free space.
6. Run backup → verify → publish → metadata → retention.
7. Exit `0` on success; non-zero on failure (Task Scheduler history shows the result).
8. Never show UI; failures are written to the log and an error flag file inspected by the app next launch.

## 9. Error handling

### 9.1 Exception hierarchy

```text
AppError
├── ConfigurationError
├── SetupError
├── DatabaseUnavailableError
├── MigrationError
├── ValidationError          (field → message mapping)
├── DomainRuleError          (business rule violated)
├── NotFoundError
├── ConflictError            (e.g., duplicate document number)
├── BackupError
├── RestoreError
└── ExportError
```

- Infrastructure exceptions (`SQLAlchemyError`, `OSError`, `sqlite3.Error`) are caught at the boundary and wrapped with context.
- `except Exception: pass` is forbidden; every catch either handles, wraps, or logs and re-raises.
- User messages explain what happened and what to do; they do not expose stack traces or SQL.
- Every unexpected error gets a correlation ID that is written to the log and shown in the dialog.
- A global `sys.excepthook` logs the traceback, shows a fatal-error dialog, and attempts a clean shutdown.
- Qt slot exceptions must not escape into the C++ event loop.

### 9.2 Retry policy

- Reads may retry once on `database is locked` after a short delay.
- Writes do not auto-retry a partially executed use case; the user retries the action.
- Backup may retry once on a transient file lock, then fail loudly.
- No exponential-backoff framework; keep it explicit and small.

## 10. Logging

| Item | Decision |
| --- | --- |
| Library | Standard `logging` |
| Location | `%LOCALAPPDATA%\GobindasBMS\logs\app.log`, `backup.log` |
| Rotation | 5 MB × 5 files per process |
| Format | `timestamp level logger corr_id message` |
| Levels | INFO default; DEBUG via config/env for support |
| Console | Development only |
| Prohibited | Passwords, full SQL parameter dumps, customer personal data, full financial payloads |
| Correlation | One ID per user action/backup run, propagated to service logs |

Audit logging is separate from diagnostic logging and lives in the database (see SECURITY_AND_DATA_PROTECTION.md).

## 11. Threading

- Qt GUI thread owns all widgets.
- `QThreadPool` + `QRunnable` for backups, restore, exports, imports, and large reports.
- Workers receive plain data/DTOs; they open their own short-lived session or call a service designed for worker use.
- SQLAlchemy sessions are never shared between threads.
- Progress/cancel are signals; cancellation is checked between chunks and before commit.
- Database writes triggered by workers use the normal UoW; the GUI thread does not hold a write transaction while waiting.

## 12. Packaging strategy

### 12.1 Build

- Two PyInstaller specs: GUI (`--onedir`, windowed) and backup runner (`--onedir` or `--onefile`, console-less).
- Bundle Alembic scripts, theme QSS/resources, icons, and version metadata.
- Exclude unused Qt modules and test packages; include required SQLite/Qt plugins explicitly.
- Build on the same Windows architecture and Python minor version as tested.
- Test the frozen build, not only source execution.

### 12.2 Installer

- Inno Setup installs per-machine or per-user (decision in Phase 12; prefer per-user to avoid admin requirements).
- Installs both executables, start-menu shortcut, uninstaller.
- Does **not** create a database or choose a data folder; the first-run wizard owns that.
- Optional scheduled task is created by the app after the user enables automatic backups, not silently by the installer.
- Uninstall must never delete the user's data folder; it asks whether to remove configuration/logs only.

### 12.3 Distribution risks

- Unsigned binaries trigger SmartScreen; document the warning or sign (Q-19).
- Antivirus false positives are common with PyInstaller; submit false-positive reports and prefer onedir.
- Qt licensing: PySide6 is LGPL; comply with relinking requirements and include notices. Confirm commercial policy before release.

## 13. Trade-offs and rejected options

| Decision | Benefit | Cost | Rejected alternative |
| --- | --- | --- | --- |
| Plain layered monolith | Simple, debuggable | Boundaries by discipline | Microservices, plugin architecture |
| Separate domain/ORM models | Testable rules, schema isolation | Mapping code | ORM models as domain entities |
| Integer scaled money | Exact | Manual conversion | SQLite `NUMERIC`/float |
| WAL + `synchronous=FULL` | Crash durability, readers during writes | Slower commits | `NORMAL`, delete journal |
| Two executables | Headless scheduled backup | Two build artifacts | One exe with `--backup` flag |
| Startup migrations | Installs upgrade themselves | Requires migration discipline | Manual migration tool |
| Config in `%APPDATA%` | Reinstall-safe, inspectable | Separate from data | Registry, DB, INI |
| Qt Widgets | Native, mature, accessible | Less modern styling than QML | QML/Qt Quick |
| Synchronous services | Simpler reasoning | Must offload long work | asyncio |
| `--onedir` build | Fast start, fewer AV issues | Larger folder | `--onefile` |

## 14. Testing seams

- Domain: pure unit tests, no database, property-style tests for rounding/allocations.
- Application: services tested with in-memory or temp-file SQLite and real repositories; Alembic applied to a temp DB.
- Infrastructure: backup/restore tests use temp folders; failure injection for missing drive, full disk, corrupt file.
- UI: ViewModel tests with a plain `QApplication` and the `offscreen` Qt platform (pytest-qt is not used); smoke test that every view constructs without a database mutation.
- Packaging: automated build plus a manual clean-VM checklist.

Detailed test strategy is in DEVELOPMENT_ROADMAP.md §6.

## 15. Unresolved architecture questions

| ID | Question | Needed by | Phase 1 outcome |
| --- | --- | --- | --- |
| AQ-01 | Is Python 3.14 or 3.13 the final build target? | Phase 1 | **Resolved for Phase 1:** CPython 3.14.6 verified with the full dependency set. Final release target is re-confirmed at packaging (Phase 12). |
| AQ-02 | Is per-user or per-machine installation preferred? | Phase 12 | Open. |
| AQ-03 | Code-signing certificate? | Phase 12 | Open. |
| AQ-04 | SQLCipher/encryption at rest? | Before schema freeze | Open. |
| AQ-05 | Authentication/roles in v1? | Phase 6 | Open. |
| AQ-06 | Thermal receipt printing? | Phase 10 | Open. |
| AQ-07 | ReportLab version pinned after smoke test | Phase 1 | **Resolved:** ReportLab 5.1.0 generated a one-page PDF on Python 3.14.6. |
| AQ-08 | pytest-qt as a dev dependency? | Phase 1 | **Resolved:** not adopted. UI tests use plain `QApplication` with `QT_QPA_PLATFORM=offscreen`; no extra dependency was needed. |

## 16. Phase 1 implementation record (2026-11-13)

This section records what was actually built and verified in Phase 1. It supplements, and does not replace, the target architecture above.

### 16.1 Locked environment

| Item | Value |
| --- | --- |
| Interpreter | CPython 3.14.6, 64-bit, in `.venv` |
| Virtual environment | `.venv` at the repository root |
| Runtime manifest | `requirements.txt` (exact pins) |
| Development manifest | `requirements-dev.txt` (`-r requirements.txt` + pytest + ruff) |
| Project metadata | `pyproject.toml` (compatible ranges, pytest and ruff configuration) |
| Linter/formatter | ruff 0.17.5, `E,F,I,W,UP,B,SIM`, line length 100, target `py314` |
| Test runner | pytest 9.2.0 |

Runtime pins: PySide6 6.12.0, SQLAlchemy 2.1.8, Alembic 1.20.1, Pydantic 2.14.3, PyQtGraph 0.14.0, NumPy 2.5.4 (transitive and pinned), ReportLab 5.1.0, OpenPyXL 3.1.5. `pip` was upgraded inside the virtual environment before installation.

All seven approved runtime packages were installed even though only PySide6 is exercised by Phase 1 code, so that the locked environment is smoke-tested as a whole before Phase 2 depends on it.

### 16.2 Implemented structure

Only files used in Phase 1 were created:

```text
app/
├── __init__.py
├── main.py                     # Entry point and composition root
├── app_context.py              # Startup wiring (paths, config, theme, view model)
├── core/
│   ├── config.py               # AppConfig, validation, atomic ConfigService
│   ├── constants.py            # Fixed names, versions, defaults, mutex name
│   ├── error_handling.py       # Global excepthook and safe error reporting
│   ├── exceptions.py           # AppError hierarchy
│   ├── formatting.py           # INR formatting with Indian grouping
│   ├── logging_config.py       # Rotating handlers and correlation IDs
│   ├── paths.py                # %APPDATA% / %LOCALAPPDATA% path resolution
│   └── single_instance.py      # Windows named-mutex guard
├── domain/
│   └── value_objects/
│       └── currency.py         # Currency value object and INR default
└── ui/
    ├── main_window.py          # Shell, navigation, status bar, theme toggle
    ├── components/             # Sidebar, top bar, cards, placeholder view
    ├── dialogs/                # Safe user-facing error dialog
    ├── themes/                 # Tokens, QSS generator, runtime manager
    ├── viewmodels/             # QtCore-only shell view model
    └── views/                  # Dashboard foundation
tests/                           # 147 tests across 11 modules
scripts/check.ps1                # Lint + tests helper
```

`app/services`, `app/repositories`, `app/modules`, `app/infrastructure`, `migrations`, `backup_runner`, and `app/ui/resources` are intentionally absent because nothing in Phase 1 uses them. They are created by the phases that own them.

### 16.3 Startup and shutdown

`python -m app.main` performs:

1. Resolve `AppPaths` (`%APPDATA%\GobindasBMS`, `%LOCALAPPDATA%\GobindasBMS\logs`), create the log directory, and configure rotating logging.
2. Load and validate `config.json`; a missing file yields defaults, an invalid file is quarantined as `config.corrupt-<timestamp>.json`.
3. Acquire the `Local\GobindasBMS.App` named mutex; a second instance exits with a message rather than running concurrently. Automated startup tests override the mutex name through `GOBINDAS_MUTEX_NAME` so they never collide with a running application or with each other.
4. Create `QApplication` with the application name, version, and organisation.
5. Build `AppContext`, apply the saved or system theme, construct the shell view model and main window, and show the window.
6. Install the global `sys.excepthook`, which logs the traceback and shows a user-safe dialog.
7. On exit, release the mutex and remove Qt logging handlers cleanly.

`--smoke-test` runs the same path, verifies the window is visible, and exits automatically. No database, backup, or business file is created.

### 16.4 Configuration model

`AppConfig` is a frozen, slotted dataclass with explicit validation rather than a framework schema. It contains the schema version, currency code/symbol/decimal places/grouping, theme (`system`, `light`, `dark`), and log level. Application name and version are read-only properties sourced from `constants.py`.

The file is written with `tempfile.mkstemp` in the target directory, `fsync`, and `os.replace`, so a crash cannot leave a truncated configuration. Invalid files are moved aside rather than deleted. Pydantic remains installed for later application-boundary validation but is not used for this small, fixed configuration shape.

### 16.5 Logging and error handling

Logging uses the standard library with a `RotatingFileHandler` (5 MB × 5) and a formatter carrying timestamp, level, logger, and correlation ID. Correlation IDs are generated per startup/action and propagated through a context filter. Console output is development-only. `AppError` subclasses separate configuration, startup, and unexpected failures; user dialogs show a safe message plus a correlation ID, while technical detail stays in the log. Logs contain no business or personal payloads in Phase 1.

### 16.6 Theme system

Design tokens (`app/ui/themes/tokens.py`) define the green-based light palette, the dark palette, spacing, radii, and typography. `qss.py` renders QSS from those tokens with `string.Template`, and `ThemeManager` applies it at runtime, follows the Windows system colour scheme when the preference is `system`, and synchronises `QPalette` so native dialogs match. The preference is persisted through `ConfigService`. No widget hard-codes a colour outside the token module.

### 16.7 INR formatting

`app/domain/value_objects/currency.py` defines an immutable `Currency` descriptor and the `INR` default (code `INR`, symbol `₹`, 2 decimal places, Indian grouping). `app/core/formatting.py` accepts `Decimal`, `int`, or a numeric string, rejects `float` and `bool`, rejects non-finite values, rounds with `ROUND_HALF_UP`, and applies Indian grouping (last three digits, then groups of two). Examples verified by tests:

```text
Decimal("1250.50")    -> ₹1,250.50
Decimal("125000.50")  -> ₹1,25,000.50
Decimal("1000000")    -> ₹10,00,000.00
Decimal("-1000000")   -> -₹10,00,000.00
```

Formatting is display-only and lives outside domain calculations. All monetary inputs to formatting are exact.

### 16.8 Verification performed

- `ruff check app tests` — all checks passed.
- `pytest` — 147 passed.
- `python -m app.main --smoke-test` — exit code 0; log contains startup, window shown, and clean shutdown with no errors or warnings beyond environment notes.
- Both themes verified by pixel-sampling the rendered window against token values, not by visual inspection alone.
- Sidebar contains all 11 planned navigation entries; navigation changes the stacked content page; theme choice survives a restart.
- The test suite asserts that no database file, SQLAlchemy model, or Alembic directory exists.

### 16.9 Phase 2 seam

Phase 2 can add `app/infrastructure/database`, ORM modules, Alembic, `UnitOfWork`, and integrity checks without changing the shell. The composition root already loads configuration and resolves paths before any UI is built, so engine construction and migration checks can be inserted at step 3–4 of the startup sequence. `AppConfig` is frozen and versioned, so schema-adjacent settings (data folder, schema revision) extend it cleanly. The currency documentation was reconciled on 2026-11-13: `BLUEPRINT.md` and `DATABASE_SCHEMA.md` now specify INR, matching the Phase 1 implementation.

## 17. Phase 2 implementation record (2026-11-13)

This section records the database foundation actually built and verified in
Phase 2. It supplements the target architecture above and does not approve any
business table.

### 17.1 Implemented scope

- SQLAlchemy 2 engine, session factory, and connection lifecycle.
- SQLite PRAGMA profile applied on every connection, with verification.
- Explicit-commit `UnitOfWork` and a minimal typed repository base.
- Programmatic Alembic configuration, baseline revision, history and status.
- Injected absolute database path with no default and no implicit creation.
- Startup identity/migration checks with no automatic upgrade.
- Read-only health diagnostics and optional full integrity check.
- Integer-paise money value object and conversion utilities.
- Headless migration CLI at `python -m app.tools.migrate`.

No business tables, seeders, sample records, folder-selection wizard, backup
UI, authentication, or business workflow is part of this phase.

### 17.2 Implemented structure

```text
alembic.ini                       # Script location only; URL is injected at runtime
migrations/
├── env.py                        # Programmatic URL/connection, batch mode
├── script.py.mako
└── versions/
    └── 0001_baseline.py          # Identity PRAGMAs only; no application tables
app/
├── app_context.py                # Opens/verifies optional configured database
├── domain/value_objects/money.py # INR integer-paise value object
├── infrastructure/database/
│   ├── base.py                   # Declarative Base, naming convention, identity constants
│   ├── config.py                 # DatabaseConfig: absolute path, parent, WAL/SHM helpers
│   ├── engine.py                 # Engine factory, PRAGMAs, Database lifecycle
│   ├── errors.py                 # Driver error classification and safe messages
│   ├── health.py                 # Diagnostics and integrity checks
│   ├── migrations.py             # Alembic manager, status, startup policy
│   ├── repository.py             # Minimal generic repository
│   └── session.py                # Explicit-commit UnitOfWork
└── tools/migrate.py              # init/upgrade/downgrade/status/history/check CLI
```

`app/infrastructure` may import the domain, SQLAlchemy, Alembic, and the
standard library. It must not import Qt or `app.ui` (enforced by
`tests/test_architecture.py`). The domain remains free of database, framework,
and IO imports.

### 17.3 Connection lifecycle

- `DatabaseConfig` requires an absolute path and an already-existing parent
  folder. There is no default database path anywhere in the codebase.
- `create_sqlite_engine` builds a `QueuePool` with `pool_size=2`,
  `max_overflow=0`, `pool_pre_ping=True`, and the configured busy timeout.
- A `connect` event applies and then verifies the PRAGMA profile on every new
  connection: foreign keys on, WAL active, `synchronous=FULL`,
  `wal_autocheckpoint=1000`, `temp_store=MEMORY`, `trusted_schema=OFF`.
- `Database.verify_accessible()` requires an existing file and runs `SELECT 1`.
  It never creates the file.
- `Database.shutdown()` runs a best-effort passive WAL checkpoint, disposes the
  engine, and is idempotent. `AppContext.close()` is called from the entry
  point's `finally` block.

### 17.4 Session and transaction strategy

`Database.unit_of_work()` returns a `UnitOfWork`. The session is created lazily,
always closes, and never commits implicitly. A missing `commit()` rolls back;
an exception rolls back before it propagates. SQLite remains single-writer;
transactions are short and contain no UI, file, or report work.

`Repository[ModelT]` only wraps get/add/delete on the session supplied by the
unit of work. Business repositories arrive with their approved aggregates.

### 17.5 Database location and startup policy

`AppConfig.database_path` is `null` by default. When it is set, startup:

1. Confirms that the drive and parent folder exist and that the folder is
   writable, using a temporary probe file that touches no database.
2. Confirms that the database file exists and accepts a trivial query.
3. Reads `PRAGMA application_id`; `0` or the project value `1195525971`
   (`0x47424753`, "GBGS") is accepted, any other value is refused.
4. Compares the Alembic revision with the application head.
5. Refuses newer, unknown, older, and uninitialized schemas without modifying
   the file. Upgrades are explicit through the CLI until Phase 4 provides a
   verified safety backup.

When `database_path` is `null`, Phase 3 classifies startup as setup-required or
recovery-required and creates no database file. Phase 2's direct startup path is
superseded by the setup/recovery workflow in §18.

### 17.6 Migrations and initial schema

- Alembic is driven programmatically; the URL and, when supplied, the live
  connection are injected through `Config`. The scripts resolve from the
  repository or `GOBINDAS_MIGRATIONS_DIR` when frozen; the current working
  directory is never used.
- `render_as_batch=True` and `compare_type=True` are configured for SQLite.
- `0001_baseline` creates no application tables. It sets
  `PRAGMA application_id = 1195525971` and `PRAGMA user_version = 1`. Alembic's
  `alembic_version` table remains the only table and the sole migration
  authority.
- No `schema_metadata`, `app_settings`, `business_profile`, or `audit_logs`
  table is created because no approved requirement justifies duplicating
  Alembic's revision, the external configuration file, or an undefined audit
  event model.
- `Base.metadata.create_all()` is not used in production code and is rejected
  by an architecture test.
- Downgrade to `base` removes the revision and resets both identity PRAGMAs;
  it is a maintenance action only, never automatic.

### 17.7 Monetary precision

`app/domain/value_objects/money.py` centralizes INR conversion:

- Domain values use `Decimal`; Python `float` and `bool` are rejected.
- Persistence uses signed 64-bit integer paise (100 paise per rupee).
- `decimal_to_minor` rounds once with `ROUND_HALF_UP` at a defined boundary.
- `decimal_to_minor_exact` rejects any value that is not exactly representable.
- `minor_to_decimal` and `Money` round-trip without binary floating point.
- Range checks guard the signed 64-bit storage limits, and negative values are
  allowed only where the caller permits them.

Phase 2 creates no monetary columns; these utilities are the mandatory boundary
for future accounting, sales, purchase, and inventory modules.

### 17.8 Health diagnostics

`DatabaseDiagnostics.check()` never deletes, recreates, or repairs a file and
never raises for an expected database failure. It reports: healthy, missing
database, unavailable path, permission denied, corrupt, locked, wrong database,
foreign keys disabled, integrity error, migration required, migration failed,
and unknown error. It reports file/WAL/SHM sizes, SQLite version, application
and user version, and migration status.

`quick_check` and `foreign_key_check` are cheap reusable calls. Full
`integrity_check` is opt-in (`full=True` or `migrate check --full`) because it
scans the whole file; normal startup does not run it.

### 17.9 Verification performed

- `ruff check app tests` — all checks passed.
- `pytest` — 239 passed.
- Fresh temporary database: `init`, `status`, `upgrade`, `history`, and
  `check --full` all succeeded; the full check reported healthy with
  `quick_check`, `foreign_key_check`, and `integrity_check` all `ok`.
- Foreign-key violations are rejected by SQLite, and valid references commit.
- Commit, no-commit rollback, exception rollback, and session cleanup are
  tested against a real temporary database.
- Startup tests cover: no configured database, a healthy configured database,
  a missing configured database, a newer revision, and an uninitialized file.
- Real startup with no database still produces no `.db`, `.db-wal`, or `.db-shm`
  file and remains green under the Phase 1 shell tests.

### 17.10 Known limitations and later-phase seams

- The Phase 3 setup wizard now supplies the user-facing location flow; database
  relocation remains out of scope until Phase 4.
- No automatic upgrade and no safety backup before migration yet (Phase 4).
- No business tables, repositories, or accounting workflows yet.
- Encryption at rest remains deferred (Q-18); SQLite files are unencrypted.
- `-wal` and `-shm` files are runtime artifacts and must never be treated as
  backups. Future backups continue to require the SQLite Online Backup API.
- The About surface does not yet display the schema revision; startup logs do.
  A UI status surface can consume `DatabaseDiagnostics` when the shell gains a
  maintenance/settings area.

## 18. Phase 3 implementation record (2026-11-14)

This section records the first-launch setup and database-location workflow
actually built and verified in Phase 3. It reuses the Phase 2 database contract
and adds no business table, backup feature, authentication, or business profile.

### 18.1 Implemented scope

- Native PySide6 setup wizard with seven pages: welcome, location, validation,
  directory review, confirmation, initialization progress, and completion.
- Native folder picker; the selected absolute path is always displayed.
- Read-only location validation before any directory or file is created.
- Additive scaffolding of the approved data-root layout.
- Database creation through `MigrationManager.create_database()` and safe
  adoption of an existing healthy database.
- Full health verification before the location is saved.
- Atomic `data_root` + `database_path` persistence in the existing
  `%APPDATA%\GobindasBMS\config.json`.
- Startup classification and a blocking recovery workflow.
- Tests for validation, scaffolding, initialization, persistence, startup, UI,
  recovery, INR preservation, and Phase 1/2 regressions.

### 18.2 Startup lifecycle

`StartupService.assess()` loads the configuration with `load_with_status()` and
returns exactly one of:

| Mode | Condition | Application action |
| --- | --- | --- |
| `SETUP_REQUIRED` | No `data_root` and no `database_path` | Show the setup wizard; the main window is not created |
| `RECOVERY_REQUIRED` | Corrupt/incomplete config, invalid location, missing drive/folder/database, permission failure, identity mismatch, or unsupported revision | Show the blocking recovery dialog |
| `READY` | Configured drive, folder, file, identity, revision, and health all pass | Open the verified database and show the main window |

`--smoke-test` never opens a window. It exits `0` when setup is required (with an
explicit log line), exits `1` for every recovery condition, and otherwise opens
the verified shell and quits automatically.

Startup never creates a database, directory, or configuration file while
classifying the environment. A missing drive is detected before any attempt to
open SQLite, and the saved paths remain untouched.

### 18.3 Setup wizard responsibilities

`app/ui/dialogs/setup_wizard.py` is presentation and orchestration only:

- It collects the root folder and exposes the seven pages in a
  `QStackedWidget` inside a custom `QDialog`; it is not a browser page and does
  not use `QWizard`.
- Back is hidden on the welcome and progress pages. The confirmation page
  requires an explicit checkbox before initialization.
- The validation page displays every check with pass, info, warning, or error
  styling and blocks continuation on any error.
- The review page lists the exact folders and database file that will be
  created.
- Initialization runs in a `QThread` with a dedicated worker so the GUI thread
  stays responsive. Progress messages are delivered through Qt signals.
- Failure returns to the progress page with the user-safe message and a
  "Choose another folder" action; it does not silently retry.
- Cancellation before initialization changes nothing. Closing during
  initialization requests interruption and the service cleans up only empty
  directories created by the failed attempt.
- The completed wizard hands back a `SetupResult` that owns the open, verified
  `Database`; the composition root adopts that same connection rather than
  reopening the file.

`SetupViewModel` contains QtCore-only state and formatting. It does not import
`QtWidgets`, and no database or filesystem policy lives in the widget.

### 18.4 Folder and drive validation

`DataLocationValidator` in `app/infrastructure/filesystem/validation.py` returns
a tuple of named checks and never mutates the user's files except for one
uniquely named temporary probe file.

Checks, in order:

1. Path syntax is valid and non-empty.
2. The path is absolute.
3. The path is not UNC and the drive is not a mapped network drive.
4. `DataRootLayout` accepts the path as a named directory (the drive root alone
   is refused).
5. The drive exists.
6. The drive type is fixed, removable, or unknown-with-warning; optical,
   network, and unavailable drives are refused.
7. Protected Windows/system/program folders are refused.
8. The path is outside the installation directory (executable directory,
   PyInstaller bundle directory, and repository root).
9. An existing path is a readable directory, or the nearest existing ancestor
   is readable and the missing folder can be created.
10. A probe file can be created, written, flushed, closed, removed, and verified.
11. Free space can be inspected and is at least `MINIMUM_FREE_SPACE_BYTES`.
12. A very long path produces a warning, not a hard failure.
13. An existing database file is reported as a warning (verify and connect); a
    folder at the database path is an error.

A removable drive is valid but produces a warning that it must remain connected
whenever the application runs. The validator does not assume that a different
drive letter means a different physical disk.

### 18.5 Directory scaffolding

`DataRootScaffolder` creates the layout documented in BACKUP_STRATEGY.md §2:

```text
<data_root>/
├── Database/
├── Backups/{Automatic,Manual,Safety}/
├── Attachments/
└── Exports/{PDF,Excel}/
```

Creation is additive and sequential. An existing directory is accepted; a file
in a required location is a hard error and is never deleted. On failure, the
scaffolder removes only empty directories that this attempt created, deepest
first, and keeps any directory that now contains anything. Pre-existing
directories are never removed.

### 18.6 Database initialization and adoption

`SetupService.initialize()`:

1. Revalidates the chosen root and obtains the fixed layout.
2. Scaffolds the folders.
3. If `<root>/Database/BusinessManagement.db` exists, opens it through the
   Phase 2 startup verification path. Only a healthy Gobindas database at the
   expected schema revision is adopted; corrupt, unknown, uninitialized, and
   newer databases are refused with an explanation.
4. If it does not exist, constructs an absolute `DatabaseConfig` and calls
   `MigrationManager.create_database()`. No `Base.metadata.create_all()` and no
   manual Alembic revision insert is used.
5. Runs `DatabaseDiagnostics.check(full=True)` and requires a healthy report.
6. Returns the open `Database`, the migration status, the health report, and the
   scaffold result.

Any failure closes the database and cleans up only the empty directories created
by this attempt. An existing database is never overwritten, truncated, migrated,
or replaced.

### 18.7 Configuration persistence

- `AppConfig` gains an optional absolute `data_root`; `database_path` remains the
  explicit absolute SQLite path. A legacy config with only `database_path` is
  still valid and is treated as a legacy location.
- When both are present, `database_path` must be inside `data_root`; this is
  validated on construction, load, and save.
- The existing `ConfigService` writes the complete configuration to a temporary
  file in the same directory, flushes and fsyncs it, validates it, and replaces
  the original atomically.
- The updated configuration is built from the user's existing configuration, so
  INR, theme, logging, and schema settings are preserved. The INR assertions are
  covered by regression tests.
- Persistence happens only after database creation and verification. The saved
  file is re-read and both paths and preserved fields are compared to the result.
- If persistence fails, `SetupPersistenceError` carries the still-open verified
  database so the user can retry saving without repeating database work. The
  database is not deleted.
- The configuration schema version remains `1`; `data_root` is an optional,
  backward-compatible field, and unknown future keys are still ignored on load.

`ConfigService.load_with_status()` distinguishes `MISSING`, `LOADED`, and
`RECOVERED`. `load()` keeps its Phase 1 behavior: an invalid file is moved to
`config.corrupt-<timestamp>.json` and defaults are returned. The original content
is preserved for diagnosis and is never silently discarded.

### 18.8 Recovery and missing-drive behavior

`RecoveryDialog` is a blocking native dialog that reports the specific reason
and the saved database path, data root, and quarantine path (where applicable).
It offers exactly four choices:

| Choice | Behavior |
| --- | --- |
| Retry | Re-runs startup assessment; succeeds if the drive or permission problem has been fixed |
| Locate existing data... | Native folder picker; `attach_existing()` validates identity, revision, and health before accepting and never creates a file |
| Start a new setup... | Runs the same setup wizard with an explanation of the consequences |
| Exit | Closes without changing configuration or creating anything |

There is no "restore backup" action in Phase 3, because restore belongs to
Phase 4 and must not be faked. No recovery path creates a database on `C:`,
changes the saved path silently, or opens an empty replacement database.

### 18.9 Implemented structure

```text
app/
├── core/
│   ├── config.py                       # data_root, load_with_status, atomic save
│   ├── constants.py                    # layout names and minimum free space
│   └── exceptions.py                   # SetupError
├── infrastructure/filesystem/
│   ├── drives.py                       # Windows drive type/capacity/free space
│   ├── layout.py                       # DataRootLayout and required directories
│   ├── scaffold.py                     # Additive creation and safe cleanup
│   └── validation.py                   # Read-only location validation
├── services/
│   ├── setup_service.py                # Validate → scaffold → init/adopt → verify → persist
│   └── startup_service.py              # Setup/recovery/ready classification
└── ui/
    ├── dialogs/setup_wizard.py         # Seven-page wizard and worker thread
    ├── dialogs/recovery_dialog.py      # Blocking recovery choices
    └── viewmodels/setup_viewmodel.py   # QtCore-only wizard state
```

`app/services` and `app/infrastructure/filesystem` are enforced as Qt-free by
`tests/test_architecture.py`. The worker imports no widgets; only the dialog
touches Qt.

### 18.10 Verification performed

- `ruff check app tests` — all checks passed.
- `pytest` — 341 passed (239 Phase 2 tests plus 102 Phase 3 tests and
  regression coverage).
- Startup tests launch the real entry point with isolated `APPDATA` and
  `LOCALAPPDATA`: clean profile → setup-required smoke exit `0`; corrupt config →
  exit `1` with `config.corrupt-*.json`; newer schema → exit `1` with a refusal
  message; uninitialized file → exit `1`; healthy configured database → shell
  opens and the smoke test exits cleanly.
- Wizard tests cover navigation, validation gating, review contents, explicit
  confirmation, successful initialization, worker failure, cancellation, and
  hand-off of the open database.
- Setup-service tests cover initialization, baseline revision, identity, health,
  existing healthy adoption, unknown/corrupt/uninitialized/newer refusal, no
  overwrite, persistence failure recovery, and INR preservation.
- Validation tests cover valid fixed and removable drives, invalid/relative/
  missing-parent/non-directory/read-only/unwritable/UNC/installation/protected
  paths, space reporting, and low-space failure with mocked drive APIs.
- Scaffold tests cover the exact directory set, existing folders and files,
  partial failure, and safe cleanup.
- Configuration tests cover absolute paths, data root, legacy configs, null
  fields, outside-root rejection, atomic writes, re-read verification, corrupt
  recovery, and INR preservation.
- The full prior suite remains green.

### 18.11 Known limitations and Phase 4 seams

- Backup, restore, retention, scheduled runs, and relocation are not implemented
  (Phase 4).
- An existing healthy database at a future schema revision is refused rather
  than upgraded; automatic upgrade waits for the Phase 4 safety-backup gate.
- Business profile fields and tables remain unapproved and unimplemented.
- Sync-client folders (OneDrive/Dropbox) are not specifically detected; the
  documented policy is to keep the live database out of live sync. This can be
  strengthened in a later hardening phase.
- The recovery dialog intentionally has no restore action until Phase 4 can
  verify and stage a restore safely.

## 19. Phase 5 implementation record (2026-11-17)

This section records the UI/UX refinement actually built in Phase 5. It does not
change the Phase 1–4 data-protection contract: no backup, restore, relocation,
scheduler, migration, or database-schema logic was modified. No business module,
seed data, authentication, or new database table was added.

### 19.1 Scope and layering

Phase 5 is confined to the presentation layer plus two new constants for feedback
durations. The dependency rules in §4.1 remain in force. ViewModels still import
only QtCore; the new backup signals (`read_failed`, `task_status`) carry display
strings and do not expose services or widgets to the view.

New presentation modules:

```text
app/ui/components/controls.py   # make_button, set_dialog_size, DetailCard
app/ui/components/feedback.py   # StatusBadge, apply_status, EmptyState, Toast, show_toast
tests/test_phase05_ui.py        # Phase 5 programmatic UI tests
```

`QSettings` is used only for window geometry, window state, and the current
navigation key. It is separate from `AppConfig`/`config.json`, so the
configuration schema and its atomic-write behaviour are unchanged.

### 19.2 Theme and QSS architecture

`app/ui/themes/tokens.py` defines frozen `Palette`, `Metrics`, and `ChartPalette`
dataclasses plus the light/dark palettes. `app/ui/themes/qss.py` builds one QSS
template from those tokens with `string.Template`; every positive length is
emitted with a `px` suffix. Tests assert that generated sheets contain no `$`
placeholders, no `pxpx`, and no unitless positive lengths for common length
properties. `ThemeManager` continues to apply the sheet at runtime and now also
synchronises the Qt palette so native dialogs follow the active theme.

### 19.3 Shell changes

`MainWindow` now:

- accepts an injectable `QSettings` instance for isolated tests;
- restores `window/geometry`, `window/state`, and `navigation/current`, with a
  connected-screen check before restoring saved geometry;
- saves the session on an accepted close, after the existing backup shutdown
  guard allows the close;
- exposes `F5` via `QShortcut(QKeySequence.StandardKey.Refresh, self)` and calls
  `refresh()` on the active view when that hook exists;
- adds an accessible status bar and accessible database, backup, currency,
  local-only, and version labels;
- shows the latest verified backup time from `BackupSnapshot` with a tooltip
  naming the backup file;
- uses token-driven default/minimum window sizes and named feedback timeouts.

The sidebar spacing now uses `METRICS.space_1`. The icon-rail collapse target in
UI_UX_BLUEPRINT.md §2.2 remains unimplemented because no approved icon set exists.

### 19.4 Dashboard and backup view changes

`HomeView` and `BackupView` now use `QScrollArea` with a resizable content widget
and token margins, so long paths and wrapped text remain reachable without
horizontal page scrolling. `HomeView` reports only verified environment facts and
uses `StatusBadge`, `DetailCard`, and `EmptyState`; it renders no fake KPI or chart
data.

`BackupView` now uses `StatusBadge`, `DetailCard`, `make_button`, and `show_toast`.
It has an explicit empty state, an unavailable state, a busy state that disables
the manual-backup and refresh controls, an accessible progress bar, an accessible
history tree with tooltips, and destructive-action isolation in the tab order.
Only a selected `VERIFIED` record enables **Restore selected backup**. A failed
history read emits the new `BackupViewModel.read_failed` signal and is shown as a
warning badge instead of a modal dialog; actual operation failures still show a
modal error. Task Scheduler status is fetched through the new asynchronous
`load_task_status()`/`task_status` path so the settings dialog does not block on
a scheduler query.

### 19.5 Dialog changes

- **Setup wizard:** token-size clamping, labeled path field with buddy, explicit
  tree accessible name, full paths in tooltips, consistent buttons/tab order, and
  a focused recovery action when initialization or persistence fails.
- **Recovery:** token sizing, `DetailCard` for preserved paths, Retry focused as
  the default action, Exit separated in tab order with an explicit accessible
  name, and unchanged four-action semantics.
- **Restore confirmation:** token sizing, `DetailCard` for the selected backup,
  Cancel as default with a named destructive action, and unchanged explicit
  confirmation requirement.
- **Backup settings:** token sizing, named fields, `Ctrl+S` on Save schedule,
  `set_task_status()` for asynchronous scheduler status, and unchanged settings
  validation/persistence path.
- **Fatal error:** a selectable correlation reference and a **Copy reference**
  button; technical detail remains behind **Show details**.

`QTreeWidgetItem` has no `setAccessibleName()` in the pinned PySide6 build, so
tree-level accessible names/descriptions and item tooltips are used instead.

### 19.6 Verification performed

- `./.venv/Scripts/python.exe -m ruff check app tests` — all checks passed.
- `./.venv/Scripts/python.exe -m pytest -q tests/test_phase05_ui.py` — 20 passed.
- `./.venv/Scripts/python.exe -m pytest -q` — 448 passed.
- Programmatic offscreen smoke runs with `QT_SCALE_FACTOR=1`, `1.25`, and `1.5`
  exited `0` and logged `Main window shown` with no critical errors or tracebacks.
  These are construction/smoke checks, not visual DPI verification.
- Real Windows visual/DPI walkthroughs and real Windows backup integration drills
  were not executed in this environment and are documented as outstanding in the
  Phase 5 report.

### 19.7 Phase 6 boundary

Phase 5 stops at presentation polish. Authentication, roles, users, business
master data, and all Phase 6+ features remain unstarted pending owner review and
explicit authorization.
