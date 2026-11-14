# Phase 2 Completion Report

| Field | Value |
| --- | --- |
| Phase | Phase 2 — SQLite Database Foundation and Migration System |
| Project | Gobindas Graphics Business Management System |
| Report date | 2026-11-14 |
| Status | Complete; awaiting owner review and authorization for Phase 3 |
| Report path | `Reports/PHASE_02_REPORT.md` |

## 1. Phase name and number

Phase 2 — SQLite Database Foundation and Migration System.

This phase establishes the database layer that later business modules will use:
SQLite connection management, SQLAlchemy 2 integration, explicit transaction
boundaries, Alembic migrations, database location abstraction, health
diagnostics, and the INR integer-paise storage boundary. It deliberately creates
no business tables and implements no business workflow.

## 2. Completion date

Implementation and the first full verification run were completed on
2026-11-13. The final verification sequence and this report were produced on
2026-11-14.

All commands in §12–§14 were executed on the project machine (Windows 64-bit)
from the repository root `D:\Development\Gobindas Graphics` using the project
virtual environment (CPython 3.14.6).

## 3. Summary of implementation

- Added a typed `DatabaseConfig` that requires an injected absolute path and an
  existing parent folder. There is no default database location and no C:
  fallback anywhere in the codebase.
- Added the SQLAlchemy 2 engine factory with the approved SQLite PRAGMA profile,
  a bounded connection pool, busy-timeout handling, and per-connection
  verification of foreign-key and WAL settings.
- Added the `Database` lifecycle object: engine ownership, session factory,
  accessibility verification, best-effort WAL checkpoint, idempotent shutdown,
  and context-manager support.
- Added an explicit-commit `UnitOfWork`. Leaving the scope without `commit()`
  rolls back; exceptions roll back before propagating; the session always closes.
- Added a minimal typed repository base that receives the unit-of-work session.
- Added programmatic Alembic control with status, history, upgrade, downgrade,
  and explicit database creation against any configured absolute path.
- Added the reversible `0001_baseline` migration. It creates no application
  tables; it sets the SQLite file-identity PRAGMAs only.
- Added a startup verification policy that refuses newer, unknown, older, and
  uninitialized schemas without modifying the file. Automatic upgrade remains a
  Phase 4 capability behind the safety-backup gate.
- Added read-only health diagnostics with quick check, full integrity check,
  foreign-key check, file/WAL/SHM information, identity checks, write-capability
  probing, and migration-state reporting.
- Added the headless `python -m app.tools.migrate` maintenance CLI.
- Added the INR `Money` value object and centralized Decimal-to-integer-paise
  conversion utilities, with rounding, precision, sign, and range rules.
- Wired an optional configured database into the composition root and the
  application shutdown path without changing Phase 1 startup behavior when no
  database is configured.
- Updated architecture, schema, security, backup, and roadmap documentation.
- Added 92 tests (80 in six new database/money modules plus 12 additional tests
  in existing modules), for a total suite of 239 passing tests.

## 4. Files created

### Root files

- `alembic.ini` — Alembic script location and logging; the database URL is not
  configured here.
- `Reports/PHASE_02_REPORT.md` (this report).

### Application package

- `app/domain/value_objects/money.py` — INR value object and paise conversion.
- `app/infrastructure/__init__.py` — infrastructure package boundary note.
- `app/infrastructure/database/__init__.py` — public database-layer exports.
- `app/infrastructure/database/base.py` — declarative base, naming convention,
  file-identity constants.
- `app/infrastructure/database/config.py` — `DatabaseConfig`, path/parent/file
  validation, URL and WAL/SHM helpers, write probe.
- `app/infrastructure/database/engine.py` — engine factory, PRAGMA profile,
  `Database` lifecycle.
- `app/infrastructure/database/errors.py` — driver error classification and
  user-safe messages.
- `app/infrastructure/database/health.py` — diagnostics, integrity checks, and
  health report types.
- `app/infrastructure/database/migrations.py` — Alembic manager, migration
  state policy, startup verification.
