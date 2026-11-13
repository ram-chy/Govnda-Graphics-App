# DEVELOPMENT_ROADMAP — Gobindas Graphics Business Management System

| Field | Value |
| --- | --- |
| Document | DEVELOPMENT_ROADMAP.md |
| Version | 1.0 |
| Date | 2026-11-12 |
| Status | Draft for review |
| Related | BLUEPRINT.md, ARCHITECTURE.md, DATABASE_SCHEMA.md, BACKUP_STRATEGY.md |

## 1. Principles

1. **Phase by phase.** No phase starts before the previous gate is approved, except explicitly parallel work noted here.
2. **Documentation before code.** A module's rules and fields are approved before its UI or tables are built.
3. **Vertical slices.** Each business module is delivered end to end (schema → service → ViewModel → view → tests → export) rather than as layers across all modules.
4. **Data safety first.** Backup, restore, and migration are built before business data exists.
5. **No speculative modules.** Empty folders or placeholder screens are not progress.
6. **Tests are part of done.** A feature without tests is not done, even if it works manually.
7. **No fake completion.** "Works" means executed and verified, not compiled.

## 2. Phase map and dependencies

```text
Phase 0 ─→ Phase 1 ─→ Phase 2 ─→ Phase 3 ─→ Phase 4 ─→ Phase 5 ─→ Phase 7 ─→ Phase 8 ─→ Phase 9 ─→ Phase 10
                                      │                     │
                                      └──── Phase 6 (conditional, only if auth approved)
                                                                                   └→ Phase 11 ─→ Phase 12
```

- Phase 6 is optional and can run after Phase 5 if authentication is approved.
- Phase 4 depends on Phase 2 (database) and Phase 3 (known data root), not on the full UI.
- Phase 7 (master data) needs the application shell from Phase 5.
- Phase 11 starts after all functional phases; some hardening work (backup drills, accessibility, performance tests) is continuous.

| Phase | Depends on | Can run in parallel with |
| --- | --- | --- |
| 0 | — | — |
| 1 | 0 approval | — |
| 2 | 1 | UI theme exploration (no production code) |
| 3 | 2 | Backup core prototype (temp DBs only) |
| 4 | 2, 3 | Phase 5 shell |
| 5 | 1 | Phase 4 backend |
| 6 | 5 (if approved) | Phase 7 |
| 7 | 5 | Phase 6 |
| 8 | 7 | — |
| 9 | 8 | Report queries |
| 10 | 8, 9 | Dashboard polish |
| 11 | 7–10 | Packaging dry runs |
| 12 | 11 | — |

## 3. Phase details

### Phase 0 — Inspection and master documentation

**Status: completed (pending owner approval).**

Deliverables:

- Workspace/environment inspection.
- Compatibility review.
- Seven master documents under `docs/`.
- Risk, assumption, and open-question registers.
- Consistency review and final report.

Definition of done:

- [x] No existing files modified or deleted.
- [x] No business code, schema, migration, or sample data created.
- [x] Documents agree on stack and constraints.
- [x] Backup feasibility and money-storage policy documented.
- [x] Open questions are explicit.
- [ ] Owner approval to proceed to Phase 1.

**Gate:** written approval of the documentation and confirmation of Q-01, Q-03, Q-04, Q-05, Q-10, Q-11 at minimum (or acceptance of defaults marked provisional).

### Phase 1 — Python environment and application foundation

**Status: completed (2026-11-13); awaiting owner review before Phase 2.**

Goal: a reproducible development environment and a runnable, testable app skeleton with no business features.

Work:

- Create `.venv` using CPython 3.14.6 (fallback 3.13 if smoke test fails).
- Create `pyproject.toml` (project metadata, tooling config) and pinned `requirements.txt` / `requirements-dev.txt`.
- Install the seven runtime dependencies plus pytest; run import and version smoke tests.
- Confirm PySide6 creates a `QApplication` and a minimal `QMainWindow` offscreen; confirm ReportLab generates a one-page PDF; confirm PyOpenXL writes a workbook; confirm PyQtGraph imports with NumPy.
- Create the package structure from ARCHITECTURE.md, but only files that are used.
- Implement `app/core/config.py` (load/validate/atomic write), `paths.py`, `exceptions.py`, `constants.py`.
- Implement logging setup and the global excepthook.
- Implement application entry point, `AppContext` wiring, single-instance guard, and an empty shell window with theme placeholder.
- Add `.gitignore`, `README.md` (run/build/test instructions), and initialize Git.
- Add import-boundary test (domain must not import Qt/SQLAlchemy) and a smoke test that starts the app offscreen.

