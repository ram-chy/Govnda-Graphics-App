# Project Initialization Prompt — Windows Small Business Management System

## 1. Your Role

Act as a Senior Software Architect, Senior Python Developer, Desktop Application
Engineer, Database Architect, and QA Engineer.

Your responsibility is to help establish a production-quality Windows desktop
application for managing a small business.

Work carefully and systematically. Prioritize architectural correctness, data
safety, maintainability, usability, and straightforward development.

Do not rush. Do not make major architectural decisions without documenting their
reasoning.

## 2. Project Vision

Build a genuine, standalone Windows desktop application for small-business
management.

This must be a native desktop application, NOT a web application packaged inside
a desktop window.

The application must:

- Run directly on Windows.
- Work offline without requiring an internet connection.
- Store business data locally in SQLite.
- Allow the user to choose where the database is stored.
- Support automatic daily database backups.
- Support manual backup and database restoration.
- Provide a professional, easy-to-use desktop interface.
- Be suitable for future expansion into a complete business management system.

The application should be easy to install and run on another Windows computer
without requiring the user to install Python separately.

## 3. Mandatory Technology Stack

Use the following technology stack:

| Area                   | Technology                               |
| ---------------------- | ---------------------------------------- |
| Programming language   | Python                                   |
| Desktop framework      | PySide6                                  |
| UI approach            | Qt Widgets                               |
| Architecture           | MVVM / Presentation-Service separation   |
| Database               | SQLite                                   |
| ORM                    | SQLAlchemy 2                             |
| Database migrations    | Alembic                                  |
| Data validation        | Pydantic + application/domain validation |
| Financial calculations | Decimal-based domain calculations        |
| Charts                 | PyQtGraph                                |
| PDF generation         | ReportLab                                |
| Excel export           | OpenPyXL                                 |
| Logging                | Python logging                           |
| Testing                | pytest                                   |
| Windows packaging      | PyInstaller                              |
| Windows installer      | Inno Setup                               |
| Version control        | Git                                      |

### Important technical requirements

1. Verify compatibility between the selected Python version and all dependencies
   before pinning versions.
2. Prefer a stable, tested Python minor version instead of automatically
   selecting the newest version.
3. Use SQLAlchemy 2 APIs and modern Python practices.
4. Use Alembic for all database schema changes.
5. Never use floating-point arithmetic for financial calculations.
6. SQLite does not provide native fixed-point decimal storage equivalent to
   MySQL DECIMAL. Design a reliable exact-money storage strategy, preferably
   integer minor units or scaled integers, with documented currency precision
   and conversion rules.
7. Use short database transactions and appropriate indexes.
8. Use SQLite foreign keys and appropriate constraints.
9. Evaluate WAL mode and configure SQLite connections consistently.
10. Avoid unnecessary dependencies and overengineering.

## 4. Architecture Requirements

Use a modular monolith with clear separation of responsibilities.

Recommended layers:

### Presentation Layer

- PySide6 windows and dialogs
- Views
- ViewModels
- Reusable UI components
- UI resources and themes

### Application Layer

- Application services
- Use cases
- Input validation
- Transaction orchestration

### Domain Layer

- Business entities
- Business rules
- Accounting rules
- Inventory rules
- Financial calculation logic

### Infrastructure Layer

- SQLAlchemy repositories
- SQLite connection management
- Alembic migrations
- Backup and restore
- PDF and Excel exports
- Logging
- File and attachment storage

Business rules must not depend on PySide6 widgets.

Keep the architecture simple. Do not introduce unnecessary abstractions,
microservices, APIs, or distributed-system patterns.

## 5. Proposed Project Structure

Use this as the initial architectural direction. Adjust it only when there is a
documented technical reason.

