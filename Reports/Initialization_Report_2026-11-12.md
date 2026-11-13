# Initialization Task Report — Gobindas Graphics BMS

| Field | Value |
| --- | --- |
| Report date | 2026-11-12 |
| Task | Project initialization and master documentation (Phase 0) |
| Status | Completed — awaiting owner review and Phase 1 authorization |
| Workspace | `D:\Development\Gobindas Graphics` |
| Prepared for | Owner / project reviewer |

> **Update (2026-11-13):** Following owner decisions, the default currency is
> confirmed as **INR (2 decimals)** and the fiscal year as **1 April – 31 March
> (Indian fiscal year)**. The affected entries below are annotated; the current
> decisions are recorded in `docs/BLUEPRINT.md` and `docs/DATABASE_SCHEMA.md`.
> The rest of this report remains a historical record of the Phase 0 work.

## 1. Executive summary

The workspace was inspected, the mandated technology stack was checked for compatibility, and all seven master documentation files were created under `docs/`.

No application code, virtual environment, database, schema, migration, seed data, or sample business data was created. No existing file was modified or deleted. The project is stopped at the documented completion boundary.

The two highest-priority follow-ups are:

1. Resolve the blocking business questions (currency, tax, users, inventory valuation, numbering, fiscal year).
2. Authorize Phase 1 — environment and application foundation.

## 2. Scope of work performed

| Task | Result |
| --- | --- |
| Task 1 — Inspect workspace and environment | Completed |
| Task 2 — Architecture review | Completed and recorded in `docs/ARCHITECTURE.md` |
| Task 3 — Create seven master documents | Completed |
| Task 4 — Consistency review | Completed; discrepancies corrected |
| Task 5 — Final report | This document |

## 3. Workspace inspection

### 3.1 Project folder before work

```text
D:\Development\Gobindas Graphics\
└── Prompt\
    └── Project Initialization Prompt — Window.md
```

- The folder was not a Git repository.
- No other project files existed.
- The prompt file was read only; it was not modified.

### 3.2 Development environment

| Item | Observed value |
| --- | --- |
| Operating system | Windows 11 Pro, build 10.0.26300, 16 GB RAM |
| Default Python | CPython 3.14.6, 64-bit |
| pip | 26.1.2 |
| Alternate Python | CPython 3.13.0 (Laragon) |
| Python `sqlite3` version | SQLite 3.50.4 |
| Git | 2.51.0.windows.1 |
| Git identity | Configured (Ram Chowdhury) |
| Drives | C: 12 GB free of 126 GB; D: 221 GB free of 239 GB; E: removable, no media |
| Installed globally | openpyxl 3.1.5, reportlab 5.1.0, pyinstaller 6.22.3 |
| Missing globally | PySide6, SQLAlchemy, Alembic, Pydantic, PyQtGraph, pytest, Inno Setup |

A dedicated virtual environment will be created in Phase 1; global packages will not be reused.

## 4. Compatibility review

Official PyPI metadata was checked on 2026-11-12.

| Package | Latest observed | Declared Python support | Assessment |
| --- | --- | --- | --- |
| PySide6 | 6.12.0 | >=3.10,<3.16 incl. 3.14 | Windows wheel `cp310-abi3-win_amd64`; ABI3 supports 3.14 |
| SQLAlchemy | 2.1.8 | >=3.11 incl. 3.14 | Compatible |
| Alembic | 1.20.1 | >=3.10 incl. 3.14 | Compatible |
| Pydantic | 2.14.3 | >=3.10 incl. 3.14 | Compatible |
| PyQtGraph | 0.14.0 | >=3.10 | Pure Python; depends on NumPy |
| NumPy | 2.5.4 | >=3.12 incl. 3.14 | Compatible |
| ReportLab | 5.1.0 | >=3.9,<4 | Metadata looks unusual; smoke test required |
| OpenPyXL | 3.1.5 | >=3.8 | No 3.14 classifier; pure Python; smoke test required |
| pytest | 9.2.0 | >=3.10 incl. 3.14 | Development only |
| PyInstaller | 6.22.3 | >=3.8,<3.16 incl. 3.14 | Build-time only |

**Recommendation:** build with Python 3.14.6; fall back to Python 3.13.x only if a Phase 1 runtime or packaging test fails. Do not use Python 3.15 at this stage.

## 5. Documentation created