Deliverables:

- Fresh clone + documented commands reproduce the environment.
- App launches and exits cleanly; logs are written.
- Dependency versions recorded in ARCHITECTURE.md §2.3.

DoD:

- [x] `python -m app.main` starts the skeleton without errors.
- [x] `pytest` passes.
- [x] Config round-trips with atomic write; corrupt config is handled.
- [x] No business tables or modules exist.
- [x] Locked versions are reproducible from a clean venv.

**Gate:** architecture walkthrough of the skeleton; approval to create the database layer.

**Phase 1 completion notes (2026-11-13):**

- Python 3.14.6 in `.venv`; exact versions locked in `requirements.txt` and recorded in ARCHITECTURE.md §2.3 and §16.1.
- `ruff check app tests`: all checks passed. `pytest`: 147 passed. `python -m app.main --smoke-test`: exit code 0 with a clean startup/shutdown log.
- Full report: `Reports/PHASE_01_REPORT.md`.
- **Currency decision:** INR is confirmed as the default currency. `BLUEPRINT.md` (A-05, Q-01) and `DATABASE_SCHEMA.md` were updated on 2026-11-13 to match the Phase 1 implementation, so there is no remaining currency-documentation conflict.
- **Phase 2 dependencies:** a confirmed data-folder policy from Phase 3 remains later, but Phase 2 needs only a test/temp database path; approval to introduce SQLAlchemy, Alembic, `UnitOfWork`, and platform-only tables.

### Phase 2 — SQLite, SQLAlchemy, and Alembic foundation

Goal: a schema that can be created and upgraded safely, with no business tables yet beyond platform scaffolding.

Work:

- Engine factory with the PRAGMAs from ADR-008 and a `connect` event.
- Naming convention, declarative base, metadata.
- `UnitOfWork` and session factory; repository protocol base.
- Alembic programmatic setup, `render_as_batch=True`, initial revision with `app_settings` / `business_profile` / `alembic_version` only (or an empty baseline — decide and document).
- Migration runner used at startup and by a CLI (`python -m app.tools.migrate`).
- Integrity checks (`quick_check`, `foreign_key_check`) as reusable functions.
- Test fixtures: temp-file DB, applied migrations, rollback isolation.
- Startup refuse-newer-schema / backup-before-upgrade logic is stubbed and tested with fake revisions.

Deliverables:

- A temp DB can be created, migrated to head, inspected, and upgraded in tests.
- SQLAlchemy sessions are never shared across threads (test or lint rule).
- Schema revision is visible in logs and the About dialog.

DoD:

- [ ] Migration from empty → head is deterministic.
- [ ] Foreign keys are enforced (test a violating insert).
- [ ] WAL and `synchronous` settings are verified on a real connection.
- [ ] Failed migration leaves the DB unchanged (transactional DDL test where possible).
- [ ] Naming conventions produce stable constraint names.

**Gate:** database foundation review; approval of the first real schema slice.

### Phase 3 — First-launch setup and database location

Goal: the user can choose a data folder, and the app remembers it safely.

Work:

- Setup wizard views/ViewModels: welcome, folder picker, validation results, confirmation, completion.
- Validation service: path syntax, creatability, write test, free space, drive type, installation-directory refusal, UNC refusal.
- Data folder scaffolding (`Database`, `Backups/{Automatic,Manual,Safety}`, `Attachments`, `Exports/{PDF,Excel}`).
- Database initialization + migrations.
- Atomic config write; config repair flow.
- Restore-existing-backup branch (can be a placeholder that validates and stages until Phase 4 if necessary; do not fake it).
- Missing-drive handling at startup (blocking state).
- Business profile setup (minimum confirmed fields only).
- Logging of path decisions without leaking sensitive content.