- `app/infrastructure/database/repository.py` — generic repository foundation.
- `app/infrastructure/database/session.py` — explicit-commit `UnitOfWork`.
- `app/tools/__init__.py` — headless tools package boundary note.
- `app/tools/migrate.py` — init/upgrade/downgrade/status/history/check CLI.

### Migration infrastructure

- `migrations/env.py` — programmatic URL/connection injection, batch mode,
  type comparison, metadata registration.
- `migrations/script.py.mako` — migration script template.
- `migrations/versions/0001_baseline.py` — reversible baseline identity
  migration.

### Tests

- `tests/test_database_config.py` — 11 tests: path, timeout, URL, sidecar
  paths, parent validation, write probe, absent/existing file policy.
- `tests/test_database_engine.py` — 9 tests: PRAGMAs, busy timeout, SQLite
  version, accessibility, shutdown, context manager, commit, foreign keys,
  bounded pool.
- `tests/test_database_health.py` — 13 tests: healthy, full check, missing
  file/folder, wrong identity, uninitialized schema, corruption, read-only
  behavior, quick check, foreign-key check, lock failure, identity boundary.
- `tests/test_database_migrations.py` — 19 tests: policy matrix, baseline
  contents, creation, status, history, refusal rules, upgrade, failed upgrade,
  naming convention, downgrade, startup refusal/acceptance.
- `tests/test_database_session.py` — 7 tests: commit, no-commit rollback,
  exception rollback, close, commit-after-close, idempotent rollback, repository
  delegation.
- `tests/test_money.py` — 21 tests: Decimal/int/string input, rounding,
  precision rejection, float/bool rejection, NaN/infinity, sign rules, 64-bit
  range, round-trip, currency validation.

### Deliberately not created

No business tables, business repositories, seeders, sample rows, setup wizard,
backup UI, restore UI, scheduler, authentication, business profile, or
accounting module was created. These belong to later phases.

## 5. Files modified

- `app/app_context.py` — opens and verifies an optional configured database,
  exposes it on `AppContext`, and disposes it on close.
- `app/core/config.py` — adds optional `database_path`, absolute-path and
  file-name validation, mapping read, and serialization.
- `app/core/constants.py` — application version raised to `0.2.0`.
- `app/core/paths.py` — clarifies that the database path is not derived from
  machine-local config/log paths.
- `app/domain/__init__.py` — records the Phase 2 money boundary.
- `app/main.py` — logs configured database state and closes the database in the
  entry point's `finally` block.
- `docs/ARCHITECTURE.md` — adds the Phase 2 implementation record (§17):
  connection lifecycle, session/transaction strategy, location policy,
  migrations, monetary precision, diagnostics, verification, limitations.
- `docs/DATABASE_SCHEMA.md` — records the actual Phase 2 tables, the empty
  baseline justification, money storage rules, and migration/backup
  consequences.
- `docs/SECURITY_AND_DATA_PROTECTION.md` — records database permissions,
  connection safety, identity checks, integrity checking, and corruption
  handling.
- `docs/BACKUP_STRATEGY.md` — records WAL/sidecar handling, Online Backup API
  requirements, safe shutdown, and the Phase 2 migration refusal policy.
- `docs/DEVELOPMENT_ROADMAP.md` — marks Phase 2 complete, checks its
  deliverables/DoD, records verification, and lists Phase 3 dependencies.
- `pyproject.toml` — project version `0.2.0`.
- `requirements.txt` — dependency lock comment updated to Phase 2 (versions
  unchanged).
- `README.md` — status, scope, requirements, structure, and next-phase sections
  refreshed for Phase 2.
- `tests/conftest.py` — adds temporary database folder/config/initialized
  database fixtures.
- `tests/test_architecture.py` — adds infrastructure/tools import-boundary and
  implicit-`create_all` checks.
- `tests/test_config.py` — adds `database_path` validation and round-trip tests.
- `tests/test_startup.py` — adds configured-database startup, missing-database
  refusal, newer-schema refusal, and uninitialized-schema refusal tests.

No Phase 1 file was deleted. No previous report was overwritten.

## 6. Dependencies added and reasons

No new runtime or development packages were added in Phase 2.

