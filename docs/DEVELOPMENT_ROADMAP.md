# DEVELOPMENT_ROADMAP — Gobindas Graphics Business Management System

| Field | Value |
| --- | --- |
| Document | DEVELOPMENT_ROADMAP.md |
| Version | 1.10 |
| Date | 2026-11-18; Phase 7A and Phase 7B added 2026-11-20; Phase 7C verification added 2026-11-22; Phase 8A specification added 2026-11-22; Phase 8B implementation added 2026-11-23; Phase 9 Customer & Supplier Management implemented 2026-11-23 |
| Status | Phases 0–7 complete; Phase 7A and Phase 7B Business Profile correction implemented; Phase 7C verification complete with owner acceptance pending; Phase 8A specification approved; Phase 8B authentication/authorization implemented with owner review pending; Phase 9 Customer & Supplier Management implemented per approved prompt with owner review pending; other business decisions remain open |
| Related | BLUEPRINT.md, ARCHITECTURE.md, DATABASE_SCHEMA.md, BACKUP_STRATEGY.md, BUSINESS_REQUIREMENTS.md, BUSINESS_WORKFLOWS.md, MODULE_SPECIFICATIONS.md, BUSINESS_RULES.md, REPORTING_REQUIREMENTS.md, OPEN_DECISIONS.md, PHASE_07_OWNER_DECISION_WORKSHEET.md, PHASE_07_FIRST_MODULE_SPECIFICATION.md, PHASE_07_IMPLEMENTATION_READINESS.md, AUTHENTICATION_SPECIFICATION.md, AUTHORIZATION_MATRIX.md, USER_ACCOUNT_WORKFLOWS.md, SESSION_AND_IDLE_LOCK_SPECIFICATION.md, PHASE_08_OWNER_DECISION_WORKSHEET.md, PHASE_08_IMPLEMENTATION_READINESS.md |

## Phase 7B status (authoritative)

Phase 7B corrects the Business Profile slice after Phase 7A. The corrected slice has six mandatory fields including a managed logo, three optional fields, immutable version history, durable profile audit events with `system/unauthenticated`, migration `0003_business_profile_requirements`, and managed logo preservation through backup, restore, and relocation. Phase 8 may depend on the corrected profile data and header rules. Earlier Phase 7A-only statements about text-only scope, no history, no logo, and no audit are historical and superseded for this slice only.

## Phase 7C status (verification only)

Phase 7C verified the corrected Business Profile slice on Windows without modifying application code or the owner's live database. Automated tests and Ruff passed, isolated profile/logo/history/audit/backup/restore/relocation/startup checks passed, and native Windows UI rendering was captured at 100%, 125%, and 150% scaling in both themes. Scheduled-task execution, owner visual review, and owner acceptance remain pending; see `Reports/PHASE_07C_REPORT.md`. This status does **not** mark the module owner-accepted.

## Phase 8A status (specification gate — historical record)

Phase 8A was the authentication/authorization **requirements finalization and technical specification** gate. It produced seven planning documents (authentication specification, authorization matrix, account workflows, session/idle-lock specification, owner decision worksheet, implementation readiness, and `Reports/PHASE_08A_REPORT.md`) and updated `OPEN_DECISIONS.md`. Phase 8A itself was **planning/specification work only**: no login, password hashing, user management, role/permission checks, schema, migration, seed user, audit change, or owner database change was made. All owner decisions (`P8A-01`–`P8A-08`, `Q-22`, `B6-10`) were resolved, the owner explicitly approved the complete specification/matrix and hashing design on 2026-11-22, Phase 7D owner acceptance was recorded 2026-11-22 (`Reports/PHASE_07D_ACCEPTANCE.md`), and the final parameter review was complete. The Phase 8A "NOT READY / do not implement" statements remain accurate for that gate and were superseded when the owner explicitly authorized Phase 8B implementation on 2026-11-22.

## Phase 8B status (implementation complete — owner review pending)