Deliverables:

- First launch on a clean profile works on D: and on a removable drive (tested).
- The selected path survives restart and is not stored inside the data folder.
- No fallback to C: ever occurs.

DoD:

- [ ] Permission-denied, nonexistent, read-only, UNC, and installation-folder paths are rejected with clear messages.
- [ ] Free-space check works (mock a low-space condition).
- [ ] Config is written only after the DB is created and verified.
- [ ] A corrupt config does not delete or move business data.
- [ ] Missing drive blocks startup and offers Retry/Locate/Exit.
- [ ] Tests cover validation and config atomicity.

**Gate:** end-to-end first-run demo; approval for backup implementation.

### Phase 4 — Backup, restore, and scheduled runner

Goal: trustworthy protection before any real business data is entered.

Work:

- Backup core on stdlib `sqlite3`: preflight, Online Backup, verification, hash, atomic publish, sidecar metadata, history recording.
- Backup lock and stale-lock recovery.
- Manual backup UI + history (list, verify, open folder, delete manual with confirmation).
- Retention job and preview.
- Headless `backup_runner` entry point and PyInstaller spec (early dry run).
- Task Scheduler create/update/verify/remove with the limitations from BACKUP_STRATEGY.md §6.
- Startup catch-up logic and failure marker handling.
- Restore workflow with safety backup, staging, swap, verification, restart, rollback.
- Database relocation workflow.
- Fault-injection tests and the manual drill.

Deliverables:

- A verified backup can be created while the app is open and while it is closed.
- Restore drill passes on a database with representative data.
- Missing-drive and corrupt-backup scenarios are handled.

DoD:

- [ ] Backup uses the Online Backup API (code review + test proves WAL content is included).
- [ ] Every published backup passes integrity and foreign-key checks.
- [ ] No overwrite path exists (unique names, exclusive create).
- [ ] Lock prevents concurrent backups (test with two processes).
- [ ] Restore always has a safety backup or typed confirmation when impossible.
- [ ] Failed restore preserves the original DB.
- [ ] Task creation failure produces a working startup-catch-up fallback and a clear UI notice.
- [ ] Manual drill recorded with timings and results.

**Gate:** data-protection review; approval to build the UI shell.

### Phase 5 — Main interface, theme, and reusable components

Goal: the shell and design system that every module uses.

Work:

- Token module, light/dark QSS generator, system-theme detection, runtime switch.
- Main window, sidebar, top bar, status bar, navigation registry, lazy views.
- Base ViewModel, worker/thread helper, error presenter, toast/banner.
- `DataTable` + base table model, filter bar, pagination, empty/error/loading states.
- Form primitives (text, money, quantity, date, party, product pickers), validation display.
- Confirm dialog, busy overlay, page header, KPI/card components.
- Window geometry/state persistence with multi-monitor safety.
- UI smoke tests and a development gallery (not shipped).
- Dashboard skeleton with placeholder data (clearly labelled; not fake business data in the DB).

Deliverables:

- A navigation shell with a working dashboard shell and one demo list/form using fake in-memory data (not seed data in the database).
- Both themes usable at 100% and 150% DPI.

DoD:

- [ ] No module hard-codes colors/fonts outside tokens.
- [ ] Table sorting/filtering/pagination works on a synthetic 10k-row dataset without blocking.
- [ ] Keyboard-only navigation works for the shell.
- [ ] All components handle loading/empty/error.
- [ ] ViewModels are testable without widgets.

**Gate:** UI/UX review against UI_UX_BLUEPRINT.md; approval for master data.

### Phase 6 — Authentication and users (conditional)

**Only if Q-04 requires it.** If single-user, record "not applicable" and skip.

Work:

- Confirm roles, permissions, and approval rules.
- Password hashing (Argon2id preferred; dependency decision), lockout/throttling, first-admin setup.
- Users/roles tables, login screen, session in memory, idle lock.
- Audit actor propagation; permission checks in application services (not only UI).
- Admin screens; password reset by owner with a documented recovery path.

DoD:

- [ ] No plaintext or reversible password storage.
- [ ] Permission checks are enforced in services and covered by tests.
- [ ] Login/logout/idle-lock flows work.
- [ ] Audit records identify the actor.
- [ ] Recovery when the only admin password is lost is documented and tested.

**Gate:** security review of the auth model.

### Phase 7 — Business master data

Goal: the reference data needed by transactions.

Work (one vertical slice at a time):

- Customers: list, create/edit, deactivate, search, opening balance policy.
- Suppliers: same.
- Units and categories.
- Products/services: pricing, tax defaults, inventory flag, units/conversions, active state.
- Business settings: profile, currency, fiscal year, numbering.
- Audit logging for master changes.
- Import/export only if Q-16 requires it.

DoD per entity:

- [ ] Approved fields and validation.
- [ ] List with search/filter/pagination.
- [ ] Create/edit/deactivate with duplicate prevention.
- [ ] Referential safety (cannot deactivate/delete when history exists).
- [ ] Domain/service tests and UI smoke tests.
- [ ] Audit record for changes.
- [ ] Money/price values round-trip exactly.

**Gate:** master data demo; approval for transaction modules.

### Phase 8 — Purchases, sales, and inventory

Goal: the core operational loop with correct posting.

Work:

- Numbering service.
- Purchase bills and lines; supplier payments/allocations.
- Sales invoices and lines; customer payments/allocations.
- Price/discount/tax calculations via domain calculators.
- Stock movement ledger and posting; valuation method per Q-05.
- Negative-stock policy per Q-06.
- Void/correction flows (no hard delete).
- Transactional use cases with rollback tests.
- Invoice PDF (ReportLab) and print preview.
- Returns/orders only if approved (Q-13/Q-14).

DoD:

- [ ] One use case = one transaction; failure leaves no partial rows.
- [ ] Totals match domain calculations and stored line values.
- [ ] Stock balance reconciles to movement ledger.
- [ ] Payment allocations never exceed balances; overpayment rules explicit.
- [ ] Void reverses effects correctly and is audited.
- [ ] Invoice numbering is unique and gap-free per policy.
- [ ] Golden-file tests for PDF totals/format.
- [ ] Concurrency/lock tests for two windows/processes.

**Gate:** end-to-end buy → stock → sell → pay demo with reconciliation.

### Phase 9 — Accounting and expenses

Goal: expenses and the approved accounting depth.

Work:

- Expense categories and expenses (with attachments).
- Chart of accounts, journal entries/lines (if Q-15 approves double-entry), fiscal periods.
- Posting maps from sales/purchases/payments/expenses.
- Trial balance, P&L, balance sheet (scope per Q-15).
- Reconciliation reports and invariant checks.

DoD:

- [ ] Debits equal credits per entry and across the ledger.
- [ ] Every financial document produces the approved ledger effects exactly once.
- [ ] Voiding produces reversing entries, not deletions.
- [ ] Closed periods reject postings.
- [ ] Reports reconcile to document totals.
- [ ] Expense attachments validate type/size and are stored safely.

**Gate:** accountant/owner review of reports and posting rules.

### Phase 10 — Reports and dashboard

Goal: decision-support views with exports.

Work:

- Report service with parameter objects and DTOs.
- Report library: sales, purchases, stock, receivables, payables, expenses, P&L, trial balance.
- PDF/Excel export with filters and consistent totals.
- Dashboard metrics and charts (PyQtGraph) with empty/error states.
- Export history/location handling; no silent overwrite.

DoD:

- [ ] Every report has defined parameters and a deterministic total.
- [ ] PDF/Excel totals match the on-screen numbers.
- [ ] Large exports run off the UI thread with progress/cancel.
- [ ] Charts handle no-data and large ranges.
- [ ] Export files are written atomically and never overwrite silently.
- [ ] Report queries are indexed and measured.

**Gate:** report sign-off by the owner.

### Phase 11 — Testing, security, and performance hardening

Goal: release-candidate quality.

Work:

- Raise domain/service coverage; add property tests for money/rounding.
- Full backup/restore/migration drill on a realistic database.
- Security review: permissions, config, logs, attachments, secrets, audit.
- Performance profiling: startup, invoice save, list queries, reports, backup.
- Accessibility pass (keyboard, contrast, screen reader names, DPI).
- Error-message review; ensure no raw tracebacks or SQL reach users.
- Dependency audit and pinning; license notices.
- Documentation update to match implemented behaviour.

