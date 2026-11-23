# BLUEPRINT — Gobindas Graphics Business Management System

| Field | Value |
| --- | --- |
| Document | BLUEPRINT.md |
| Version | 1.0 |
| Date | 2026-11-12 |
| Status | Draft for review — no implementation started |
| Scope | Product vision, scope, workflows, phases, acceptance criteria |
| Related | ARCHITECTURE.md, DATABASE_SCHEMA.md, UI_UX_BLUEPRINT.md, BACKUP_STRATEGY.md, DEVELOPMENT_ROADMAP.md, SECURITY_AND_DATA_PROTECTION.md |

## 0. How to read this document

This is the product-level source of truth for the project. Statements are labelled:

- **[CONFIRMED]** — came directly from the initialization brief; treat as fixed.
- **[RECOMMENDED]** — a proposal from the architecture review; requires approval before it becomes binding.
- **[OPEN]** — a business or product decision that has not been made. Defaults are provisional only.

All seven documents use the same labels and the same decision IDs (ADR-xxx in ARCHITECTURE.md, Q-xx in this document, A-xx for assumptions). If two documents disagree, this one wins for product scope and ARCHITECTURE.md wins for technical implementation.

## 1. Project overview

### 1.1 Identity

- **Working product name:** Gobindas Graphics Business Management System (internal short name: **GGBMS**).
- **Client context:** Gobindas Graphics, a small graphics/printing business. The exact service catalogue is not yet confirmed.
- **Repository root:** `D:\Development\Gobindas Graphics`.
- **Distribution name:** `gobindas-bms` (Python package metadata).
- **Application executable:** `GobindasBMS.exe` (provisional).
- **Backup executable:** `GobindasBMS-Backup.exe` (provisional).

### 1.2 One-sentence description

A standalone, offline-first Windows desktop application that lets a small business record sales, purchases, inventory, expenses, and basic accounting in a local SQLite database, with first-class database location control and automatic verified backups.

### 1.3 What "done" means at initialization

The initialization phase is complete when:

1. The workspace has been inspected and the environment recorded.
2. The seven master documents exist under `docs/`.
3. The stack has been checked for compatibility.
4. Risks, assumptions, and open questions are explicit.
5. No business functionality has been implemented, no sample data has been inserted, and no schema has been created.

**The project stops there until the owner approves the documentation and authorizes Phase 1.**

## 2. Product goals

### 2.1 Primary goals

| ID | Goal | Measure |
| --- | --- | --- |
| G-01 | Run natively on Windows without a browser or a server | Single desktop executable; no HTTP server; no web runtime |
| G-02 | Work fully offline | All features usable with the network disconnected |
| G-03 | Keep business data under the owner's control | User-selected database folder; no hidden C: default |
| G-04 | Protect data against loss and corruption | Verified automatic + manual backups, guarded restore |
| G-05 | Be fast and pleasant for daily data entry | Keyboard-first forms, responsive tables, startup < 5 s |
| G-06 | Survive future growth | Modular monolith, versioned schema, documented boundaries |
| G-07 | Be installable without Python knowledge | PyInstaller build + Inno Setup installer |

### 2.2 Non-goals (v1)

- Cloud synchronization, remote API, mobile client, or web dashboard.
- Simultaneous multi-computer use of one SQLite file over a network share.
- Multi-company or multi-tenant operation.
- Full statutory accounting certification or tax filing.
- Payroll, manufacturing/MRP, CRM campaigns, e-commerce integration.
- Custom report designer.
- Built-in SQLite encryption (evaluated separately, see SECURITY_AND_DATA_PROTECTION.md).

Non-goals may be revisited only through a documented decision.

## 3. Target platform and environment

### 3.1 Runtime target

| Item | Value | Status |
| --- | --- | --- |
| OS | Windows 10 22H2 and Windows 11, x64 | [CONFIRMED] Windows |
| Architecture | x86-64 only | [RECOMMENDED] |
| Python | CPython 3.14.x | [RECOMMENDED] verified compatible |
| UI framework | PySide6 6.12.x, Qt Widgets | [CONFIRMED] stack |
| Database | SQLite 3.50.x (bundled with Python) | [CONFIRMED] stack |
| Display | 1280×720 minimum; 100–200% DPI | [RECOMMENDED] |
| Installer | Inno Setup 6.x | [CONFIRMED] stack; not installed on dev machine yet |