Phase 8B implemented the approved authentication slice in isolated, uncommitted work. It added Argon2id hashing with a scrypt fallback, first-run owner creation, local accounts and password workflows, exactly four roles, service-layer authorization, failed-login throttling, an in-memory session with idle lock, startup/login/lock dialogs, append-only authentication audit events, and migration `0004_authentication`. Only `A`-marked permissions are implemented; `P`/`O` permissions, approval workflows, new business modules, default users, cloud/OTP recovery, and new roles remain out of scope. See `Reports/PHASE_08B_REPORT.md` for scope, verification commands, exact results, limitations, and the pending owner acceptance checklist.

## Phase 9 status (Customer & Supplier Management, per prompt — implementation complete, owner review pending)

Phase 9 implemented the approved Customer & Supplier master-data slice per `Prompt/Phase 9 — Customer & Supplier Management.md`. Scope is intentionally limited to basic party identity/contact records (name required; phone, email, address, contact person, notes, is_active optional), search/list, create/edit, duplicate warning with explicit confirmation, activate/deactivate, service-layer authorization, and append-only audit events. No financial ledger/opening balance/credit/tax/transaction behavior, no hard delete, and no sample/seed data in the real DB were added. Migration `0005_party_master` adds the `parties` table. The pre-existing roadmap section labeled "Phase 9 — Accounting and expenses" remains the earlier planning label and is not implemented by this slice; owner/roadmap reconciliation may be needed. See `Reports/PHASE_09_REPORT.md`.

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
Phase 0 ─→ Phase 1 ─→ Phase 2 ─→ Phase 3 ─→ Phase 4 ─→ Phase 5 ─→ Phase 6 ─→ Phase 7 planning/gate ─→ Phase 7A Business Profile ─→ Phase 8 ─→ Phase 9 ─→ Phase 10 ─→ Phase 11 ─→ Phase 12