```text
BusinessManagementSystem/
│
├── app/
│   ├── main.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── constants.py
│   │   ├── exceptions.py
│   │   ├── security.py
│   │   └── paths.py
│   │
│   ├── ui/
│   │   ├── views/
│   │   ├── viewmodels/
│   │   ├── components/
│   │   ├── dialogs/
│   │   ├── themes/
│   │   └── resources/
│   │
│   ├── domain/
│   │   ├── entities/
│   │   ├── rules/
│   │   └── value_objects/
│   │
│   ├── services/
│   ├── repositories/
│   │
│   ├── modules/
│   │   ├── dashboard/
│   │   ├── customers/
│   │   ├── suppliers/
│   │   ├── products/
│   │   ├── purchases/
│   │   ├── sales/
│   │   ├── inventory/
│   │   ├── accounting/
│   │   ├── expenses/
│   │   └── reports/
│   │
│   └── infrastructure/
│       ├── database/
│       ├── backup/
│       ├── exports/
│       ├── logging/
│       └── scheduler/
│
├── backup_runner/
│   └── main.py
│
├── migrations/
├── tests/
├── scripts/
├── docs/
│
├── requirements.txt
├── pyproject.toml
├── .gitignore
└── README.md
```

Do not create empty modules just to fill the structure. Establish the
architecture and document the planned modules first.

## 6. Database Location — Critical Requirement

The application must NOT automatically store the business database inside the
installation directory or assume that the C: drive is the database location.

On first launch, provide a database setup wizard.

The wizard must allow the user to:

- Select a database folder.
- Confirm the selected location.
- Validate folder permissions.
- Validate that the drive is accessible.
- Check available disk space.
- Create the application data directories.
- Initialize the SQLite database.

Example:

```text
D:\MyBusiness\
│
├── Database\
│   └── BusinessManagement.db
│
├── Backups\
│   ├── Automatic\
│   └── Manual\
│
├── Attachments\
│
└── Exports\
    ├── PDF\
    └── Excel\
```

Requirements:

1. The database location must be independent of the application installation
   directory.
2. The user may choose D:, E:, an external drive, or another suitable local
   folder.
3. Store the selected database location in application configuration outside the
   business database directory.
4. Never silently switch to another drive if the selected database drive becomes
   unavailable.
5. Display a clear error if the database cannot be accessed.
6. Provide a safe database-location migration feature in the future.
7. Changing the database location must use SQLite's backup functionality,
   validate the destination, preserve a rollback copy, and update configuration
   only after successful verification.
8. Do not recommend using a shared network-folder SQLite database for
   simultaneous multi-computer access.

## 7. Backup and Restore — Critical Requirement

Database protection is a core product feature, not an optional extra.

### Automatic daily backup

- Default backup time: 10:00 PM.
- Allow the user to configure the backup time.
- Use Windows Task Scheduler with a lightweight packaged backup runner.
- Automatic backup must work even when the main application is closed.
- Check for missed backups on application startup and create a catch-up backup
  when appropriate.
- Prevent overlapping backup jobs.
- Report backup failures clearly.

If Task Scheduler cannot be configured, explain the limitation and provide a
startup-based fallback.

### Manual backup

Provide a manual backup option inside the application.

Allow the user to:

- Create a backup immediately.
- Choose a destination folder.
- View backup history.
- Identify automatic and manual backups.
- See backup dates, sizes, and verification status.

### Backup implementation

Use SQLite's Online Backup API. Do not simply copy a live database file.

Recommended process:

1. Create a temporary backup.
2. Complete the SQLite backup operation.
3. Validate the backup.
4. Run `PRAGMA integrity_check` before accepting it.
5. Rename the verified temporary backup to its final filename.
6. Record backup status and timestamp.

Never overwrite previous backups.

Use descriptive filenames containing date and time.

### Backup retention

- Default retention: 30 days.
- Allow configuration of retention.
- Do not delete the only valid backup.
- Do not remove a backup before confirming that a newer valid backup exists.

### Restore

Provide a restore workflow that:

1. Lets the user select a backup.
2. Validates the selected backup.
3. Creates a safety backup of the current database.
4. Closes active database connections.
5. Restores through a safe staged process.
6. Verifies the restored database.
7. Reopens the database only after successful verification.
8. Reports success or failure clearly.