### 3.2 Inspected development machine (2026-11-12)

- Windows 11 Pro, build 10.0.26300, 16 GB RAM.
- Default Python 3.14.6 at `C:\Users\Ram Chowdhury\AppData\Local\Programs\Python\Python314`, pip 26.1.2.
- Alternate Python 3.13.0 at `C:\laragon\bin\python\python-3.13`.
- Git 2.51.0; global identity configured; **no Git repository exists yet**.
- Python `sqlite3` library: SQLite 3.50.4.
- Drives: C: (12 GB free of 126 GB), D: (221 GB free of 239 GB), E: removable with no media.
- Already installed globally: `openpyxl 3.1.5`, `reportlab 5.1.0`, `pyinstaller 6.22.3`.
- Not installed: PySide6, SQLAlchemy, Alembic, Pydantic, PyQtGraph, pytest, Inno Setup.
- A dedicated virtual environment will be created in Phase 1; global packages will not be used.

## 4. Users and operating context

### 4.1 Personas

| Persona | Description | Needs |
| --- | --- | --- |
| Owner/operator | Runs the business, enters sales and purchases, checks profit | Fast entry, clear summaries, confidence in backups |
| Office assistant | Handles customers, invoices, supplier bills | Guided forms, search, error prevention |
| Accountant (occasional) | Reviews ledgers, exports data | Accurate totals, PDF/Excel export, traceability |

The number of concurrent users and whether login is required are **[OPEN] Q-04**. The v1 design assumes one active Windows user per database, with the architecture able to add authentication later.

### 4.2 Operating assumptions

- The computer is a personal business workstation, not a shared server.
- The owner can choose a data folder on an internal or external drive.
- The machine may be switched off at the configured backup time.
- The database is expected to stay below 2 GB for several years.
- The owner may not have administrator rights at daily runtime.

## 5. Functional scope

### 5.1 In scope for the product (eventual v1.0)

1. First-launch setup wizard with database location validation.
2. Dashboard with business summaries and charts.
3. Customer and supplier master data.
4. Product/service master data, categories, units, and unit conversion.
5. Purchase recording and supplier balances.
6. Sales invoicing and customer balances.
7. Inventory movements, stock on hand, and valuation.
8. Expense recording with categories.
9. Basic accounting summaries (cash, bank, receivables, payables, profit and loss).
10. Reports with PDF and Excel export.
11. Configurable automatic daily backup, manual backup, restore, backup history.
12. Business settings and database location management.
13. Optional authentication and roles, **only if approved**.
14. Audit trail for financially significant actions.

### 5.2 Explicitly out of scope for initialization

No business modules, tables, seed data, or UI screens are implemented during initialization. The module list in Section 7 is a proposal, not a commitment to detailed behaviour.

### 5.3 Scope boundary per module

Each module must have, before implementation:

- Approved field list and validation rules.
- Approved workflow and posting rules.
- Approved numbering scheme (where documents are numbered).
- Approved effect on inventory and accounting.
- Approved report/export requirements.
- Tests for the rules.

Anything not approved is marked **[OPEN]** and must not be guessed in code.

## 6. User workflows (target behaviour)

### 6.1 First launch