| Package | Version | Phase 2 role |
| --- | --- | --- |
| SQLAlchemy | 2.1.8 | Engine, session, unit of work, repository base |
| Alembic | 1.20.1 | Migration scripts, status, history, upgrade/downgrade |
| pytest | 9.2.0 | Database, transaction, migration, health, and money tests |
| ruff | 0.17.5 | Lint gate |

SQLAlchemy and Alembic were already installed, pinned, and import-tested in
Phase 1 as part of the approved stack; Phase 2 is the first phase that exercises
them. `requirements.txt` versions are unchanged. The project version moved from
`0.1.0` to `0.2.0` in `pyproject.toml`, `app/core/constants.py`, and the package
metadata.

## 7. Database architecture

### Layering and dependency direction

```text
app/main.py                     composition root / entry point
app/app_context.py              explicit dependency wiring
        │
        ├── app/core              configuration, paths, logging, exceptions
        ├── app/infrastructure    SQLAlchemy, Alembic, SQLite adapters
        └── app/tools             headless migration/health CLI

app/domain                      framework-free value objects (Money)
```

Infrastructure may import the domain and the standard/SQLAlchemy/Alembic
libraries. It must not import Qt or `app.ui`. The domain imports no Qt,
SQLAlchemy, Alembic, or `sqlite3`. `app/core` imports no Qt or database library.
These boundaries are enforced by `tests/test_architecture.py`.

Views and view models never open a database connection. Future business modules
must reach persistence through application services, a `UnitOfWork`, and
repositories.

### Components

| Component | Responsibility |
| --- | --- |
| `DatabaseConfig` | Absolute path, busy timeout, parent/file validation, write probe, WAL/SHM paths, URL construction |
| `create_sqlite_engine` | Engine with bounded pool, busy timeout, `connect` event applying the PRAGMA profile |
| `Database` | Engine ownership, session factory, accessibility check, checkpoint, idempotent shutdown |
| `UnitOfWork` | Lazy session, explicit commit, rollback on exit/exception, reliable close |
| `Repository[ModelT]` | Minimal typed get/add/delete over the unit-of-work session |
| `MigrationManager` | Programmatic Alembic status, history, create, upgrade, downgrade |
| `DatabaseDiagnostics` | Read-only health, identity, integrity, file information, migration state |
| `AppContext` | Optional database construction, startup verification, shutdown |
| `app.tools.migrate` | Headless maintenance entry point |

### Database location abstraction

- `AppConfig.database_path` is `None` by default. It accepts only an absolute
  path that names a file.
- `DatabaseConfig` is injected; it never derives a path from the project
  directory or the current working directory.
- A missing drive, missing parent folder, non-directory parent, missing file, or
  existing file (when creating) raises an application-level
  `DatabaseUnavailableError` with a safe user message.
- A database file is created only by the explicit
  `MigrationManager.create_database()` call, used by the CLI or a future setup
  wizard. Startup never creates a database.
- There is no default path, no C: fallback, and no silent switch to another
  file.

### Startup policy

When `database_path` is `null`, startup is unchanged from Phase 1 and creates no
database files. When it is set, startup:

1. Confirms the drive, parent folder, and folder writability using a temporary
   probe file that touches no database.
2. Confirms the database file exists and accepts `SELECT 1`.
3. Reads `PRAGMA application_id`; `0` or `1195525971` (`0x47424753`, "GBGS") is
   accepted, any other value is refused.
4. Compares the Alembic revision with the application head.
5. Refuses newer, unknown, older, and uninitialized schemas without modifying
   the file.

No migration is applied automatically. Upgrades are an explicit maintenance
action through the CLI until Phase 4 can create a verified safety backup first.

## 8. SQLite configuration

### PRAGMA profile

Applied and verified on every new DB-API connection by a SQLAlchemy `connect`
event listener:

