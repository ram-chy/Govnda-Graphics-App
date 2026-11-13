# PHASE 1 — Python Environment & Application Foundation

## 1. Your Role

Act as a Senior Python Desktop Application Architect and Senior PySide6
Developer.

Implement Phase 1 of the Windows Small Business Management System according to
the approved master documentation.

Work carefully. Prioritize clean architecture, reliability, maintainability, and
straightforward implementation.

Do not rush or introduce unnecessary complexity.

## 2. Project Context

We are developing a genuine standalone Windows desktop application for
small-business management.

This is NOT a web application.

The application must:

- Run natively on Windows.
- Work offline.
- Use Python and PySide6.
- Use SQLite as its database in a later phase.
- Allow the user to choose the database storage folder.
- Support daily automatic and manual backups in a later phase.
- Be installable on Windows without requiring users to install Python
  separately.

### Approved Technology Stack

| Component              | Technology                               |
| ---------------------- | ---------------------------------------- |
| Language               | Python                                   |
| Desktop framework      | PySide6                                  |
| UI                     | Qt Widgets                               |
| Architecture           | MVVM / Presentation-Service separation   |
| Database               | SQLite (Phase 2)                         |
| ORM                    | SQLAlchemy 2 (Phase 2)                   |
| Migrations             | Alembic (Phase 2)                        |
| Validation             | Pydantic + application/domain validation |
| Financial calculations | Decimal-based domain calculations        |
| Charts                 | PyQtGraph                                |
| PDF                    | ReportLab                                |
| Excel                  | OpenPyXL                                 |
| Logging                | Python logging                           |
| Testing                | pytest                                   |
| Packaging              | PyInstaller                              |
| Installer              | Inno Setup                               |

Do not change this stack without documenting a genuine technical issue and
requesting approval.

## 3. Important Business Configuration

The application's default currency is:

**INR — Indian Rupee (₹)**

Currency requirements:

- Currency code: INR
- Currency symbol: ₹
- Default decimal places: 2
- Default display example: ₹1,250.50
- Use Indian number grouping where appropriate, for example ₹1,25,000.50.
- Never use Python float for monetary calculations.
- Use Decimal for financial calculations.
- In Phase 2, implement exact monetary database storage using integer paise or
  another explicitly documented exact representation.

For this phase, establish the application's default currency configuration and
formatting utilities. Do not implement accounting or financial database tables.

Make the default currency configurable in the future, but do not build
multi-currency functionality now.

## 4. Mandatory Documentation Review

Before coding, inspect the existing documentation:

```text
docs/
├── BLUEPRINT.md
├── ARCHITECTURE.md
├── DATABASE_SCHEMA.md
├── UI_UX_BLUEPRINT.md
├── BACKUP_STRATEGY.md
├── DEVELOPMENT_ROADMAP.md
└── SECURITY_AND_DATA_PROTECTION.md
```

Also inspect the existing project structure and Git status.

Use the approved documentation as the source of truth.

If any required documentation is missing or contains a conflict affecting
implementation, report it before proceeding. Do not invent a replacement
architecture.

## 5. Phase 1 Scope

This phase establishes the technical foundation only.

### Task 1 — Python Environment

1. Check the installed Python version.
2. Verify compatibility with PySide6 and the selected dependencies.
3. Select a stable, tested Python version.
4. Create a local virtual environment named `.venv`.
5. Configure dependency management through `pyproject.toml`.
6. Pin or constrain dependencies appropriately.
7. Add/update `.gitignore`.
8. Document environment setup and execution commands.

Do not install unnecessary packages.

### Task 2 — Project Structure

Establish the approved modular project structure.

The initial structure should include:

```text
BusinessManagementSystem/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── constants.py
│   │   ├── exceptions.py
│   │   ├── logging_config.py
│   │   └── paths.py
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── views/
│   │   ├── viewmodels/
│   │   ├── components/
│   │   ├── dialogs/
│   │   ├── themes/
│   │   └── resources/
│   │
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── entities/
│   │   ├── rules/
│   │   └── value_objects/
│   │
│   ├── services/
│   ├── repositories/
│   │
│   ├── modules/
│   │
│   └── infrastructure/
│       ├── database/
│       ├── backup/
│       ├── exports/
│       ├── logging/
│       └── scheduler/
│
├── backup_runner/
├── migrations/
├── tests/
├── scripts/
├── docs/
├── Reports/
│
├── pyproject.toml
├── .gitignore
└── README.md
```

Create only the directories and files needed for this phase. Do not fill the
project with empty placeholder modules unnecessarily.

The `Reports` directory already exists. Preserve its contents.

### Task 3 — Application Entry Point

Implement a working application entry point.

Requirements:

- Initialize the PySide6 application correctly.
- Configure application name and version.
- Initialize logging.
- Initialize application configuration.
- Handle startup exceptions.
- Provide a clean application shutdown.
- Avoid putting business logic in `main.py`.

The application must start successfully from the virtual environment.

### Task 4 — Main Window Foundation

Create the initial main application window using PySide6 Qt Widgets.

The window should establish the approved UI direction:

- Professional desktop layout.
- Clean and minimal appearance.
- Green-based Light Mode.
- Professional Dark Mode foundation.
- Clear navigation area.
- Main content area.
- Consistent typography and spacing.
- Reusable components.

Create a basic application shell with:

- Application title.
- Sidebar/navigation structure.
- Main content area.
- Status bar.
- Theme switching capability.

