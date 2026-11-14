# PHASE 3 — Database Location Selection & First-Launch Setup Wizard

## 1. Your Role

Act as a Senior Python Desktop Application Architect, PySide6 Developer, and
Database Integration Engineer.

Implement Phase 3 of the Gobindas Graphics Business Management System.

Build on the approved Phase 1 and Phase 2 implementations.

Prioritize data safety, reliable first-launch behavior, clear user feedback, and
maintainable architecture.

Do not rush. Do not redesign the existing database architecture without a
documented reason and approval.

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
- PyInstaller (future packaging)

Default currency:

- INR — Indian Rupee
- Symbol: ₹
- Currency code: INR
- Decimal places: 2
- Monetary storage: integer paise
- Financial calculations: Decimal

### Mandatory existing project requirements

- The user chooses the business data storage location.
- The database must not silently fall back to C:.
- The application must work offline.
- The application installation directory and business data directory must remain
  separate.
- Daily automatic backup and manual backup belong to Phase 4.
- Every completed phase must produce a report inside the project-root `Reports`
  folder.

## 3. Mandatory Pre-Implementation Review

Before coding, inspect:

1. Complete project structure.
2. `docs/BLUEPRINT.md`
3. `docs/ARCHITECTURE.md`
4. `docs/DATABASE_SCHEMA.md`
5. `docs/BACKUP_STRATEGY.md`
6. `docs/SECURITY_AND_DATA_PROTECTION.md`
7. `docs/DEVELOPMENT_ROADMAP.md`
8. `Reports/PHASE_01_REPORT.md`
9. `Reports/PHASE_02_REPORT.md`
10. Phase 1 and Phase 2 implementation.
11. Existing tests.
12. Git status.

Verify the Phase 2 interfaces before using them.

Important existing database components include:

- `DatabaseConfig`
- `Database`
- `MigrationManager`
- `DatabaseDiagnostics`
- `AppConfig.database_path`
- Existing database startup verification.
- Existing application composition root and shutdown lifecycle.

Use the actual implementation signatures. Do not assume that names or behavior
match this prompt if the source code differs.

Do not duplicate existing functionality.

If a blocking defect is discovered, explain it before proceeding.

## 4. Phase 3 Objectives

Implement:

1. First-launch detection.
2. Database setup wizard.
3. User-selected data root folder.
4. Windows folder and drive validation.
5. Application data directory creation.
6. SQLite database initialization using the existing migration manager.
7. Database verification.
8. Safe application configuration persistence.
9. Startup integration.
10. Missing-drive handling.
11. Configuration repair workflow.
12. Automated tests.

The setup wizard must be part of the native PySide6 application.

Do not create a browser-based setup page.

## 5. First-Launch Application Flow

Implement this application startup sequence:

### Scenario A — New installation

When the application has no configured database:

1. Initialize the application shell dependencies and logging.
2. Detect that no database location has been configured.
3. Display the first-launch setup wizard.
4. Allow the user to select a data root folder.
5. Validate the selected location.
6. Display the proposed directory structure.
7. Ask for confirmation.
8. Create the required folders.
9. Initialize the SQLite database using `MigrationManager`.
10. Verify the initialized database.
11. Persist the selected database path in application configuration.
12. Open the configured database.
13. Continue to the main application window.

Do not display the normal business application before setup has completed.

### Scenario B — Existing installation

When a database path is already configured:

1. Load the saved configuration.
2. Validate the configured location.
3. Confirm the database exists.
4. Run the existing Phase 2 startup verification.
5. Open the database only if it passes verification.
6. Continue to the main application.

Do not display the first-launch wizard unnecessarily.

### Scenario C — Database drive unavailable

When the configured database drive is missing:

- Do not create another database.
- Do not switch to C:.
- Do not silently change the saved path.
- Do not overwrite configuration.
- Display a clear blocking error.
- Explain that the user must reconnect the drive or locate the existing
  database.
- Allow a safe recovery workflow.

The application must not operate against an empty replacement database.

### Scenario D — Setup cancelled

If the user cancels first-launch setup:

- Exit setup safely.
- Do not create a business database.
- Do not save an incomplete database configuration.
- Preserve existing files.
- Allow the user to retry setup on the next launch.

## 6. Data Root Folder Selection

Let the user select a root folder where all application data will be stored.

Example:

```text
D:\MyBusiness\
│
├── Database\
│   └── BusinessManagement.db
│
├── Backups\
│   ├── Automatic\
│   ├── Manual\
│   └── Safety\
│
├── Attachments\
│
└── Exports\
    ├── PDF\
    └── Excel\
```

