# PHASE 2 — SQLite Database Foundation & Migration System

## 1. Role

Act as a Senior Python Database Architect and Senior SQLAlchemy Developer.

Implement Phase 2 of the Windows Small Business Management System using the
approved project architecture and existing Phase 1 implementation.

Prioritize database integrity, data safety, maintainability, and predictable
behavior.

Do not rush. Do not redesign approved architecture without a documented reason
and approval.

## 2. Project Context

This is a genuine standalone Windows desktop application.

Approved technology stack:

- Python
- PySide6 / Qt Widgets
- SQLAlchemy 2
- SQLite
- Alembic
- Pydantic
- pytest

The application must work offline.

Default business currency:

- Currency: INR — Indian Rupee
- Currency code: INR
- Symbol: ₹
- Decimal places: 2
- 1 INR = 100 paise

Phase 1 should already provide the Python environment, application shell,
configuration foundation, logging, and currency utilities.

Inspect the actual implementation before proceeding.

## 3. Mandatory Pre-Implementation Review

Before changing files:

1. Inspect the complete existing project structure.
2. Read `docs/BLUEPRINT.md`.
3. Read `docs/ARCHITECTURE.md`.
4. Read `docs/DATABASE_SCHEMA.md`.
5. Read `docs/BACKUP_STRATEGY.md`.
6. Read `docs/SECURITY_AND_DATA_PROTECTION.md`.
7. Read `docs/DEVELOPMENT_ROADMAP.md`.
8. Inspect Phase 1 implementation and tests.
9. Read `Reports/PHASE_01_REPORT.md`.
10. Inspect Git status.

Verify that Phase 1 is complete enough to support Phase 2.

If Phase 1 has unresolved problems that block safe database implementation,
report them before proceeding.

Do not assume that Phase 1 was completed correctly merely because a report
exists.

## 4. Phase 2 Objectives

Implement:

1. SQLite connection management.
2. SQLAlchemy 2 database integration.
3. Database configuration abstraction.
4. Database session management.
5. Database transaction management.
6. Alembic migration infrastructure.
7. Initial system-level database schema.
8. Database integrity checks.
9. Database health diagnostics.
10. Database-related automated tests.

The implementation must support the future database-folder selection wizard
without depending on a hardcoded database location.

## 5. Database Architecture

Use SQLAlchemy 2 with modern declarative models.

Establish a clean database architecture:

- Database engine management.
- Session factory.
- Session lifecycle.
- Transaction boundaries.
- Declarative Base.
- Model registration.
- Repository foundation where appropriate.
- Database exception handling.

Keep database access out of PySide6 views and widgets.

Business modules must access database functionality through the application and
repository layers.

Avoid creating unnecessary abstractions.

### Connection management

Implement centralized SQLite connection management.

Requirements:

- Use an appropriate SQLAlchemy connection pool configuration for a single-user
  desktop application.
- Enable SQLite foreign key enforcement on every connection.
- Configure a sensible connection timeout.
- Handle locked-database errors gracefully.
- Use short-lived sessions.
- Close sessions reliably.
- Roll back failed transactions.
- Do not leave open database connections during application shutdown.

Evaluate WAL mode and document the decision.

If WAL mode is enabled:

- Understand its `-wal` and `-shm` companion files.
- Do not treat these files as independent backups.
- Ensure future backup implementation uses SQLite's Online Backup API.
- Handle database shutdown and checkpointing appropriately.

Do not enable settings without explaining their purpose and implications.

## 6. Database Location Abstraction

The database location-selection wizard belongs to Phase 3.

However, Phase 2 must prepare the architecture for it.

Implement a database path provider or equivalent abstraction.

Requirements:

1. Database code must not assume the database is located in the project
   directory.
2. Database path must come from application configuration or an injected
   database configuration object.
3. Support an explicitly configured absolute database path.
4. Validate the parent directory before database creation.
5. Do not silently create or switch to a default C: database.
6. Do not silently fall back to another database if the configured path is
   unavailable.
7. Raise a clear application-level exception when the configured database cannot
   be accessed.
8. Keep database path handling independent from SQLAlchemy model definitions.

For automated tests, use temporary directories and temporary database files.