The navigation entries may be placeholders for future modules. Do not implement
business functionality.

### Task 5 — Configuration Foundation

Implement a configuration service.

It should support:

- Application name.
- Application version.
- Default currency code: INR.
- Default currency symbol: ₹.
- Currency decimal places: 2.
- Theme preference.
- Application settings path.
- Logging configuration.

Store application configuration separately from the business database.

Do not hardcode the business database location.

The actual database-folder selection wizard belongs to a later phase.

### Task 6 — Currency Formatting Utility

Implement a reusable currency utility.

Requirements:

- Accept Decimal values.
- Format INR using ₹.
- Display two decimal places.
- Support Indian number grouping.
- Reject or safely handle invalid monetary input.
- Never convert financial values through float.

Add unit tests for:

- Positive values.
- Negative values.
- Zero.
- Large Indian-number values.
- Decimal precision.
- Invalid input.

Example:

```text
1250.50       → ₹1,250.50
125000.50     → ₹1,25,000.50
1000000.00    → ₹10,00,000.00
```

Keep formatting separate from business calculation logic.

### Task 7 — Logging and Exception Foundation

Implement:

- Centralized logging configuration.
- Rotating log files.
- Appropriate log levels.
- Application-level exception handling.
- Clear user-facing error messages.
- Technical details in logs.

Do not expose sensitive information in logs.

Keep log storage separate from the business database.

### Task 8 — Basic Testing

Use pytest.

Add tests covering:

- Configuration loading.
- Default INR settings.
- Currency formatting.
- Application path handling.
- Logging initialization.
- Basic application startup where practical.
- Core utility behavior.

Tests must be repeatable.

Do not create fake passing tests or disable failing tests to make the test suite
green.

### Task 9 — Development Documentation

Update the relevant documentation:

- `README.md`: installation, environment setup, and how to run.
- `docs/ARCHITECTURE.md`: actual Phase 1 implementation details.
- `docs/DEVELOPMENT_ROADMAP.md`: Phase 1 completion status and Phase 2
  dependencies.

Document deviations from the original architecture and obtain approval for
material changes.

## 6. Explicitly Out of Scope

Do NOT implement these in Phase 1:

- SQLite database initialization.
- SQLAlchemy models or repositories.
- Alembic migrations.
- Database setup wizard.
- Database location migration.
- Automatic backup scheduling.
- Manual backup and restore.
- Windows Task Scheduler integration.
- Authentication.
- User management.
- Customer or supplier management.
- Product management.
- Sales or purchase workflows.
- Inventory.
- Accounting.
- Expense management.
- Business reports.

These belong to later phases.

Do not prematurely implement future features.

## 7. Code Quality Requirements

Follow these rules:

1. Use type hints where appropriate.
2. Follow PEP 8.
3. Use clear naming conventions.
4. Keep functions and classes focused.
5. Avoid duplicated code.
6. Separate UI, application, domain, and infrastructure responsibilities.
7. Use dependency injection where it improves clarity.
8. Avoid circular imports.
9. Avoid global mutable application state.
10. Handle exceptions explicitly.
11. Do not use float for financial calculations.
12. Do not add dependencies without a reason.
13. Do not introduce unnecessary design patterns.
14. Keep the implementation understandable and maintainable.

## 8. Git and File Safety

- Inspect existing Git status before changes.
- Never delete existing files without approval.
- Do not overwrite existing documentation unnecessarily.
- Preserve all existing Reports folder contents.
- Do not commit or push unless explicitly requested.
- Do not run seeders.
- Do not introduce sample business data.

## 9. Mandatory Phase Completion Report

**This requirement applies to every development phase, not just Phase 1.**

The project root contains a folder named:

```text
Reports/
```

After completing Phase 1, you MUST create:

```text
Reports/PHASE_01_REPORT.md
```

Never save phase completion reports only inside `docs/`, the project root, or
another location.

The report must contain:

1. Phase name and number.
2. Completion date.
3. Summary of implemented work.
4. Files and directories created.
5. Files modified.
6. Dependencies added and their purpose.
7. Architecture decisions.
8. INR currency implementation details.
9. Tests executed.
10. Actual test results.
11. Application startup verification.
12. Known limitations.
13. Outstanding issues.
14. Any deviation from approved documentation.
15. Phase 2 readiness assessment.

Be truthful. Do not report a feature as complete unless it has been implemented
and verified.

If the phase cannot be completed, still save a report documenting completed
work, blockers, failures, and remaining tasks.

Do not overwrite previous phase reports.

## 10. Final Verification

Before declaring Phase 1 complete:

- Verify the virtual environment.
- Verify dependency installation.
- Run the test suite.
- Start the desktop application.
- Verify the main window opens.
- Verify Light Mode and Dark Mode.
- Verify INR formatting.
- Check logs for startup errors.
- Review the project structure.
- Review the documentation updates.
- Confirm `Reports/PHASE_01_REPORT.md` exists and is complete.

Report actual commands and results.

## 11. Final Response

After completing the phase, provide a concise summary containing:

- Phase 1 status.
- Main implementation achievements.
- Test results.
- Any outstanding issues.
- Exact report location.
- Recommended next phase.

## 12. Completion Boundary

**STOP after Phase 1.**

Do not start Phase 2 until I review the Phase 1 report and explicitly authorize
the next phase.

Begin by inspecting the workspace and approved documentation. Then implement
Phase 1 systematically.