Use the existing approved project naming conventions if they differ from the
example.

Requirements:

- Use a native Windows folder selection dialog.
- Display the full selected path.
- Let the user change the selection.
- Show the proposed data directory structure.
- Clearly distinguish the data root from the database file.
- Never assume the current working directory.
- Never derive the business database path from the installation directory.

The application should remember the selected data root through its
configuration, while `database_path` remains the explicit absolute path to the
SQLite file.

## 7. Folder and Drive Validation

Implement a dedicated validation service.

Validate the selected location before creating the database.

### Required checks

1. Path is valid.
2. Path is absolute.
3. Path is accessible.
4. Folder exists or can safely be created.
5. Selected path is a directory, not a file.
6. Parent directory is accessible.
7. Write permission is available.
8. Read permission is available.
9. Available disk space can be inspected.
10. Drive type is identified where Windows APIs support it.
11. The selected path is not inside the application installation directory.
12. UNC/network paths are rejected for this single-computer SQLite design.
13. The location is not a protected or unsuitable Windows system directory.

### Drive support

Support appropriate local drives, including:

- Fixed drives such as D: and E:.
- Removable drives such as an external USB drive.

Do not reject an external drive simply because it is removable.

Show a clear warning when a removable drive is selected because it must remain
connected whenever the application needs the database.

Do not assume that a different drive letter represents a different physical
disk.

### Disk space

Display available free space.

Do not invent a misleading database-size estimate or a hardcoded minimum
capacity without justification.

If space is insufficient for the initial setup, explain the issue and stop
safely.

### Write test

Use a uniquely named temporary probe file.

- Create the file.
- Write a small test payload.
- Flush and close it.
- Remove it.
- Verify the result.

Do not overwrite user files during validation.

## 8. Application Directory Creation

After successful validation and user confirmation, create:

```text
SelectedDataRoot/
│
├── Database/
├── Backups/
│   ├── Automatic/
│   ├── Manual/
│   └── Safety/
├── Attachments/
└── Exports/
    ├── PDF/
    └── Excel/
```

Requirements:

- Create directories safely.
- Verify the result.
- Handle permission errors.
- Do not delete existing folders.
- Do not delete existing files.
- Do not overwrite existing databases.
- Do not treat an existing non-empty folder as empty.
- Preserve existing user data.

If setup fails, retain any existing data and report exactly what happened.

Cleanup may remove only empty directories created by the current failed setup
attempt, and only when it is safe to do so.

## 9. Database Initialization

Use the existing Phase 2 database architecture.

Do not create a second database implementation.

Required flow:

1. Construct the database file path under the selected `Database` directory.
2. Create the appropriate `DatabaseConfig`.
3. Validate the database configuration.
4. Initialize the database through the existing
   `MigrationManager.create_database()` or the actual approved equivalent.
5. Apply the existing Alembic baseline migration.
6. Verify application identity.
7. Verify Alembic migration state.
8. Run the appropriate database health checks.
9. Confirm the database is ready.
10. Open the database using the existing `Database` lifecycle object.

Do not use `Base.metadata.create_all()`.

Do not manually insert an Alembic revision.

Do not invent additional schema tables.

Do not implement business tables in this phase.

### Existing database protection

If the selected database file already exists:

- Never overwrite it.
- Never initialize over it.
- Inspect it through the existing diagnostics.
- If it is a recognized healthy application database, offer a safe connection
  workflow.
- If it is an unknown, incompatible, corrupt, or uninitialized file, refuse to
  overwrite it.
- Explain the available next steps.

Do not pretend that restoring an existing backup is supported in Phase 3. Backup
restoration belongs to Phase 4.

## 10. Configuration Persistence

Persist the selected data root and database file path in the existing
application configuration system.

Requirements:

- Use the existing `AppConfig`.
- Do not introduce a competing configuration file.
- Store the database path as an absolute path.
- Preserve existing application settings.
- Keep configuration outside the selected business data root.
- Use atomic configuration writes.
- Validate the saved configuration after writing.
- Handle corrupted configuration safely.

### Atomic write process

1. Serialize the complete configuration.
2. Write to a temporary configuration file in the same directory.
3. Flush and close the file.
4. Validate the serialized configuration.
5. Atomically replace the original configuration file.
6. Re-read the saved configuration.
7. Confirm that the database path matches the selected path.