DoD:

- [ ] Domain coverage ≥ 90%; financial services ≥ 85%; no critical untested money path.
- [ ] No high-severity security findings open.
- [ ] Performance targets from BLUEPRINT.md NFRs met or deviations documented.
- [ ] Backup restore drill passes with the release build.
- [ ] Accessibility checklist passed for all screens.
- [ ] All known defects triaged.

**Gate:** release candidate approved.

### Phase 12 — Packaging and installer

Goal: install on a clean Windows PC without Python.

Work:

- PyInstaller GUI spec (`--onedir`, windowed) with Alembic scripts, themes, icons, version info.
- PyInstaller backup runner spec (no Qt).
- Inno Setup script: install per-user (preferred) or per-machine, shortcuts, uninstaller, file associations none.
- First-run behavior, upgrade-in-place, uninstall data-safety rules.
- Clean-VM test on Windows 10 and 11 (no Python, no dev tools).
- Antivirus/SmartScreen check; code-sign if available (Q-19).
- Release checklist, checksums, release notes, rollback plan.

DoD:

- [ ] Installer installs and launches on a clean VM.
- [ ] Uninstall does not delete the data folder.
- [ ] Upgrade preserves config and data; migrations run correctly.
- [ ] Backup runner scheduled task works from the installed path.
- [ ] No development dependencies or source paths are required at runtime.
- [ ] Build is reproducible from documented commands.
- [ ] Checksums published; release notes list known limitations.

**Gate:** owner acceptance test on a real machine.

## 4. Cross-phase deliverables

| Area | When |
| --- | --- |
| README with setup/run/test/build | Phase 1, updated each phase |
| ADRs updated for decisions | Continuous |
| Open-question register resolved | Before affected phase |
| Backup drill | Before first real data (Phase 4), before release (Phase 11) |
| Migration test on prior release | Every release after 1.0 |
| Accessibility checklist | Every screen |
| Performance measurement | Phase 5 baseline, Phase 11 final |
| Release notes / known issues | Phase 12 |

## 5. Testing strategy

### 5.1 Test pyramid

| Level | Scope | Tools | Target |
| --- | --- | --- | --- |
| Unit | Money, rounding, totals, rules, validation, retention logic | pytest | Fast, no IO |
| Integration | Repositories, UoW, migrations, backup/restore, exports | pytest, temp SQLite files | Real SQLite, no mocks for DB |
| ViewModel | State transitions, validation mapping, formatting | pytest + pytest-qt | No widgets where possible |
| UI smoke | Every view constructs, binds, and destroys cleanly | pytest-qt | No business mutation |
| End-to-end | Setup → sale → backup → restore → report | Scripted test + manual | Per release |
| Packaging | Install, launch, scheduled backup, upgrade, uninstall | Manual checklist on clean VM | Per release |

### 5.2 Rules

- Never use the production database in tests.
- Use temp-file SQLite (WAL behaviour matters); in-memory DB only for pure schema tests.
- Clock and ID generation are injected; no sleeps in tests.
- Do not mock the domain; test it directly.
- Every bug fix gets a regression test.
- Financial calculators use table-driven and property-style cases (boundaries, rounding halves, negatives, zero, large values).
- Backup tests include failure injection and process-level locking.
- UI tests run offscreen; screenshots are for review, not assertions, unless pixel checks are stable.

### 5.3 Continuous quality (local, no CI required)

- `pytest` before each commit.
- A single `scripts/check.ps1` runs lint/format/tests/import boundaries.
- No merge with failing tests.
- Coverage is inspected for money and posting modules, not chased globally.

## 6. Definition of done (generic)

A deliverable is done only when:

1. Approved requirements exist and are referenced.
2. Code follows the layering and naming rules.
3. Money uses value objects and integer storage; no floats.
4. Errors are handled and user messages are actionable.
5. Tests cover the happy path, validation failures, and the main edge cases.
6. The UI has loading/empty/error states and works in both themes.
7. Audit requirements are met.
8. Documentation is updated.
9. The feature was executed manually and the result recorded.
10. No known data-loss or corruption path remains.