| # | File | Purpose | Lines |
| --- | --- | --- | --- |
| A | `docs/BLUEPRINT.md` | Product vision, scope, workflows, NFRs, assumptions, open questions | 387 |
| B | `docs/ARCHITECTURE.md` | Stack decisions (ADRs), layers, MVVM, lifecycle, errors, logging, packaging | 519 |
| C | `docs/DATABASE_SCHEMA.md` | Storage conventions, exact-money policy, proposed entities, indexes, migrations | 613 |
| D | `docs/UI_UX_BLUEPRINT.md` | Shell, navigation, dashboard, patterns, design tokens, accessibility | 431 |
| E | `docs/BACKUP_STRATEGY.md` | Backup runner, scheduler, verification, retention, restore, relocation | 487 |
| F | `docs/DEVELOPMENT_ROADMAP.md` | Phases 0–12, dependencies, DoD, testing strategy, risks | 525 |
| G | `docs/SECURITY_AND_DATA_PROTECTION.md` | Threat model, permissions, audit, file handling, incident response | 319 |

Total: **3,281 lines** of documentation.

## 6. Important decisions and recommendations

### 6.1 Confirmed constraints

- Native Windows desktop application, offline-first, no web frontend or server.
- PySide6 with Qt Widgets, SQLAlchemy 2, Alembic, Pydantic, Decimal finance, PyQtGraph, ReportLab, OpenPyXL, pytest, PyInstaller, Inno Setup.
- SQLite stored in a user-selected folder, independent of the installation directory.
- Automatic daily backup at 22:00 by default (configurable), plus manual backup and restore.
- Documentation before business implementation; no business modules during initialization.

### 6.2 Proposed technical decisions

| Area | Decision | Reason |
| --- | --- | --- |
| Python | CPython 3.14.6, 64-bit | Installed; all dependencies declare support; 3.13 fallback |
| Architecture | Layered modular monolith | Single-user desktop; simplest maintainable structure |
| Domain model | Pure domain entities/value objects separate from ORM | Exact finance rules testable without database |
| MVVM | Qt-aware ViewModels (QtCore only), no widget imports | Native signals/slots without over-abstraction |
| Money | Integer minor units; prices e4, quantities e3, rates e6 | Exactness; avoids SQLite decimal/REAL problems |
| Rounding | ROUND_HALF_UP at defined boundaries, stored results | Predictable totals; no recomputation from floats |
| DB profile | WAL, `synchronous=FULL`, FK on, 5 s busy timeout | Crash durability and integrity |
| Migrations | Alembic bundled; startup migration with safety backup | Installed app must upgrade itself safely |
| Config | `%APPDATA%\GobindasBMS\config.json` | Independent of data folder; reinstall-safe |
| Logs | `%LOCALAPPDATA%\GobindasBMS\logs` | Keeps logs out of backed-up business data |
| Backups | stdlib `sqlite3` Online Backup API; verify before publish | Consistent snapshot; minimal runner |
| Backup runner | Separate headless executable, no Qt/SQLAlchemy | Works with app closed; smaller failure surface |
| Scheduling | Per-user Task Scheduler + startup catch-up | Avoids stored passwords/services; handles missed runs |
| Restore | Safety backup → close → stage → swap → verify → restart | Satisfies reopen-after-verification with no stale connections |
| Packaging | PyInstaller `--onedir` + Inno Setup; two executables | Faster start, fewer AV issues, headless runner |
| Auth | Conditional; not invented | Depends on owner answer to Q-04 |

## 7. Consistency review performed

Checks completed:

| Check | Result |
| --- | --- |
| All seven documents exist | Pass |
| Technology stack agrees across documents | Pass |
| Database location rules agree | Pass — config outside data root; no silent fallback |
| Backup requirements technically achievable | Pass — with documented Task Scheduler limitation and catch-up fallback |
| Money storage precise and consistent | Pass — corrected worked example to `1,524.14` |
| Module scope not treated as finalized | Pass — tables and modules marked proposed/provisional |
| Phase dependencies clear | Pass |
| Question IDs defined and referenced | Pass — Q-01–Q-26 and SQ-01–SQ-03 all defined; no orphan references |
| UI minimum size consistent | Pass — aligned to 1280×720 |
| Log location consistent | Pass — removed data-root `Logs\` from backup layout |
| Restore free-space rule present | Pass — added |
| Manual backup destination/history documented | Pass — added |

Corrections made during the review:

1. Fixed an incorrect multiplication example in `DATABASE_SCHEMA.md` (correct result: 123.456 × 12.3456 = 1,524.1383936 → 1,524.14).
2. Aligned UI minimum window size to 1280×720 and sidebar collapse threshold to 1360 px.
3. Removed `Logs\` from the business data root to match the `%LOCALAPPDATA%` logging decision.
4. Added restore disk-space preflight, manual backup destination rules, and backup history details.
5. Added Q-25 and Q-26 to the blueprint register.
6. Noted that the Task Scheduler XML executable path is illustrative and install-path dependent.

## 8. Open questions

Blocking decisions:

Q-01 and Q-11 have since been resolved by the owner (2026-11-13); the table
keeps the original Phase 0 provisional defaults with the confirmed values noted.

| ID | Question | Provisional default |
| --- | --- | --- |
| Q-01 | Currency and decimal places? | INR, 2 decimals (confirmed 2026-11-13; originally BDT) |
| Q-03 | Tax/VAT model? | No tax in v1 until confirmed |
| Q-04 | Single user or login/roles? | Single user, no login |
| Q-05 | Inventory valuation method? | Weighted average (provisional) |
| Q-10 | Invoice numbering and reset rule? | `INV-YYYY-000001`, yearly reset |
| Q-11 | Fiscal year start? | 1 April (Indian fiscal year, April–March; confirmed 2026-11-13; originally 1 July) |

Additional open items cover multi-currency, negative stock, units/area pricing, discounts, credit sales, numbering details, branches, quotations/returns, accounting depth, legacy import, print formats, encryption, code signing, language, off-site backup, audit retention, barcodes, attachment limits, second backup destination, and backup-age warnings.

The full register is in `docs/BLUEPRINT.md §13`; security-specific items are in `docs/SECURITY_AND_DATA_PROTECTION.md §17`.

## 9. Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| ReportLab/OpenPyXL compatibility on 3.14 | Medium | Phase 1 import + PDF/XLSX smoke test; pin working versions |
| PyInstaller missing Qt/SQLite plugins | High | Early dry run; explicit plugins; clean-VM test |
| Task Scheduler does not run when logged off | High | Startup catch-up; visible limitation; no stored password |
| Money rounding defects | High | Value objects, golden/property tests, reconciliation queries |
| Backup/restore data loss | Critical | Verification, safety backup, staged swap, rollback, drills |
| Migration failure on upgrade | High | Safety backup, batch migrations, prior-release test database |
| Antivirus/SmartScreen false positives | Medium | Onedir build, code signing if available, vendor report |
| Inno Setup not installed | Low | Install in Phase 12 |
| C: free space only 12 GB | Medium | Keep venv/build outputs on D:; clean artifacts |
| Scope creep toward web/cloud/multi-user | High | Documented non-goals; ADR + phase gate required |
| Single-developer knowledge concentration | High | Docs, ADRs, tests, reproducible build |

## 10. Verification performed

- Inspected the project directory, installed Python versions, pip, Git, OS build, drives, packages, and SQLite version.
- Queried PyPI metadata for ten packages and verified the PySide6 Windows wheel ABI compatibility.
- Created and cross-referenced all seven documents.
- Ran automated checks for question-ID coverage and unresolved placeholder markers.
- Reviewed documents for stack, money, location, backup, module-scope, and phase consistency.
- **No application tests were run** because no application code exists. No claim of runtime functionality is made.
- **No database or schema was created**, and no sample business data was inserted.

## 11. Recommended next step

1. Review the seven documents.
2. Answer the remaining blocking questions Q-03, Q-04, Q-05, and Q-10 (Q-01 and Q-11 were resolved on 2026-11-13).
3. Approve the proposed architecture decisions.
4. Authorize Phase 1: virtual environment, pinned dependencies, configuration, logging, package skeleton, single-instance guard, import-boundary tests, and an empty runnable shell.
5. Initialize Git in Phase 1.

**The project remains stopped at the initialization boundary.**

## 12. Artifact locations

```text
D:\Development\Gobindas Graphics\
├── docs\
│   ├── BLUEPRINT.md
│   ├── ARCHITECTURE.md
│   ├── DATABASE_SCHEMA.md
│   ├── UI_UX_BLUEPRINT.md
│   ├── BACKUP_STRATEGY.md
│   ├── DEVELOPMENT_ROADMAP.md
│   └── SECURITY_AND_DATA_PROTECTION.md
├── Prompt\
│   └── Project Initialization Prompt — Window.md   (unchanged)
└── Reports\
    └── Initialization_Report_2026-11-12.md          (this file)
```