Do not update the active configuration before the database has been successfully
initialized and verified.

If configuration persistence fails after database initialization:

- Do not delete the newly created database.
- Do not overwrite user data.
- Keep setup recoverable.
- Explain the failure.
- Allow the user to retry configuration persistence.

## 11. Setup Wizard UI

Create a professional multi-step PySide6 wizard.

Suggested steps:

### Step 1 — Welcome

Explain:

- First-time application setup.
- Business data is stored locally.
- The user chooses the storage location.
- The database will not be stored automatically inside the installation
  directory.

### Step 2 — Choose Data Location

Include:

- Folder path display.
- Browse button.
- Selected location summary.

### Step 3 — Validate Location

Show:

- Path validity.
- Read/write permission.
- Drive type.
- Available disk space.
- Network path validation.
- Installation-directory validation.

Use clear success, warning, and error states.

### Step 4 — Review Directory Structure

Show the proposed folders and database filename.

Explain that the application will create these directories.

### Step 5 — Confirm Setup

Show:

- Data root.
- Database file path.
- Drive information.
- Important storage warnings.

Require explicit confirmation before initialization.

### Step 6 — Initialize

Show progress and meaningful status messages.

Do not freeze the UI during long operations.

Use an appropriate worker mechanism for database initialization where necessary.

### Step 7 — Completion

Show:

- Successful initialization.
- Selected storage location.
- Database status.
- Next action to open the application.

### UI design

Follow the approved design system:

- Clean and minimal.
- Calm green-based Light Mode.
- Professional Dark Mode.
- Clear typography.
- Consistent spacing.
- Native desktop behavior.
- Accessible controls.
- Useful validation messages.

Reuse existing UI components where appropriate.

Do not redesign the main application shell unnecessarily.

## 12. Configuration Repair and Recovery

Implement a safe recovery path for configuration problems.

Handle:

- Missing configuration.
- Invalid configuration.
- Corrupted configuration.
- Missing configured drive.
- Missing database file.
- Permission failure.
- Database identity mismatch.
- Unsupported migration state.

Never silently recreate a missing database.

When the configuration is invalid or corrupted:

- Preserve the original configuration file.
- Log a safe diagnostic.
- Provide a recovery option.
- Ask the user to locate the existing data root or database where appropriate.
- Do not discard previous settings automatically.

If the original database cannot be found, do not create a new database without
explicit user confirmation.

## 13. Business Profile Scope

The Phase 2 report identifies minimum confirmed business-profile setup as a
possible Phase 3 responsibility.

However, no complete business-profile schema or field list has been approved.

Therefore:

- Do not invent business-profile fields.
- Do not create a speculative `business_profile` database table.
- Do not prefill a business name or address based only on the project name.
- Keep the database setup wizard focused on storage and initialization.
- Record business-profile requirements as an open decision for a later phase.

The default currency remains INR (₹).

Do not implement multi-currency functionality.

## 14. INR Requirements

Preserve the Phase 2 financial foundation.

- Default currency: INR.
- Symbol: ₹.
- Decimal places: 2.
- Use Decimal for calculations.
- Use integer paise for monetary database storage.
- Do not use float.
- Do not change the existing Money implementation unnecessarily.

Add regression tests to ensure the setup process does not reset or modify
currency configuration.

## 15. Explicitly Out of Scope

Do not implement:

- Automatic daily backup.
- Manual backup.
- Backup retention.
- Backup restore.
- Windows Task Scheduler integration.
- Backup verification workflow.
- Automatic schema upgrades.
- Business profile database tables.
- Authentication.
- User management.
- Customers.
- Suppliers.
- Products.
- Sales.
- Purchases.
- Inventory.
- Accounting.
- Expenses.
- Business reports.
- PyInstaller packaging.

These belong to later phases.

## 16. Testing Requirements

Use pytest.

All tests must use temporary directories and temporary SQLite databases.

Never modify a real business database during automated tests.

### First-launch tests

- No configured database opens the setup wizard.
- Successful setup opens the main application.
- Cancelled setup does not initialize a database.
- Reopening an initialized application skips the first-launch wizard.

### Folder validation tests

- Valid fixed drive.
- Valid removable drive where testable.
- Invalid path.
- Relative path.
- Missing parent.
- Non-directory path.
- Read-only location.
- Unwritable location.
- UNC/network path.
- Installation directory.
- Available-space reporting.

Mock Windows drive APIs where required.

### Directory creation tests

