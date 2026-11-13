# ARCHITECTURE — Gobindas Graphics Business Management System

| Field | Value |
| --- | --- |
| Document | ARCHITECTURE.md |
| Version | 1.0 |
| Date | 2026-11-12 |
| Status | Draft for review |
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
- **Status:** Proposed.
- **Decision:** Migrations live in `migrations/` and are shipped inside the frozen app. On startup, the app reads the current revision, backs up if an upgrade is required, then upgrades to head. The same migration command is available as a CLI maintenance action.
- **Rationale:** Desktop installs cannot rely on a developer running migrations manually; schema and app versions must move together.
- **Consequences:** Migration scripts must be path-independent (programmatic `Config`, absolute script location via `sys._MEIPASS` when frozen). Failed upgrades abort startup and preserve the backup.

### ADR-008 — SQLite connection profile
- **Status:** Proposed.
- **Decision:** Every connection sets `PRAGMA foreign_keys=ON`, `busy_timeout=5000`, `journal_mode=WAL`, `synchronous=FULL`, `wal_autocheckpoint=1000`, `temp_store=MEMORY`. `foreign_keys` must be enabled per connection via an event hook.
- **Rationale:** Referential integrity, crash safety, concurrent readers, short writer waits.
- **Trade-off:** `synchronous=FULL` is slower than `NORMAL`; for a financial desktop app, durability wins. Re-evaluate with measurements if write latency is unacceptable.
- **Consequences:** WAL sidecar files (`-wal`, `-shm`) exist while running; backups must use the Online Backup API, never a file copy.

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
- **Status:** Proposed.
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
2. Load/validate config or run the setup wizard.
3. Verify database location.
4. Build the engine/session factory and `UnitOfWork` factory.
5. Construct services and the module registry.
6. Create ViewModels and the main window.
7. Start the Qt event loop.

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

## 8. Lifecycle

### 8.1 GUI startup

| Step | Action | Failure behaviour |
| --- | --- | --- |
| 1 | Install excepthook, start log | Continue with stderr fallback |
| 2 | Single-instance mutex | Focus existing instance or exit |
| 3 | Load config | Missing → setup wizard; corrupt → repair dialog |
| 4 | Validate data folder | Show blocking error with Retry/Locate/Exit |
| 5 | Open engine, check integrity (fast) | Offer recovery/restore; do not auto-create |
| 6 | Check Alembic revision | Higher than app → refuse; lower → backup + upgrade |
| 7 | Check missed backup | Run catch-up asynchronously, non-blocking |
| 8 | Build services/viewmodels/window | Fatal error dialog with log ID |
| 9 | Load dashboard | Show skeleton/progress; errors contained |
| 10 | Event loop | — |

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