| PRAGMA | Value | Reason |
| --- | --- | --- |
| `foreign_keys` | `ON` | Enforce declared references; tested with a violating insert |
| `busy_timeout` | `5000` ms | Bounded wait instead of an immediate "database is locked" |
| `journal_mode` | `WAL` | Better read/write concurrency and crash recovery for a desktop app |
| `synchronous` | `FULL` | Durability is preferred over write speed for business records |
| `wal_autocheckpoint` | `1000` pages | Bounds WAL growth without manual checkpointing |
| `temp_store` | `MEMORY` | Keeps temporary SQLite work in memory |
| `trusted_schema` | `OFF` | Prevents schema-embedded code from running with implicit trust |

The listener reads back `journal_mode` and `foreign_keys` and raises if either
setting did not take effect.

### Connection pool

- `QueuePool` with `pool_size=2`, `max_overflow=0`, `pool_pre_ping=True`.
- `check_same_thread=False` is explicit because a pooled connection may be
  checked out by a short-lived worker thread; sessions themselves are never
  shared between threads.
- `pool_timeout` equals the configured busy timeout.
- The small bound makes a second writer wait rather than multiply connections.
  SQLite remains single-writer by design.

### WAL decision and consequences

WAL was enabled deliberately. It improves concurrency for a GUI that may read
while a short write transaction runs, and it is supported by SQLite's Online
Backup API. The trade-offs are documented:

- While open, the database has `-wal` and `-shm` sidecar files.
- Those sidecars are runtime artifacts, not independent backups. Copying
  `.db`, `.db-wal`, or `.db-shm` separately is not a valid backup.
- `Database.shutdown()` performs a best-effort passive WAL checkpoint before
  disposing the engine, and shutdown is idempotent.
- Phase 4 backups must use the SQLite Online Backup API so WAL content is
  included.

### Error handling

Driver and SQLAlchemy failures are classified as `locked`, `corrupt`,
`permission`, `unavailable`, or `unknown`. The database boundary raises the
application exception hierarchy with a safe user message. Messages never include
SQL or file content.

## 9. Migration implementation

- Alembic is driven programmatically. `alembic.ini` supplies the script location
  and logging only; the database URL is always injected at runtime. Offline mode
  is explicitly unsupported because SQLite migrations run against a real file.
- `migrations/env.py` registers `Base.metadata`, uses `render_as_batch=True` and
  `compare_type=True`, and accepts either an injected connection or a configured
  URL from the CLI.
- The migrations directory is resolved from the package location or
  `GOBINDAS_MIGRATIONS_DIR` when frozen; the current working directory is never
  used.
- `0001_baseline` is reversible. Upgrade sets the file identity; downgrade
  resets `application_id` and `user_version` to 0 and removes the revision row.
- `Base.metadata.create_all()` is never used in production code, and an
  architecture test rejects it.
- The Alembic version table is never edited by hand except by Alembic itself.
  Test-only scripts simulate a newer revision to prove startup refusal.

### CLI

```powershell
.\.venv\Scripts\python.exe -m app.tools.migrate --database "D:\GGBMS\gobindas.db" init
.\.venv\Scripts\python.exe -m app.tools.migrate --database "D:\GGBMS\gobindas.db" status
.\.venv\Scripts\python.exe -m app.tools.migrate --database "D:\GGBMS\gobindas.db" upgrade
.\.venv\Scripts\python.exe -m app.tools.migrate --database "D:\GGBMS\gobindas.db" history
.\.venv\Scripts\python.exe -m app.tools.migrate --database "D:\GGBMS\gobindas.db" downgrade --revision base
.\.venv\Scripts\python.exe -m app.tools.migrate --database "D:\GGBMS\gobindas.db" check --full
```

`init` is the only command that may create a file, and it refuses to overwrite
an existing database. `upgrade`, `downgrade`, `status`, `history`, and `check`
require an existing file. Every command requires an absolute path.

### Migration tests

Fresh initialization, upgrade to head, already-up-to-date re-run, status,
history, safe upgrade of an uninitialized file, failed-upgrade preservation,
downgrade, naming stability, and startup acceptance/refusal are covered in
`tests/test_database_migrations.py` and `tests/test_startup.py`.

## 10. Initial schema and table justification

The baseline database contains exactly one table, created by Alembic:

| Table | Origin | Purpose | Justification |
| --- | --- | --- | --- |
| `alembic_version` | Alembic | Stores the current schema revision | Required by the approved migration tool; authoritative migration state |