Do not implement the user-facing folder selection wizard in this phase.

## 7. SQLite Schema Foundation

Create only the minimum system-level schema required at this stage.

Potential infrastructure tables, subject to the approved schema documentation:

### `schema_metadata` (only if needed)

Purpose:

- Store application-level database schema metadata if Alembic version tracking
  alone is insufficient.

Avoid duplicating Alembic's migration tracking unnecessarily.

### `app_settings` (only if justified)

Purpose:

- Store limited database-level application settings when there is a clear need.

Do not duplicate settings already stored in the external application
configuration file.

### `audit_logs` (defer if requirements are not finalized)

Do not create a speculative audit system without a documented event model,
retention strategy, and privacy requirements.

Do not create business tables in Phase 2.

No customers, suppliers, products, sales, purchases, expenses, inventory,
accounting, or journal tables.

Document the reason for every initial table.

## 8. Financial Precision Strategy

This application uses INR.

SQLite does not provide native fixed-point decimal storage equivalent to MySQL
DECIMAL.

Use integer paise as the preferred storage representation for monetary values
with two decimal places.

Examples:

| Amount       | Stored paise |
| ------------ | -----------: |
| ₹0.50        |           50 |
| ₹1.00        |          100 |
| ₹125.50      |        12550 |
| ₹1,250.75    |       125075 |
| ₹1,00,000.00 |     10000000 |

Requirements:

1. Never use Python float for financial calculations.
2. Use Decimal for domain-level financial calculations.
3. Convert Decimal to integer paise using an explicit precision and rounding
   policy.
4. Reject unsupported precision when appropriate.
5. Avoid implicit rounding.
6. Define overflow limits and validation rules.
7. Keep conversion utilities centralized.
8. Add unit tests for conversions and edge cases.
9. Document how future accounting and inventory modules must use this strategy.

Do not implement financial transactions in Phase 2.

## 9. Alembic Migration Infrastructure

Set up Alembic properly.

Requirements:

- Configure Alembic to use SQLAlchemy metadata.
- Register all current models.
- Support the configured database location.
- Support fresh database creation.
- Support migration upgrades.
- Support migration history.
- Support downgrade scripts where safe and meaningful.
- Keep migrations in version control.
- Never use `Base.metadata.create_all()` as a replacement for the migration
  system in production.
- Do not manually edit Alembic version tracking tables.
- Ensure future migrations can run against user-selected database locations.

Test:

1. Fresh database initialization.
2. Applying all migrations.
3. Re-running migrations when already up to date.
4. Migration status inspection.
5. A safe migration upgrade scenario.

Do not use seeders.

Do not insert sample business records.

## 10. Database Health and Integrity

Implement database diagnostic utilities.

Include:

- Connection test.
- Database existence check.
- Read/write capability check.
- SQLite version inspection.
- Database file information.
- Foreign-key enforcement verification.
- `PRAGMA quick_check`.
- Full `PRAGMA integrity_check` utility.

Do not run expensive integrity checks on every normal application startup
without a documented reason.

Provide clear results for:

- Healthy database.
- Missing database.
- Unavailable drive.
- Permission failure.
- Corrupt database.
- Locked database.
- Migration required.
- Migration failure.

Never automatically delete or recreate a database because it appears unavailable
or corrupt.

## 11. Transaction Management

Provide a consistent transaction strategy.

Requirements:

- Use explicit transaction boundaries.
- Commit only after successful operations.
- Roll back on exceptions.
- Prevent accidental partial writes.
- Avoid holding transactions open while waiting for user input.
- Document the single-writer behavior of SQLite.
- Keep database operations short.

Do not implement business-specific repositories or workflows yet.

## 12. Testing Requirements

Use pytest.

Create automated tests covering:

### Connection tests

- Database creation.
- Database connection.
- Database path configuration.
- Missing parent directory.
- Unavailable database path.
- Session creation and cleanup.

### SQLite configuration tests

- Foreign keys enabled.
- Connection timeout configuration.
- WAL behavior if enabled.
- Connection lifecycle.

### Migration tests

- Fresh database migration.
- Upgrade to latest.
- Already-up-to-date migration.
- Migration tracking.