- Required directory structure.
- Existing folders preserved.
- Existing files preserved.
- Partial setup failure.
- Permission failure.
- Safe cleanup behavior.

### Database tests

- Successful initialization.
- Alembic baseline applied.
- Application identity verified.
- Database health verified.
- Existing healthy database not overwritten.
- Existing unknown database refused.
- Corrupt database refused.
- Missing drive does not create fallback database.

### Configuration tests

- Correct absolute path saved.
- Data root saved.
- Existing settings preserved.
- Atomic write behavior.
- Re-read verification.
- Corrupt configuration recovery.
- Failed configuration persistence remains recoverable.

### Startup and UI tests

- First-launch wizard appears when required.
- Existing installation opens normally.
- Missing drive blocks normal operation.
- Cancel exits safely.
- Wizard navigation works.
- Light and Dark themes remain functional.

### Regression tests

Run the complete existing test suite.

All Phase 1 and Phase 2 tests must continue passing.

Do not disable tests or fabricate results.

## 17. Documentation Updates

Update:

### `docs/ARCHITECTURE.md`

Document:

- First-launch startup lifecycle.
- Setup wizard responsibilities.
- Folder validation service.
- Configuration persistence.
- Database initialization integration.
- Recovery flow.

### `docs/BACKUP_STRATEGY.md`

Document:

- Final data directory layout.
- Backup directory structure.
- Database path ownership.
- WAL sidecar implications.
- Future backup runner integration points.

Do not implement backup functionality.

### `docs/SECURITY_AND_DATA_PROTECTION.md`

Document:

- Folder permissions.
- Drive availability.
- UNC path policy.
- Configuration protection.
- Database overwrite prevention.
- Setup recovery behavior.

### `docs/DATABASE_SCHEMA.md`

Document:

- Existing Phase 2 schema initialization.
- Confirmation that Phase 3 adds no business tables.

### `docs/DEVELOPMENT_ROADMAP.md`

Mark Phase 3 status and identify Phase 4 dependencies.

Do not rewrite unrelated sections.

## 18. File and Git Safety

- Inspect Git status before modifications.
- Preserve all Phase 1 and Phase 2 work.
- Preserve all existing reports.
- Do not delete unrelated files.
- Do not run seeders.
- Do not insert sample business records.
- Do not commit or push without permission.
- Never overwrite an existing database.
- Never silently change the database path.
- Never use C: as a fallback.

## 19. Mandatory Phase Completion Report

Every development phase must save its completion report inside the project-root
`Reports` folder.

For this phase, create:

`Reports/PHASE_03_REPORT.md`

The report must contain:

1. Phase number and title.
2. Completion date.
3. Implementation summary.
4. Files created.
5. Files modified.
6. Dependencies added and reasons.
7. First-launch workflow.
8. Folder selection implementation.
9. Drive and folder validation.
10. Directory structure.
11. Database initialization process.
12. Configuration persistence.
13. Recovery and missing-drive behavior.
14. INR configuration preservation.
15. Tests executed.
16. Actual test results.
17. Application startup verification.
18. Known limitations.
19. Outstanding issues.
20. Deviations from approved documentation.
21. Phase 4 readiness assessment.

If the phase is incomplete, still create the report with completed work,
blockers, failures, and remaining tasks.

Never overwrite:

- `Reports/PHASE_01_REPORT.md`
- `Reports/PHASE_02_REPORT.md`

This Reports-folder requirement is mandatory for every future phase.

## 20. Final Verification

Before declaring Phase 3 complete:

- Run Ruff checks.
- Run the full pytest suite.
- Verify first-launch setup.
- Verify successful database initialization.
- Verify database migration state.
- Verify database integrity.
- Verify configuration persistence.
- Verify setup cancellation.
- Verify missing-drive handling.
- Verify no C: fallback exists.
- Verify existing database protection.
- Verify Phase 1 and Phase 2 functionality.
- Review all documentation changes.
- Confirm `Reports/PHASE_03_REPORT.md` exists.

Report actual commands and results.

## 21. Final Response

Provide:

- Phase 3 completion status.
- Setup wizard functionality.
- Database folder selection behavior.
- Database initialization result.
- Configuration and recovery behavior.
- Test results.
- Outstanding issues.
- Exact report location.
- Recommended next phase.

## 22. Completion Boundary

STOP after Phase 3.

Do not begin Phase 4 until I review the Phase 3 report and explicitly authorize
it.

Begin by inspecting the existing project and Phase 2 report. Then implement
Phase 3 systematically.