No application table exists. Each candidate was considered and deliberately
omitted:

- **No `schema_metadata`**: Alembic already stores the authoritative revision.
  `PRAGMA user_version` is a cheap diagnostic marker, not a second source of
  truth.
- **No `app_settings`**: machine configuration remains in
  `%APPDATA%\GobindasBMS\config.json` per ADR-009. Duplicating it would create
  two sources of truth.
- **No `business_profile`**: the minimum confirmed business identity fields are
  not approved yet.
- **No `audit_logs`**: no approved event model, retention policy, or privacy
  rules exist. A speculative audit system would be misleading.

There are no Phase 2 relationships or business indexes. The only constraints and
indexes are those Alembic creates for `alembic_version`. The file also carries
`application_id = 1195525971` and `user_version = 1` as identity/diagnostic
markers.

## 11. INR and integer-paise implementation

- Default currency: **INR**, symbol **₹**, 2 decimal places, 100 paise per
  rupee.
- Domain calculations use `Decimal`, never binary `float`.
- Persistence uses signed 64-bit integer paise (`INTEGER` storage).
- `decimal_to_minor` performs exactly one `ROUND_HALF_UP` at a defined boundary.
- `decimal_to_minor_exact` rejects any value that is not exactly representable
  instead of rounding implicitly.
- `minor_to_decimal` and `Money` round-trip exactly without floating point.
- `float` and `bool` are rejected at the boundary. NaN and infinity are
  rejected. The signed 64-bit range is enforced.
- Negative amounts are allowed for credit/adjustment flows; callers that cannot
  accept them pass `allow_negative=False`.
- Conversion utilities are centralized in
  `app/domain/value_objects/money.py`.

Phase 2 creates no monetary columns. Future accounting, sales, purchase, and
inventory modules must store integer paise in `INTEGER` columns and must not use
`REAL`, `NUMERIC`, or `DECIMAL` affinity for money.

Examples verified by tests:

| Amount | Stored paise |
| --- | ---: |
| `Decimal("0.50")` | 50 |
| `Decimal("1.00")` | 100 |
| `Decimal("125.50")` | 12550 |
| `Decimal("1250.75")` | 125075 |
| `Decimal("100000.00")` | 10000000 |

## 12. Tests executed

Commands were run from the repository root with the project interpreter:

```powershell
.\.venv\Scripts\python.exe -m ruff check app tests migrations
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest --collect-only -q
.\.venv\Scripts\python.exe -m app.main --smoke-test
.\.venv\Scripts\python.exe -m app.tools.migrate --database <temp-db> init
.\.venv\Scripts\python.exe -m app.tools.migrate --database <temp-db> status
.\.venv\Scripts\python.exe -m app.tools.migrate --database <temp-db> upgrade
.\.venv\Scripts\python.exe -m app.tools.migrate --database <temp-db> history
.\.venv\Scripts\python.exe -m app.tools.migrate --database <temp-db> check --full
.\.venv\Scripts\python.exe -m app.tools.migrate --database <temp-db> downgrade --revision base
.\.venv\Scripts\python.exe -m app.tools.migrate --database <temp-db> upgrade
```

Test coverage by module (239 collected):