### Transaction tests

- Successful commit.
- Failed transaction rollback.
- Session cleanup after errors.

### Integrity tests

- Quick check.
- Full integrity check.
- Foreign-key integrity.

### Financial precision tests

- Decimal to paise conversion.
- Paise to Decimal conversion.
- Precision rejection.
- Negative amounts where permitted.
- Large amount boundaries.
- Rounding policy.

Use temporary databases for tests.

Tests must not modify any real user database.

Do not disable tests or fabricate passing results.

## 13. Documentation Updates

Update:

`docs/ARCHITECTURE.md`

- Actual database architecture.
- Connection lifecycle.
- Session strategy.
- Transaction strategy.
- Dependency direction.

`docs/DATABASE_SCHEMA.md`

- Actual Phase 2 tables.
- Relationships.
- Constraints.
- Indexes.
- Migration strategy.
- Monetary storage strategy.

`docs/SECURITY_AND_DATA_PROTECTION.md`

- Database permissions.
- Connection safety.
- Integrity checking.
- Database corruption handling.

`docs/BACKUP_STRATEGY.md`

- How the database architecture supports SQLite Online Backup API.
- WAL considerations.
- Safe database connection shutdown.

`docs/DEVELOPMENT_ROADMAP.md`

- Phase 2 completion status.
- Phase 3 dependencies.

Do not rewrite unrelated documentation.

## 14. Explicitly Out of Scope

Do not implement:

- Database folder selection wizard.
- User-facing database relocation.
- Backup scheduler.
- Automatic daily backup.
- Manual backup UI.
- Restore UI.
- Windows Task Scheduler.
- Authentication.
- User roles.
- Business profile.
- Customers.
- Suppliers.
- Products.
- Purchases.
- Sales.
- Inventory.
- Accounting.
- Expenses.
- Business reports.

These belong to later phases.

## 15. File and Git Safety

- Inspect Git status before modifications.
- Preserve existing Phase 1 work.
- Preserve all previous reports.
- Do not delete or overwrite unrelated files.
- Do not run seeders.
- Do not insert sample business data.
- Do not commit or push without permission.
- Do not modify a real business database during tests.
- Do not perform destructive migrations against existing user data.

## 16. Mandatory Phase Completion Report

Every development phase must produce a report inside the project-root `Reports`
folder.

For Phase 2, create:

`Reports/PHASE_02_REPORT.md`

The report must include:

1. Phase number and title.
2. Completion date.
3. Summary of implementation.
4. Files created.
5. Files modified.
6. Dependencies added and reasons.
7. Database architecture.
8. SQLite configuration.
9. Migration implementation.
10. Initial schema and table justification.
11. INR and integer-paise implementation.
12. Tests executed.
13. Actual test results.
14. Database integrity verification.
15. Known limitations.
16. Outstanding issues.
17. Deviations from approved documentation.
18. Phase 3 readiness assessment.

If the phase is incomplete, still create the report documenting completed work,
blockers, and remaining tasks.

Never overwrite `Reports/PHASE_01_REPORT.md` or any previous phase report.

**This Reports-folder requirement is mandatory for every future phase as well.**

## 17. Final Verification

Before declaring completion:

- Verify SQLAlchemy installation.
- Verify Alembic configuration.
- Create a fresh temporary SQLite database.
- Apply migrations.
- Inspect migration history.
- Verify foreign-key enforcement.
- Verify transaction rollback.
- Run database integrity checks.
- Run all relevant tests.
- Verify the application still starts.
- Confirm the existing Phase 1 functionality remains operational.
- Review documentation.
- Confirm `Reports/PHASE_02_REPORT.md` exists.

Report actual commands and results.

## 18. Final Response

Provide:

- Phase 2 completion status.
- Database architecture implemented.
- Migration status.
- Monetary precision strategy.
- Test results.
- Known limitations.
- Exact completion report location.
- Recommended next phase.

## 19. Completion Boundary

STOP after Phase 2.

Do not begin Phase 3 until I review the Phase 2 report and explicitly authorize
it.

Start by inspecting the existing project and Phase 1 report. Then implement
Phase 2 systematically.