## 7. Risks and mitigations

| ID | Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| R-01 | Business requirements remain unclear, causing rework | High | High | Resolve Q-register before each module; build thin vertical slices; document assumptions |
| R-02 | Money rounding bugs corrupt totals | Medium | High | Value objects, golden tests, SQL reconciliation reports, code review |
| R-03 | Backup/restore failure destroys data | Low | Critical | Online Backup API, verification, safety backup, staged swap, drills |
| R-04 | ReportLab or another dependency fails on Python 3.14 | Medium | Medium | Phase 1 smoke tests; fallback to 3.13 or compatible version; record ADR |
| R-05 | PyInstaller build misses Qt/SQLite plugins | Medium | High | Early packaging dry run in Phase 4; clean-VM tests; explicit hidden imports |
| R-06 | Task Scheduler restrictions prevent automatic backup | Medium | High | Startup catch-up fallback; clear UI notice; document limitation |
| R-07 | Antivirus/SmartScreen blocks installer | Medium | Medium | Onedir build, signing if available, vendor false-positive report, release notes |
| R-08 | Inno Setup not installed on dev machine | High | Low | Install in Phase 12; document prerequisite; no earlier dependency |
| R-09 | Low free space on C: (≈12 GB) affects builds | Medium | Medium | Keep venv/builds on D:, clean build artifacts, monitor |
| R-10 | SQLite locking under two app instances | Low | Medium | Single-instance mutex, backup lock, busy timeout, tests |
| R-11 | Schema migration failure on upgrade | Medium | High | Safety backup, transactional/batch migrations, prior-release test DB |
| R-12 | Scope creep (web, cloud, multi-user) | High | High | Non-goals in BLUEPRINT.md; ADR required; phase gates |
| R-13 | Single developer bus factor | Medium | High | Documentation, ADRs, tests, reproducible build, no hidden knowledge |
| R-14 | Reports disagree with documents | Medium | High | Shared domain totals; reconciliation invariants; golden tests |
| R-15 | UI becomes slow with large data | Medium | Medium | Pagination, projections, indexes, early 10k-row benchmark |
| R-16 | Sensitive data exposed in logs/exports | Low | High | Logging rules, redaction, attachment permissions, review |
| R-17 | Qt/PySide6 licensing compliance | Low | Medium | Include LGPL notices, allow relinking, legal review before sale |
| R-18 | Power loss during sale/backup | Low | High | `synchronous=FULL`, atomic files, transaction tests, crash recovery |
| R-19 | Owner uses OneDrive/network sync on live DB | Medium | High | UI warnings, detection of sync paths, documentation |
| R-20 | Currency/tax assumptions wrong | Medium | High | Answer Q-01/Q-03 before schema freeze; schema supports explicit scales |

## 8. Release checklist (preview)

- [ ] All phase gates signed off.
- [ ] Version numbers updated in app, installer, metadata.
- [ ] Backup/restore drill passed on the release build.
- [ ] Migration tested from the previous release.
- [ ] Clean-VM install/upgrade/uninstall passed.
- [ ] No sample/demo business data in the shipped database.
- [ ] Logs contain no sensitive payloads.
- [ ] Documentation matches behaviour; known limitations listed.
- [ ] Checksums and release notes prepared.
- [ ] Owner acceptance test completed.

## 9. Post-1.0 candidates (not committed)

- Database relocation improvements and scheduled off-site copy.
- Encrypted database/backups (Q-18).
- Barcode scanning, thermal receipts.
- Quotations/orders/returns if deferred.
- Bengali/bilingual UI (Q-20).
- Import from legacy Excel/software (Q-16).
- Multi-user/server edition (requires a different architecture; not this app).

## 10. Immediate next step

Phase 1 is complete (2026-11-13) and recorded in `Reports/PHASE_01_REPORT.md`. The owner confirmed INR as the default currency, and the affected documentation was reconciled on 2026-11-13. Review the report and authorize **Phase 2 — SQLite, SQLAlchemy, and Alembic foundation**. Do not start Phase 2 without explicit approval.