| Test module | Tests | Scope |
| --- | ---: | --- |
| `test_architecture.py` | 9 | Import boundaries, no implicit table creation, no `float` in financial modules, compile checks |
| `test_config.py` | 32 | Defaults, INR defaults, validation, database path, atomic save, corruption |
| `test_currency.py` | 20 | Currency value object and INR defaults |
| `test_database_config.py` | 11 | Absolute path, file name, timeout, URL, WAL/SHM paths, parent validation, write probe, file policy |
| `test_database_engine.py` | 9 | PRAGMAs, timeout, version, accessibility, shutdown, context manager, commit, foreign keys, pool bound |
| `test_database_health.py` | 13 | Health states, identity, integrity, corruption, lock, read-only behavior, migration state |
| `test_database_migrations.py` | 19 | Policy, baseline, creation, status, history, upgrade, downgrade, startup policy |
| `test_database_session.py` | 7 | Commit, rollback, exception cleanup, close, repository delegation |
| `test_error_handling.py` | 4 | Excepthook behavior and safe messages |
| `test_formatting.py` | 51 | INR formatting, grouping, precision, invalid input |
| `test_logging.py` | 9 | Handlers, rotation, correlation IDs |
| `test_main_window.py` | 10 | Shell construction, navigation, themes, status bar |
| `test_money.py` | 21 | Decimal/paise conversion, precision, rounding, sign, range, round-trip |
| `test_paths.py` | 9 | APPDATA/LOCALAPPDATA resolution, directory creation, filename safety |
| `test_shell_viewmodel.py` | 4 | Initial state, theme persistence, save failure |
| `test_single_instance.py` | 4 | Mutex acquire/release and second-instance refusal |
| `test_startup.py` | 7 | Real subprocess startup, no database created, configured database, refusal policies |
| **Total** | **239** | |

No tests were skipped, xfailed, or disabled. No fabricated results were used.
Database tests use isolated temporary directories and temporary files; no real
user database is touched.

## 13. Actual test results

Exact results from the final verification run on 2026-11-14:

```text
$ .\.venv\Scripts\python.exe -m ruff check app tests migrations
All checks passed!

$ .\.venv\Scripts\python.exe -m pytest -q
........................................................................ [ 30%]
........................................................................ [ 60%]
........................................................................ [ 90%]
.......................                                                  [100%]
239 passed in 13.97s

$ .\.venv\Scripts\python.exe -m pytest --collect-only -q
239 tests collected in 0.10s

$ .\.venv\Scripts\python.exe -m app.main --smoke-test
exit code 0
```

Fresh temporary database verification:

```text
$ python -m app.tools.migrate --database <temp>\gobindas.db init
state:   up_to_date
current: 0001_baseline
head:    0001_baseline
exit code 0

$ python -m app.tools.migrate --database <temp>\gobindas.db status
state:   up_to_date
current: 0001_baseline
head:    0001_baseline

$ python -m app.tools.migrate --database <temp>\gobindas.db upgrade
state:   up_to_date
current: 0001_baseline
head:    0001_baseline

$ python -m app.tools.migrate --database <temp>\gobindas.db history
0001_baseline (down: base) - Baseline schema identity.

$ python -m app.tools.migrate --database <temp>\gobindas.db check --full
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
  wal:  exists=False size=None
  shm:  exists=False size=None
  schema revision: 0001_baseline
```

Downgrade/upgrade cycle:

```text
downgrade --revision base -> state: not_initialized, current: (none)
upgrade                   -> state: up_to_date, current: 0001_baseline
check --full              -> status: healthy; all three integrity checks ok
```

Installed versions used for verification:

```text
Python 3.14.6
SQLAlchemy 2.1.8
alembic 1.20.1
```

## 14. Database integrity verification

The final verification used a fresh temporary database at:

```text
C:\Users\Ram Chowdhury\AppData\Local\Temp\opencode\ggbms-phase2-verify\gobindas.db
```

Checks and observed results:

- **Database creation**: `init` created the file and applied `0001_baseline`
  with exit code 0.
- **Schema revision**: `status` reported `up_to_date`, current and head
  `0001_baseline`.
- **Migration history**: one script, `0001_baseline`, down revision `base`.
- **Tables**: the only table was `alembic_version`.
- **PRAGMAs on a real connection**:
  `journal_mode=wal`, `foreign_keys=1`, `synchronous=2` (FULL),
  `busy_timeout=5000`, `temp_store=2` (MEMORY), `trusted_schema=0`,
  `application_id=1195525971`, `user_version=1`.
- **Foreign-key enforcement**: inserting a child row with a nonexistent parent
  was rejected with an integrity error; a valid reference was accepted.
- **Explicit commit**: a row committed through `UnitOfWork` was visible after
  the scope.
- **No-commit rollback**: a row written without `commit()` was absent after the
  scope.
- **Exception rollback**: a row written before a raised exception was absent
  after the scope.