Historical/deferred auth candidate (formerly Phase 6):
Q-04 / AQ-05 decision ─→ renumbered auth phase, only if required
```

- Phase 6 is the completed business requirements, workflows, and module-planning documentation phase. It is not authentication implementation.
- Phase 7 was the owner-decision and first-module specification approval gate. It was documentation-only; its gate passed on 2026-11-20 for the minimal slice.
- Phase 7A is the approved first business module: Business Settings — Business Profile only. Other modules remain blocked by their own decisions.
- The historical authentication phase is no longer deferred. Phase 8A completed its specification only; Phase 8B implemented that approved specification after explicit owner authorization on 2026-11-22. Future business modules still require their own module-specific decisions and approvals.
- Phase 4 depends on Phase 2 (database) and Phase 3 (known data root), not on the full UI.
- Business master-data implementation needs the application shell from Phase 5 and owner approval of the module-specific rules in `OPEN_DECISIONS.md`.
- Phase 11 starts after all functional phases; some hardening work (backup drills, accessibility, performance tests) is continuous.

| Phase | Depends on | Can run in parallel with |
| --- | --- | --- |
| 0 | — | — |
| 1 | 0 approval | — |
| 2 | 1 | UI theme exploration (no production code) |
| 3 | 2 | Backup core prototype (temp DBs only) |
| 4 | 2, 3 | Phase 5 shell |
| 5 | 1 | Phase 4 backend |
| 6 | 5 and explicit Phase 6 authorization | Owner review of remaining open decisions |
| 7 planning/gate | 6 and explicit Phase 7 authorization | Review of non-blocking decisions |
| 7A Business Profile | Approved first-module spec and readiness PASS | Deferred auth decision |
| 8 | 7A and approved transaction rules | Report query planning |
| 9 | 8, approved accounting depth | Report queries |
| 10 | 8, 9, approved report definitions | Dashboard polish |
| 11 | First business implementation through 10 | Packaging dry runs |
| 12 | 11 | — |
| Deferred auth | Q-04/AQ-05 approval | Later module work depending on affected rules |

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

**Status: Complete (2026-11-13).** Report: `Reports/PHASE_02_REPORT.md`.

Goal: a schema that can be created and upgraded safely, with no business tables yet beyond platform scaffolding.

Work:

- [x] Engine factory with the PRAGMAs from ADR-008 and a `connect` event.
- [x] Naming convention, declarative base, metadata.
- [x] `UnitOfWork` and session factory; repository protocol base.
- [x] Alembic programmatic setup, `render_as_batch=True`; an **empty baseline** was chosen and documented (`0001_baseline`: identity PRAGMAs only, no `app_settings`/`business_profile`).
- [x] Migration runner used by a CLI (`python -m app.tools.migrate`); startup inspection and refusal policy are implemented, automatic upgrade awaits Phase 4.
- [x] Integrity checks (`quick_check`, `foreign_key_check`) as reusable functions.
- [x] Test fixtures: temp-file DB, applied migrations, rollback isolation.
- [x] Startup refuse-newer-schema logic; pending revisions are refused rather than upgraded until the Phase 4 safety backup exists.

Deliverables:

- [x] A temp DB can be created, migrated to head, inspected, and upgraded in tests.
- [x] SQLAlchemy sessions are never shared across threads (bounded pool + documented policy + tests).
- [x] Schema revision is visible in startup logs. A UI About surface remains future work.

DoD:

- [x] Migration from empty → head is deterministic.
- [x] Foreign keys are enforced (a violating insert is rejected in tests).
- [x] WAL and `synchronous` settings are verified on a real connection.
- [x] Failed upgrade leaves the DB unchanged (invalid target revision test; SQLite cannot make all DDL transactional).
- [x] Naming conventions produce stable constraint names.

**Gate:** database foundation review; approval of the first real schema slice.

**Phase 3 dependencies delivered by Phase 2:**

- Injected absolute `DatabaseConfig` and `AppConfig.database_path` (default `null`).
- Explicit database creation via `MigrationManager.create_database()`; no implicit creation.
- Startup identity/revision checks that a future wizard can reuse.
- `DatabaseDiagnostics` for location validation and health display.
- No default database path, no C: fallback, and no silent switch to another file.

Phase 3 still owns the folder chooser, write-permission UX, save/validate flow, and
remembering the selected location.

### Phase 3 — First-launch setup and database location

**Status: complete (2026-11-14).** Recorded in `Reports/PHASE_03_REPORT.md`.

Goal: the user can choose a data folder, and the app remembers it safely.

Work:

- Setup wizard pages: welcome, folder picker, validation results, directory review, confirmation, initialization progress, completion.
- Validation service: path syntax, absoluteness, creatability, write probe, read access, free space, drive type, protected-folder refusal, installation-directory refusal, UNC refusal, and drive-root refusal.
- Data folder scaffolding (`Database`, `Backups/{Automatic,Manual,Safety}`, `Attachments`, `Exports/{PDF,Excel}`).
- Database initialization through the Phase 2 migration manager, plus safe adoption of an existing healthy database.
- Atomic config write of `data_root` and `database_path`; configuration repair flow.
- Missing-drive, corrupt-config, and incomplete-config recovery with Retry / Locate existing data / Start new setup / Exit.
- Logging of path decisions without leaking sensitive content.
- Restore existing backup remains Phase 4 work and was deliberately not faked.
- Business-profile setup remains deferred because no field list is approved.

Deliverables:

- First launch on a clean profile works on a local fixed or removable drive (tested with mocked drive APIs).
- The selected path survives restart and is not stored inside the data folder.
- No fallback to C: occurs.

DoD:

- [x] Permission-denied, nonexistent, read-only, UNC, drive-root, and installation-folder paths are rejected with clear messages.
- [x] Free-space check works (mock a low-space condition).
- [x] Config is written only after the DB is created and verified.
- [x] A corrupt config does not delete or move business data.
- [x] Missing drive blocks startup and offers Retry/Locate/New setup/Exit.
- [x] Tests cover validation and config atomicity.

**Gate:** end-to-end first-run demo; approval for backup implementation.

**Phase 4 dependencies delivered by Phase 3:**

- A verified data root containing `Database`, `Backups/{Automatic,Manual,Safety}`,
  `Attachments`, and `Exports/{PDF,Excel}`.
- `AppConfig.data_root` and the explicit absolute `AppConfig.database_path`.
- A verified, open `Database` lifecycle and clean shutdown path.
- Startup setup/recovery classification and a blocking recovery dialog that
  already never falls back to another path.
- The existing location validator for a future backup-destination check.
- No restore action, no backup field, and no scheduling claim is present in
  Phase 3; Phase 4 must add them.

### Phase 4 — Backup, restore, and scheduled runner

**Status: complete (2026-11-16).** Report: `Reports/PHASE_04_REPORT.md`.

Goal: trustworthy protection before any real business data is entered.

Work completed:

- Backup core on stdlib `sqlite3`: preflight, SQLite Online Backup API snapshot,
  independent verification, SHA-256, JSON sidecar metadata, atomic publish, and
  state/history recording.
- Cross-process operation lock with stale-lock recovery only after the owning
  process is proven inactive.
- Native PySide6 backup view: manual backup, history, verification status,
  progress, schedule/retention settings, restore, and relocation actions.
- Retention service for managed automatic backups with safety/manual protection
  and verified-backup preservation rules.
- Headless `python -m app.tools.backup` runner (stable exit codes; packaged build
  dispatch via `--run-backup`) and retention after successful runs.
- Windows Task Scheduler create/update/query/remove integration with post-action
  verification and no silent success on rejection.
- Startup catch-up evaluation/execution for missed automatic backups, avoiding
  duplicate same-day backups and respecting the operation lock.
- Staged restore workflow: eligibility re-verification, safety backup, runtime
  shutdown, staged replacement, reopen verification, rollback, and recovery-
  required blocking if rollback cannot preserve a usable database.
- Database relocation using SQLite Online Backup API to a verified destination
  with atomic config update and preservation of the old database/data root.
- Pre-upgrade safety-backup gate for schema changes (maintenance path);
  automatic startup migration remains disabled.

DoD status:

- [x] Backup uses the SQLite Online Backup API (implementation and tests).
- [x] Published backups are independently verified (integrity, foreign-key,
  identity, schema revision, checksum, metadata).
- [x] No overwrite path for published backups (unique naming and exclusive/atomic
  publish flow).
- [x] Cross-process lock protects backup/restore/relocation/upgrade (unit/integration
  tests, including contention/stale recovery cases).
- [x] Restore requires a verified eligible backup and creates a verified safety
  backup before replacement; staged replacement and rollback are implemented.
- [x] Failed restore/relocation paths preserve the previous usable database/config
  and emit recovery signals when rollback cannot guarantee safety.
- [x] Task registration is verified; rejection is surfaced as failure. Startup
  catch-up provides the fallback when scheduled execution is missed/unavailable.
- [x] Automated test suite and Ruff pass in this environment (428 passed, Ruff
  clean). A manual Windows drill (Task Scheduler registration/run with GUI
  closed, GUI restore/relocation/missing-drive recovery on real Windows UI) was
  **not executed** in this session and must be recorded separately before relying
  on it as a release drill.

**Gate:** data-protection review; approval to build the UI shell.

### Phase 5 — Main interface, theme, and reusable components

**Status: complete (2026-11-17).** Report: `Reports/PHASE_05_REPORT.md`.

Goal: refine the existing PySide6 shell into a consistent, accessible, polished
desktop UI without adding business functionality. The authoritative scope was the
Phase 5 UX brief, which superseded the earlier demo-list/fake-data deliverables
listed in this roadmap.

Work completed:

- [x] Final design tokens for palettes, typography, spacing, radii, control
  heights, shell dimensions, chart palettes, and dialog/wizard sizes.
- [x] Single token-driven QSS template with explicit `px` units and tests against
  unresolved placeholders/unitless lengths; runtime light/dark/system switching
  and Qt palette synchronisation preserved.
- [x] Shell refinement: token-driven sizing, accessible status labels, latest
  verified backup status, `F5` refresh shortcut, and `QSettings` persistence of
  geometry, window state, and current navigation with multi-monitor safety.
- [x] Dashboard presentation using only verified environment facts, with an
  explicit no-business-records empty state; no fake KPIs, charts, or seed data.
- [x] Scrollable dashboard and backup views with token margins and wrapped-path
  handling.
- [x] Reusable `StatusBadge`, `EmptyState`, `Toast`, `DetailCard`,
  `make_button()`, and `set_dialog_size()` components.
- [x] Setup, recovery, restore confirmation, backup settings, and fatal-error
  dialog refinements: consistent sizing, defaults, tab order, accessible names,
  and asynchronous Task Scheduler status.
- [x] Backup UI states: empty, unavailable, busy, verified-only restore, status
  feedback, toast on success, modal error on decisions, and non-modal warning on
  history read failure.
- [x] Programmatic offscreen smoke checks at scale factors 1, 1.25, and 1.5.

Deliberately deferred under the Phase 5 brief:

- Icon-rail collapse and an approved SVG icon family (no icon set exists).
- `DataTable`, form primitives, component gallery, KPI/chart cards, and skeleton
  loading (owned by later business/report phases).
- Real Windows visual/DPI walkthroughs and real Windows backup integration drills.

DoD status:

- [x] No module hard-codes colors/fonts/spacing outside tokens.
- [x] Theme switching, palette synchronisation, shell persistence, F5 refresh,
  accessibility names, backup states, dialog defaults, and feedback are covered
  by automated tests.
- [x] Existing Phase 1–4 regression suite remains green: 448 tests passed.
- [x] Ruff passes across `app` and `tests`.
- [ ] Keyboard-only walkthrough, 10k-row table benchmark, and real Windows visual
      DPI review remain manual release/hardening tasks; the corresponding screens
      or approved metric definitions do not exist yet.

**Gate:** owner UI/UX review against UI_UX_BLUEPRINT.md; explicit authorization was
required before Phase 6 planning began and remains required before master data or
any other business implementation.

### Phase 6 — Business requirements, workflows & module planning

**Status: complete (2026-11-18).** Report: `Reports/PHASE_06_REPORT.md`.

Goal: define the business blueprint before any business module is implemented. This was a documentation-only phase; no code, schema, migration, business data, or authentication was added.

Deliverables:

- [x] `docs/BUSINESS_REQUIREMENTS.md` — product scope, confirmed constraints, proposed requirements, out-of-scope areas.
- [x] `docs/BUSINESS_WORKFLOWS.md` — confirmed implemented workflows and proposed business workflows with actors, steps, states, failures, and outputs.
- [x] `docs/MODULE_SPECIFICATIONS.md` — module boundaries, shared services, dependencies, and functional data requirements.
- [x] `docs/BUSINESS_RULES.md` — confirmed conventions, provisional defaults, open alternatives, approval policies, and proposed permissions.
- [x] `docs/REPORTING_REQUIREMENTS.md` — report catalogue, metric definitions needed, exports, integrity, and access requirements.
- [x] `docs/OPEN_DECISIONS.md` — all decisions requiring owner confirmation before implementation.
- [x] This roadmap updated for Phase 6 completion and proposed next phases.
- [x] `Reports/PHASE_06_REPORT.md` created.

Definition of done:

- [x] Entire repository structure, master docs, Phase 1–5 reports, navigation/placeholders, layer boundaries, and Git state inspected.
- [x] Confirmed items separated from proposals, clarifications, and out-of-scope items.
- [x] No business rule was selected silently from a provisional default.
- [x] Existing decisions and documentation preserved.
- [x] No database migration, business table, seed data, auth implementation, or unrelated code change made.
- [x] No commit, amend, rebase, or push performed.
- [ ] Owner review and explicit decision on the minimum Phase 7 prerequisite set in `OPEN_DECISIONS.md` §7.

**Recommended first business implementation scope after owner approval:** business settings, customers, suppliers, units/categories, and product/service catalogue as vertical slices, with no transaction posting until tax, discount, numbering, payment, and correction rules are decided. This is now recorded below under the first implementation candidate.

**Gate:** owner approval of Phase 6 planning was required before Phase 7 planning began. The explicit Phase 7 brief authorized the planning/approval-gate documentation, but owner answers and explicit approval are still required before any business implementation.

### Phase 7 — Owner decisions & first module specification

**Status: planning complete (2026-11-18); approval gate passed 2026-11-20.** Report: `Reports/PHASE_07_REPORT.md`.

**Implementation status: READY for the minimal Business Profile slice only.** Other business modules remain blocked by their own decisions.

Goal: resolve the business decisions that block implementation and prepare a draft owner-approved specification for the first business module. This is a documentation and approval-gate phase only.

Deliverables:

- [x] `docs/PHASE_07_OWNER_DECISION_WORKSHEET.md` — grouped decision questions, alternatives, consequences, dependencies, statuses, and owner-answer fields.
- [x] `docs/PHASE_07_FIRST_MODULE_SPECIFICATION.md` — draft specification for the recommended first module.
- [x] `docs/PHASE_07_IMPLEMENTATION_READINESS.md` — readiness assessment and owner action checklist.
- [x] `docs/OPEN_DECISIONS.md` updated only for Phase 7 traceability/status; no unanswered decision marked approved.
- [x] This roadmap updated for Phase 7 planning and the approval gate.
- [x] `Reports/PHASE_07_REPORT.md` created.

Definition of done:

- [x] Project structure, Git state, Phase 1–6 reports, and required source documents inspected.
- [x] Every blocking decision from Phase 6 represented with preserved IDs.
- [x] No unanswered decision marked approved.
- [x] No proposed requirement represented as confirmed.
- [x] Recommended first module selected from dependencies and approved requirements.
- [x] First-module dependencies clearly explained.
- [x] Existing architecture, database, backup, and security decisions preserved.
- [x] No code, migration, table, model, dependency, seed data, auth, or application behavior changed.
- [x] No commit, amend, rebase, reset, clean, or push performed.
- [x] First-module answers recorded by owner continuation instruction on 2026-11-20.
- [x] First-module specification explicitly approved for the minimal slice.
- [x] Readiness re-check passed for the minimal slice.

**Approved first module:** Business Settings — Business Profile only.

**Gate passed:** business name mandatory; address, phone, email, website, registration number, and footer message optional; one profile per installation; single record with no history; no tax, attachments, print, audit UI, roles, customers, suppliers, catalogue, or transactions. All other decisions remain open.

### Phase 7A — First business module: Business Profile

**Status: implemented 2026-11-20; demo complete; owner acceptance still pending.**

Goal: deliver one vertical slice for the approved business-profile fields without inventing unapproved business rules.

Work:

- Alembic revision adding the single-row `business_profile` table.
- Framework-independent domain object, validation, and completion rules.
- Application service owning the unit-of-work boundary and structured results.
- SQLAlchemy repository with no business-validation responsibility.
- QtCore-only ViewModel and a presentation-only Settings view.
- Tests for domain rules, persistence, migration, UI states, and architecture boundaries.
- Documentation and phase report updates.

Definition of done:

- [x] Profile can be created, loaded, edited, saved, and reloaded.
- [x] Empty, incomplete, complete, validation-error, and save-failure states are covered.
- [x] One profile only; no silent overwrite or sample data.
- [x] No tax, logo/attachment, print, audit UI, roles, customers, suppliers, catalogue, transaction, or configuration changes are included.
- [x] Existing Phase 1–7 tests remain green.
- [x] Lint and architecture boundary checks pass.
- [ ] Owner acceptance recorded in the phase report.

**Gate:** approved module demo plus owner acceptance before any master-data or transaction module.

### Historical/deferred — Authentication and users (conditional; formerly listed as Phase 6)

This section is preserved from the earlier roadmap, where authentication was labelled Phase 6. Phase 6 is now the completed business-planning documentation phase. Q-04/AQ-05 were resolved in favour of four local roles; the deferred work was renumbered as Phase 8A (specification) and Phase 8B (implementation). The checklist below is historical planning text and is superseded by the Phase 8B implementation record.

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

### First implementation candidate — Business master data (partially implemented)

This content was formerly labelled Phase 7 in this roadmap. It is preserved as the next business implementation candidate after the Phase 7 approval gate. The Phase 9 prompt (2026-11-23) implemented the approved **Customers & Suppliers** slice only: required `name`; optional phone/email/address/contact_person/notes/is_active; duplicate warning with explicit confirmation; activate/deactivate; no hard delete; service-layer authz/audit; migration `0005_party_master`. Units/categories/products-services/business settings master data remain pending owner approval and implementation.

Goal: the reference data needed by transactions.

Prerequisite for remaining master-data slices: owner approval of the specific field list, duplicate policy, and archival behavior from `OPEN_DECISIONS.md` (`B6-09`, `B6-13` catalogue portion, `B6-11`) and the applicable rules in `BUSINESS_RULES.md`.

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

Prerequisite: owner decisions on Q-03, Q-07, Q-08, Q-09, Q-10, Q-13, Q-14, Q-05/Q-06 if inventory is included, and the `B6-01`, `B6-02`, `B6-05`, `B6-06`, `B6-07` discovery decisions. Provisional defaults in `BUSINESS_RULES.md` are not implementation authority.

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

### Phase 10 — Product & Service Catalogue Management

**Status: implemented 2026-11-24; owner review pending.** Report: `Reports/PHASE_10_REPORT.md`.

Goal: implement a simple, dependable Product & Service catalogue master-data slice per the approved Phase 10 prompt.

Work completed:

- [x] Shared `catalogue_items` table with `kind=product|service` (migration `0006_catalogue_master`).
- [x] Domain validation: required name; optional description, unit (simple text), default sale price reference (INR paise integer, no tax/discount/stock calculation), is_active.
- [x] Duplicate warning on case-insensitive normalized name within same kind; save only after explicit confirmation.
- [x] Activate/deactivate lifecycle; no hard delete.
- [x] Permissions: `catalogue.view/create/edit`; Owner/Admin + Operator view/create/edit; Accountant/Reviewer + Viewer view-only.
- [x] Dedicated Products and Services navigation entries and catalogue UI.
- [x] Append-only audit events: `catalogue.created`, `catalogue.updated`, `catalogue.activated`, `catalogue.deactivated`.
- [x] Focused tests and full regression suite.

DoD:

- [x] Approved catalogue scope implemented; no inventory/stock/variants/barcodes/tax/transactions added.
- [x] Service-layer authorization enforced; UI not sole enforcement.
- [x] Migration forward-only; downgrade refuses when catalogue rows exist.
- [x] Full pytest suite and Ruff pass.

**Note:** Reports and dashboard (previously planned as Phase 10 in earlier roadmap drafts) remain a future phase and require separate owner-approved scope/planning.

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

Phases 1–6, the Phase 7 approval gate, and Phase 7A Business Profile are complete
(2026-11-20). Reports are in `Reports/PHASE_01_REPORT.md` through
`Reports/PHASE_07A_REPORT.md`. The owner confirmed INR and the Indian fiscal year;
the 2026-11-20 continuation instruction approved only the minimal Business Profile
slice. The affected documentation was reconciled during those phases.

Review `Reports/PHASE_07A_REPORT.md` for acceptance. Do not start master data,
transactions, authentication, tax details, attachments, reports, or any other
business module without a new explicit owner decision in
`docs/OPEN_DECISIONS.md`.

Phase 5 preserved the Phase 4 data-protection guarantees (verified backups, safe
restore/relocation, scheduling/catch-up, and the pre-upgrade safety-backup gate).
A manual Windows integration drill for the backup/restore/relocation/scheduler
flows and real Windows visual/DPI walkthroughs at 100%, 125%, and 150% remain
prerequisites before treating those flows as release-verified.