Never silently overwrite current business data.

### Important security note

A different drive letter does not necessarily mean a different physical disk.

Document the limitations of local backups. Recommend BitLocker where supported
and an additional backup on a separate physical device.

SQLite is not encrypted by default. Do not claim that storing the database on D:
encrypts or secures it. Evaluate database encryption separately if it becomes a
confirmed requirement.

## 8. UI/UX Direction

Build a professional Windows desktop interface.

Design principles:

- Clean and minimal.
- Easy on the eyes.
- Consistent spacing and typography.
- Clear navigation.
- Data-heavy screens must remain readable.
- Tables must support sorting, filtering, and pagination or efficient
  incremental loading where appropriate.
- Forms must have clear validation messages.
- Use reusable UI components.
- Avoid unnecessary animations and visual clutter.

### Theme direction

Light Mode:

- Calm green-based visual identity.
- Green as a restrained primary accent.
- Neutral backgrounds.
- Semantic colors reserved for warning, error, and informational states.

Dark Mode:

- Professional dark interface.
- Comfortable contrast.
- Consistent semantic colors.

Provide a dashboard with useful business summaries and graphs.

Use Qt Widgets for the main business interface. Do not switch to QML without a
documented reason.

## 9. Planned Business Modules

These are proposed modules. Treat their detailed requirements as pending
discovery rather than inventing final business rules.

Potential modules:

1. Dashboard
2. Customer Management
3. Supplier Management
4. Product Management
5. Category and Unit Management
6. Purchase Management
7. Sales Management
8. Inventory Management
9. Expense Management
10. Accounting and Finance
11. Reports
12. User and Role Management
13. Business Settings
14. Backup and Restore

The system may eventually support:

- Sales and purchase reporting
- Stock movement and valuation
- Customer and supplier balances
- Expense tracking
- Cash and bank summaries
- Profit and loss
- Balance sheet
- Trial balance

Do not implement these modules during initialization.

Document any unresolved business decisions explicitly.

## 10. Security and Reliability

Plan for:

- Safe database transactions.
- Database integrity constraints.
- Parameterized database operations through SQLAlchemy.
- Proper exception handling.
- Secure password hashing if application authentication is included.
- Role and permission design if multiple users are included.
- Safe file handling.
- Audit logging for important business operations.
- Database backup verification.
- Protection against accidental destructive operations.
- Clear application error messages.

Do not invent authentication requirements or user roles. Identify them as
decisions to confirm.

## 11. Documentation — First Deliverable

Before implementing business functionality, create the following master
documentation inside `docs/`.

### A. BLUEPRINT.md

Include:

- Project overview
- Product goals
- Target platform
- Functional scope
- Proposed modules
- Non-functional requirements
- User workflows
- Development phases
- Acceptance criteria
- Open questions and assumptions

### B. ARCHITECTURE.md

Include:

- Technology decisions
- Architecture overview
- Layer responsibilities
- MVVM implementation approach
- Dependency direction
- Database access strategy
- Application startup and shutdown lifecycle
- Error-handling strategy
- Logging strategy
- Packaging strategy
- Architecture trade-offs

### C. DATABASE_SCHEMA.md

Include:

- Initial database design strategy
- Proposed entities
- Relationships
- Primary and foreign keys
- Unique constraints
- Index strategy
- Financial precision and money-storage strategy
- Migration strategy
- SQLite-specific considerations

Do not invent final tables for unconfirmed business workflows. Mark proposed
schemas clearly.

### D. UI_UX_BLUEPRINT.md

Include:

- Main application layout
- Navigation structure
- Dashboard layout
- Form patterns
- Table patterns
- Dialog patterns
- Light Mode design tokens
- Dark Mode design tokens
- Responsive behavior within desktop window sizes
- Accessibility and usability considerations
- Reusable component strategy

### E. BACKUP_STRATEGY.md

Include:

- Database folder selection
- Database path configuration
- SQLite connection lifecycle
- WAL considerations
- Daily backup workflow
- Windows Task Scheduler integration
- Manual backup workflow
- Backup verification
- Retention policy
- Restore workflow
- Database relocation
- Missing-drive handling
- Failure recovery
- Security limitations