1. Application starts and looks for `%APPDATA%\GobindasBMS\config.json`.
2. If no configuration exists, the setup wizard opens.
3. The user selects a business data folder (example: `D:\GobindasBusiness`).
4. The wizard validates: path syntax, existence/creatability, write access, free space (minimum 500 MB recommended), drive type, and that the folder is not inside the installation directory.
5. The wizard creates `Database\`, `Backups\Automatic\`, `Backups\Manual\`, `Attachments\`, `Exports\PDF\`, `Exports\Excel\`.
6. The wizard creates a new SQLite database, applies Alembic migrations, and records the location in config only after verification.
7. The user may restore an existing backup instead of creating an empty database.
8. The user confirms business profile basics (name, currency, fiscal year start) — fields to be finalized.
9. The main window opens.

Failure at any step leaves the previous configuration untouched and shows a specific, actionable message.

### 6.2 Normal startup

1. Read configuration.
2. Verify the database folder and database file are accessible.
3. If the drive is unavailable: show a blocking error with **Retry**, **Locate database**, and **Exit**. Never silently switch locations.
4. Acquire the single-instance lock.
5. Open the database, apply pending migrations after a safety backup, run quick integrity checks when configured.
6. Check whether an automatic backup was missed; offer/perform catch-up backup.
7. Open the main window; load dashboard asynchronously.

### 6.3 Daily sales entry (provisional)

1. User selects customer (or walk-in).
2. Adds products/services with quantity, unit price, discount, tax as applicable.
3. Application calculates line totals and document totals using domain rules.
4. User reviews and confirms.
5. One transaction writes the invoice, lines, stock movements, ledger entries, and audit record.
6. User can print/export a PDF and record payment.
7. Any failure rolls back the whole transaction.

Detailed tax, discount, credit, and return rules are **[OPEN] Q-03, Q-08, Q-09**.

### 6.4 Purchase entry (provisional)

1. Select supplier, add items and costs.
2. Confirm in one transaction; stock and payables update together.
3. Record supplier payments.

### 6.5 Manual backup

1. User chooses **Backup now** and optionally a destination folder.
2. Application creates a temporary backup, verifies it, renames it, and writes metadata.
3. History shows date, mode, size, destination, and verification result.

### 6.6 Restore

1. User selects a backup from history or a file.
2. Application validates the file without touching live data.
3. Application creates a safety backup of the current database.
4. Application closes connections and restores through a staged file + verification.
5. On success, application reopens the database (or restarts itself) and reports the result.
6. On failure, the original database remains intact and the error is logged.

### 6.7 Missing drive

1. Application detects that the configured database path is not reachable.
2. It shows the configured path, the failing reason, and recovery options.
3. It does not create a new database elsewhere.
4. Manual backups on other drives remain usable for restore.

## 7. Proposed modules

Priority: **P0** = required foundation, **P1** = v1 revenue-critical, **P2** = valuable but can follow, **P3** = conditional.

| # | Module | Priority | Status | Notes |
| --- | --- | --- | --- | --- |
| 1 | Dashboard | P1 | Proposed | Summaries and charts; no editing |
| 2 | Customers | P1 | Proposed | Balances, statements |
| 3 | Suppliers | P1 | Proposed | Balances, bills |
| 4 | Products & Services | P1 | Proposed | Categories, units, pricing |
| 5 | Categories & Units | P1 | Proposed | Supporting master data |
| 6 | Purchases | P1 | Proposed | Bills, payments, returns TBD |
| 7 | Sales | P1 | Proposed | Invoices, payments, returns TBD |
| 8 | Inventory | P1 | Proposed | Movement ledger, valuation TBD |
| 9 | Expenses | P1 | Proposed | Categories, payment method |
| 10 | Accounting & Finance | P2 | Proposed | Depth TBD (Q-17) |
| 11 | Reports | P1 | Proposed | PDF/Excel, filters |
| 12 | Users & Roles | P3 | Conditional | Only if multi-user required |
| 13 | Business Settings | P0 | Proposed | Profile, currency, numbering |
| 14 | Backup & Restore | P0 | Proposed | Core product feature |

Rules:

- P0 modules are built before business modules.
- A module is not "done" until its workflows, rules, tests, and exports (if any) are approved.
- Modules must not reach into each other's repositories; cross-module work goes through application services.

## 8. Non-functional requirements

| ID | Requirement | Target |
| --- | --- | --- |
| NFR-01 | Cold start | ≤ 5 s on SSD; ≤ 3 s warm |
| NFR-02 | UI responsiveness | No main-thread operation > 200 ms without progress feedback |
| NFR-03 | Table performance | 10,000-row page/filter response < 500 ms |
| NFR-04 | Transaction safety | Atomic writes; no partial financial documents |
| NFR-05 | Data volume | 100k invoices, 500k lines, 20k products, 10k parties, DB < 2 GB |
| NFR-06 | Backup duration | 500 MB database verified in < 60 s on local SSD |
| NFR-07 | Recovery point | ≤ 24 h with automatic backups; user-defined manual backups |
| NFR-08 | Recovery time | ≤ 15 min for a verified local restore |
| NFR-09 | Availability offline | 100% of features without network |
| NFR-10 | Accessibility | Keyboard reachable; WCAG AA contrast for text |
| NFR-11 | DPI | Usable at 100%, 125%, 150%, 200% |
| NFR-12 | Installability | No Python or developer tools required on target PC |
| NFR-13 | Maintainability | Layered boundaries, typed public interfaces, tests for rules |
| NFR-14 | Observability | Rotating logs for app and backup runner; no silent failures |
| NFR-15 | Portability of data | Standard SQLite file; documented backup format; Excel/PDF exports |

## 9. Technology and constraints

The stack is fixed by the brief and recorded in ARCHITECTURE.md. The following constraints shape the product:

- SQLite has no native fixed-point decimal type; money must be stored exactly as scaled integers.
- SQLite allows one writer at a time; transactions must be short and the app is single-user by design.
- Task Scheduler cannot run a GUI app reliably in the background; the backup runner must be headless.
- A drive letter is not a backup strategy; local backups do not protect against theft, fire, ransomware, or disk failure.
- Windows SmartScreen and antivirus may warn about unsigned installers; code signing is **[OPEN] Q-19**.
- PyInstaller bundles the Python runtime and Qt; build size and antivirus false positives must be tested.

## 10. Development phases (summary)

Full detail, deliverables, and definitions of done are in DEVELOPMENT_ROADMAP.md.

| Phase | Work | Gate |
| --- | --- | --- |
| 0 | Inspection, architecture review, documentation | **Current — stop for approval** |
| 1 | Python environment, project foundation, config, logging | App skeleton runs |
| 2 | Database, SQLAlchemy, Alembic baseline | Empty schema migrates |
| 3 | Setup wizard and database location management | First launch works on D:/E: |
| 4 | Backup and restore, backup runner, Task Scheduler | Verified backup + restore drill |
| 5 | Main shell, theme, reusable components | Navigation shell usable |
| 6 | Authentication (only if approved) | Decision recorded |
| 7 | Master data modules | CRUD + validation complete |
| 8 | Purchases, sales, inventory | End-to-end transaction tests |
| 9 | Accounting and expenses | Ledger consistency tests |
| 10 | Reports and dashboard | Exports match ledger |
| 11 | Testing, security, performance hardening | Release checklist met |
| 12 | PyInstaller + Inno Setup | Clean install on a fresh PC |

## 11. Acceptance criteria

### 11.1 Initialization (this phase)

- [x] Workspace inspected; environment recorded.
- [x] Dependency compatibility checked against official package metadata.
- [x] Seven master documents created and cross-referenced.
- [x] Risks, assumptions, and open questions recorded.
- [x] No business code, schema, or seed data created.
- [ ] Owner approves documents (pending).

### 11.2 Release 1.0 (product level)

- A new Windows PC with no Python can install and launch the app.
- The user can choose a data folder, and the choice survives restarts.
- If the configured drive is missing, the app refuses to start with a clear error and never switches drives.
- Sales, purchases, inventory, expenses, and reports reconcile to the same totals.
- A scheduled backup runs when the app is closed and is verified.
- A restore drill restores a verified backup without losing the pre-restore state.
- All financial calculations use exact decimal rules and are covered by tests.
- No unhandled exception reaches the user as a raw traceback.
- Documentation matches the shipped behaviour.

## 12. Assumptions

| ID | Assumption | Impact if wrong |
| --- | --- | --- |
| A-01 | One business, one currency, one database per installation | Multi-company would change the schema and config |
| A-02 | Single active user at a time | Multi-user would require concurrency and auth redesign |
| A-03 | Currency needs 2 decimal places | Storage scale and rounding would change |
| A-04 | Quantities need up to 3 decimals; unit prices up to 4 | Field scales and invoice math would change |
| A-05 | Default currency is INR (Indian Rupee), 2 decimal places | Formatting, tax, and fiscal year defaults |
| A-06 | English UI is sufficient for v1 | Localization adds a translation layer |
| A-07 | Local SSD/internal drive is the normal database location | Performance and backup assumptions change |
| A-08 | Owner accepts Task Scheduler limitation (runs while user is logged on) | Password storage or a Windows service would be required |
| A-09 | Backup retention of 30 days is acceptable | Retention defaults and disk sizing change |
| A-10 | No statutory audit/certification requirement for v1 | Accounting depth and controls would increase |
| A-11 | Products can be goods and services | Inventory posting rules need a type flag |
| A-12 | Printing to A4 PDF is sufficient initially | Thermal/receipt printing adds a device layer |

## 13. Open questions

Defaults are **not** decisions. Each must be answered before the affected module is implemented.

| ID | Question | Default if unanswered | Blocks |
| --- | --- | --- | --- |
| Q-01 | Currency and decimal places? | INR, 2 decimals | Schema, formatting |
| Q-02 | Multi-currency buying/selling? | No | Schema, calculations |
| Q-03 | Tax/VAT: rates, inclusive or exclusive, per line or per invoice? | No tax in v1 | Sales, purchases, reports |
| Q-04 | Single user or multiple users with login/roles? | Resolved 2026-11-22: multiple local users with four roles | Phase 8B authentication, audit, schema |
| Q-05 | Inventory valuation: FIFO, weighted average, or simple cost? | Weighted average (provisional) | Inventory, COGS, P&L |
| Q-06 | Are negative stock levels allowed? | Block by default | Sales validation |
| Q-07 | Which services/products and units? Area (sq ft), pieces, rolls? | Goods + services with units | Product model, pricing |
| Q-08 | Discounts at line, document, or both? Rounding policy? | Line discount, half-up rounding | Invoice math |
| Q-09 | Credit sales and partial payments? Payment methods? | Yes; cash/bank/mobile | Receivables |
| Q-10 | Invoice numbering: prefix, reset per fiscal year? | `INV-YYYY-000001`, yearly reset | Documents, uniqueness |
| Q-11 | Fiscal year start? | 1 April (Indian fiscal year, April–March) | Reports, numbering |
| Q-12 | Multiple branches or warehouses? | No | Inventory schema |
| Q-13 | Quotations, sales orders, delivery notes? | Not in v1 | Scope |
| Q-14 | Purchase returns and sales returns? | Not in v1 | Scope, inventory |
| Q-15 | Full double-entry accounting or summary ledger? | Summary ledger first | Phase 9 |
| Q-16 | Existing data to import (Excel/other software)? | None | Migration tooling |
| Q-17 | Required print formats: A4 invoice, receipt, statements? | A4 invoice + statement | Report design |
| Q-18 | Encryption at rest required? | No; recommend BitLocker | Security, packaging |
| Q-19 | Code signing certificate available? | No; document SmartScreen warning | Packaging |
| Q-20 | Bengali language or bilingual UI? | English only | UI architecture |
| Q-21 | Off-site/second-device backup requirement? | Manual copy recommended | Backup scope |
| Q-22 | Audit log retention and visibility? | Keep indefinitely, owner-visible | Schema, UI |
| Q-23 | Barcode scanning? | No | Product/UI |
| Q-24 | Attachment types/size limits? | PDF/JPG/PNG, 10 MB each | Storage |
| Q-25 | Should automatic backups also write to a second destination? | No; manual extra copy | Backup runner |
| Q-26 | Warn or block when no verified backup exists for N days? | Warn after 7 days | Backup UX |

## 14. Glossary

| Term | Meaning |
| --- | --- |
| BMS | Business Management System |
| Minor units | Integer amount in the smallest currency unit (e.g., paise for INR) |
| e4 / e3 | Scaled integer with 4 or 3 decimal places |
| Document | A numbered financial record such as an invoice or bill |
| Posting | Writing the accounting/inventory effects of a document |
| Unit of Work | A short transaction scope covering one use case |
| Catch-up backup | A missed automatic backup performed at next startup |
| WAL | SQLite write-ahead logging mode |
| RPO / RTO | Recovery point objective / recovery time objective |
| DoD | Definition of done |