- **Session cleanup**: sessions closed and connections returned to the pool in
  all three cases.
- **Startup verification**: the migrated database passed
  `verify_database_for_startup` with state `up_to_date`.
- **Health check**: `check(full=True)` reported `healthy`; `quick_check`,
  `foreign_key_check`, and `integrity_check` all reported `ok`.
- **Downgrade/upgrade**: downgrade to `base` produced `not_initialized`;
  upgrade restored `up_to_date`; the full check was healthy again.
- **Shutdown**: the only remaining file in the temporary folder after shutdown
  was the database file; the passive checkpoint completed and the engine was
  disposed.
- **No implicit database**: `python -m app.main --smoke-test` with no configured
  database exited 0 and logged "Database: not configured"; no `.db`, `.db-wal`,
  or `.db-shm` file was created.
- **Startup refusal tests**: missing database, newer schema, and uninitialized
  schema each refused startup with exit code 1 and left the file unchanged.
- **Configured startup test**: a healthy configured database started, logged
  `Database ready` with `schema=0001_baseline`, showed the main window, and
  produced no error log entry.
- **Real user data**: no real user database was opened, created, migrated, or
  modified during testing.

## 15. Known limitations

- Phase 2 has no user-facing setup wizard. A database path must be injected
  through configuration or tooling. The folder chooser, write-permission UX,
  save/validate flow, and remembering the location belong to Phase 3.
- Startup does not upgrade an older or uninitialized schema. It refuses and
  requires an explicit CLI upgrade because no verified safety backup exists yet.
  Phase 4 adds the backup-then-upgrade path.
- No backup, restore, retention job, or scheduled runner exists yet (Phase 4).
- No business tables, business repositories, accounting workflows, or reports
  exist yet.
- Encryption at rest is deferred (Q-18). SQLite files are unencrypted.
- Full `PRAGMA integrity_check` is opt-in because it scans the whole file. Normal
  startup performs only identity and revision checks plus a cheap health option
  when explicitly requested.
- The UI has no About/settings surface showing the schema revision; startup logs
  do. A future UI surface can consume `DatabaseDiagnostics`.
- WAL sidecar files exist while the database is open and must never be treated
  as independent backups.
- The implementation and tests target Windows with an offscreen Qt platform.
- The application is not packaged yet; PyInstaller/Inno Setup are later phases.
- `ruff format --check` is not part of the project gate and reports formatting
  drift in some pre-existing files; `ruff check` (the documented gate) passes
  clean. This is cosmetic and does not affect behavior.
- Git state: all Phase 2 work is uncommitted, per the instruction not to commit
  or push without permission.
- The Phase 2 report was written after the implementation date; the completion
  date above distinguishes implementation (2026-11-13) from final verification
  and reporting (2026-11-14).

## 16. Outstanding issues

1. **Owner review and authorization.** The Phase 2 report and database
   foundation require owner review before Phase 3 begins. Phase 3 must not start
   without explicit authorization.
2. **Git decision.** Nothing has been committed or pushed. The owner must decide
   the commit/branch policy for the Phase 1 and Phase 2 working tree.
3. **Final verification correction.** During final verification, the Phase 2
   docstring edit in `app/core/paths.py` was found to have lost its closing
   triple quote, which made the module unimportable and blocked test collection.
   The missing terminator was restored; lint, the full suite, and startup then
   passed. No behavior change was involved.
4. **Human walkthrough.** Phase 2 changes no UI, but the Phase 1 visual review
   (themes at 100% and 150% DPI) remains advisable before release.
5. **Formatter drift.** Optional housekeeping: run `ruff format` on the
   repository if the project decides to make formatting part of the gate. It was
   deliberately not run in Phase 2 to avoid unrelated churn.
6. **Python target confirmation.** CPython 3.14.6 is verified for development;
   the release interpreter should be re-confirmed at packaging (AQ-01).

No functional defect, failing test, or data-safety issue is known in the Phase 2
scope after the correction above.

## 17. Deviations from approved documentation