### F. DEVELOPMENT_ROADMAP.md

Include:

- Development phases
- Phase dependencies
- Expected deliverables
- Testing strategy
- Definition of done for each phase
- Risks and mitigations

### G. SECURITY_AND_DATA_PROTECTION.md

Include:

- Local data security
- Windows permissions
- Encryption considerations
- Password storage, if applicable
- Audit logging
- Backup security
- Restore safety
- Data-loss prevention

## 12. Development Roadmap

Use this as a proposed execution order:

| Phase | Work                                              |
| ----- | ------------------------------------------------- |
| 0     | Workspace inspection and master documentation     |
| 1     | Python environment and application foundation     |
| 2     | SQLite database setup and migration foundation    |
| 3     | Database folder selection and first-launch wizard |
| 4     | Backup and restore infrastructure                 |
| 5     | Main PySide6 interface and reusable components    |
| 6     | Authentication and user management, if required   |
| 7     | Business master data                              |
| 8     | Purchase, sales, and inventory workflows          |
| 9     | Accounting and expense management                 |
| 10    | Reports and dashboard graphs                      |
| 11    | Testing, security review, and performance         |
| 12    | PyInstaller packaging and Inno Setup installer    |

The roadmap may be refined after requirements discovery, but changes must be
documented.

## 13. Strict Working Rules

Follow these rules throughout the project:

1. Inspect the existing workspace before making changes.
2. If the workspace is empty, initialize the project documentation.
3. If files already exist, understand them before modifying anything.
4. Documentation comes before implementation.
5. Do not implement business modules during initialization.
6. Do not create unnecessary code just to demonstrate progress.
7. Do not use a web frontend or browser-based architecture.
8. Do not introduce Laravel, Next.js, React, Node.js, or a remote database.
9. Do not run seeders or insert sample business data without explicit
   permission.
10. Do not delete or overwrite existing files without understanding their
    purpose.
11. Do not make destructive database operations without explicit permission.
12. Do not silently change approved technology decisions.
13. Do not add unnecessary dependencies.
14. Keep implementation straightforward and maintainable.
15. Use internet access when necessary to verify official documentation and
    dependency compatibility.
16. Do not guess when a business requirement is unclear. Record the question.
17. Do not claim that a feature works unless it has been implemented and tested.
18. Run relevant tests and report actual results.
19. Update documentation when an approved architectural decision changes.
20. Work phase by phase and report completed work accurately.

## 14. Initialization Tasks

Start with these tasks in order:

### Task 1 — Inspect

Inspect:

- Current directory
- Existing files
- Existing Git repository
- Python installation
- Available development environment

Do not modify existing project files before understanding them.

### Task 2 — Architecture Review

Review the proposed stack and architecture.

Identify:

- Compatibility concerns
- SQLite-specific risks
- Financial precision concerns
- Windows packaging risks
- Backup and restore risks
- Missing requirements

Provide recommendations with reasons.

### Task 3 — Documentation

Create all seven master documentation files listed above.

Keep confirmed requirements separate from assumptions and recommendations.

### Task 4 — Consistency Review

Check that:

- All documentation agrees on the technology stack.
- Database location requirements are consistent.
- Backup requirements are technically achievable.
- Financial storage decisions are precise.
- Module scope is not accidentally treated as finalized.
- Development phases have clear dependencies.

### Task 5 — Final Report

Provide a report containing:

1. Workspace inspection results.
2. Confirmed architecture.
3. Created documentation files.
4. Important decisions.
5. Unresolved questions.
6. Identified technical risks.
7. Recommended next phase.
8. Verification performed.

## 15. Completion Boundary

**STOP after completing initialization and documentation.**

Do not begin Phase 1 implementation until I review the documentation and
explicitly authorize the next phase.

The final objective is a stable, maintainable, offline-first Windows desktop
business application—not a quick prototype.

Start with Task 1.