1. **Empty baseline instead of platform scaffolding.**
   - The Phase 2 brief allowed `schema_metadata`, `app_settings`, and
     `business_profile` only if justified, and deferred audit logging.
   - Phase 2 chose an empty baseline because Alembic already owns revision
     tracking, external configuration already owns machine settings, and
     business identity/audit fields are not approved.
   - The decision is recorded in `docs/DATABASE_SCHEMA.md` §17.1,
     `docs/ARCHITECTURE.md` §17.6, and the roadmap. No business table was
     created.

2. **No automatic upgrade at startup.**
   - The approved architecture requires a verified safety backup before a schema
     change. That backup belongs to Phase 4.
   - Phase 2 therefore refuses a pending or uninitialized schema and provides an
     explicit CLI upgrade. This is a deliberate sequencing decision, documented
     in ARCHITECTURE.md ADR-007/§17.5 and DATABASE_SCHEMA.md §11.

3. **`PRAGMA user_version` is a diagnostic marker, not migration authority.**
   - Alembic's `alembic_version` table remains authoritative. The user version
     exists only as a cheap, human-readable identity/diagnostic value.

4. **WAL was enabled rather than deferred.**
   - The brief required an evaluation and documented decision. WAL improves
     desktop read/write concurrency and is compatible with the required Online
     Backup API. Sidecar risks and backup consequences are documented.

5. **No new dependencies.**
   - The approved stack already included SQLAlchemy and Alembic. Phase 2 used
     them rather than introducing an alternate database or migration library.

No stack, business-scope, or data-safety deviation remains unresolved.

## 18. Phase 3 readiness assessment

**Assessment: ready for Phase 3 after owner review and explicit authorization.**

Phase 2 delivers the contract Phase 3 needs:

- Injected absolute `DatabaseConfig` and optional `AppConfig.database_path`
  (default `null`).
- Explicit database creation through `MigrationManager.create_database()`; no
  implicit creation and no C: fallback.
- Startup identity/revision checks and refusal behavior that the setup wizard
  can reuse.
- `DatabaseDiagnostics` for location validation, health display, and user-safe
  failure messages.
- Temporary-database fixtures and 80 database/money tests for future regression
  coverage.
- A documented transaction/session boundary that business modules must follow.

Phase 3 still owns and must implement:

- The first-launch setup wizard views and view models: welcome, folder picker,
  validation results, confirmation, completion.
- Path validation UX: syntax, creatability, write test, free space, drive type,
  installation-directory refusal, UNC refusal.
- Data-folder scaffolding (`Database`, `Backups/{Automatic,Manual,Safety}`,
  `Attachments`, `Exports/{PDF,Excel}`).
- Database initialization and migrations through the existing manager.
- Atomic config write, config repair flow, and remembering the selected
  location outside the data folder.
- Restore-existing-backup branch (may stage until Phase 4; must not be faked).
- Missing-drive blocking state at startup.
- Minimum confirmed business-profile setup.
- Logging of path decisions without leaking sensitive content.

Phase 4 remains the owner of backup/restore, the verified safety backup before
upgrade, retention, scheduling, and fault-injection drills.

## Verification checklist

- [x] SQLAlchemy installation and version verified (2.1.8).
- [x] Alembic configuration verified (1.20.1) and exercised.
- [x] Fresh temporary SQLite database created.
- [x] All migrations applied (`0001_baseline`).
- [x] Migration history inspected.
- [x] Foreign-key enforcement verified with a rejected violating insert.
- [x] Transaction rollback verified (no-commit and exception paths).
- [x] Database integrity checks run (`quick_check`, `foreign_key_check`,
      `integrity_check`) and healthy.
- [x] Full test suite run: 239 passed.
- [x] Lint run: all checks passed.
- [x] Application starts: smoke test exit code 0.
- [x] Phase 1 functionality remains operational (existing tests pass).
- [x] Documentation reviewed and updated.
- [x] `Reports/PHASE_02_REPORT.md` exists and contains the required sections.
- [x] No real user database was touched.
- [x] No seeder or sample business record was added.
- [x] Existing reports preserved.
- [x] No commit or push performed.

**Phase 2 is complete. Phase 3 must not begin until the owner reviews this report
and explicitly authorizes it.**
