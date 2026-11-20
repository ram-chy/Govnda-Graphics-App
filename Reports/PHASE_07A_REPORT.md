# PHASE 07A REPORT — First business module: Business Profile

| Field | Value |
| --- | --- |
| Report | PHASE_07A_REPORT.md |
| Date | 2026-11-20 |
| Phase | 7A — First business module: Business Profile |
| Status | Historical Phase 7A report; owner demo/acceptance pending |
| Authority | Owner continuation instructions “Proceed for Next Phase for your self” and “continiue”, recorded in `docs/PHASE_07_OWNER_DECISION_WORKSHEET.md`; corrected by the Phase 7B prompt |
| Scope | Historical minimal Business Profile slice; superseded by `Reports/PHASE_07B_REPORT.md` |

> **Corrigendum:** This report records Phase 7A as first delivered. The owner-approved Phase 7B prompt corrected the Business Profile slice to require `business_name`, `address`, `phone`, `email`, `footer_message`, and `logo`; add optional `secondary_phone`; add immutable version history, durable audit events, managed logo storage, migration `0003_business_profile_requirements`, and managed logo preservation through backup/restore/relocation. Statements below that say only business name was mandatory, history/logo/audit were excluded, or `0002_business_profile` was the head are historical and superseded.

## 1. Outcome

Phase 7A delivers the first vertical business slice: a single per-installation
business profile that can be viewed, created, edited, validated, saved, and
reloaded. The implementation adds one Alembic revision and one application table.
No other business module was started.

The profile is stored as one row with `id = 1`. A database check constraint
rejects any second row. The application service upserts that row; it never creates
sample data, silently replaces the profile, or keeps history.

## 2. Approved field set

| Field | Rule |
| --- | --- |
| Business name | Mandatory; whitespace-only is rejected |
| Address | Optional text |
| Phone | Optional text; no format validation |
| Email | Optional text; no format validation |
| Website | Optional text |
| Registration number | Optional text |
| Footer message | Optional text |

Tax fields, GSTIN, logo/attachments, bank details, fiscal settings, currency
settings, print/PDF output, audit UI, authentication, roles, customers, suppliers,
catalogue, transactions, accounting, expenses, and reports are explicitly out of
scope.

## 3. Implemented layers

### 3.1 Domain

`app/domain/business_profile.py` is framework-independent. It defines:

- `BusinessProfile`, `SINGLE_PROFILE_ID`, and approved field labels.
- `validate_profile()` for the single mandatory field.
- `assess_completion()` for empty/incomplete/complete states.
- `normalized()` for trimming all stored text.
- No phone, email, website, or tax-format rules.

### 3.2 Infrastructure

- `app/infrastructure/database/models/business_profile.py` maps the
  `business_profile` table.
- `app/infrastructure/database/business_profile_repository.py` loads and upserts
  the single row without applying business rules.
- `migrations/versions/0002_business_profile.py` adds the table with
  `CHECK (id = 1)` and drops it on downgrade.
- `migrations/env.py` imports the mapped record so Alembic metadata includes it.

### 3.3 Application service

`app/services/business_profile_service.py` owns validation calls, explicit
unit-of-work boundaries, commit/rollback, and structured load/save results.
Validation errors are returned as field errors. Storage failures are logged with a
correlation ID, rolled back, and returned as a safe status message. The prior
profile remains unchanged when a save fails.

`BusinessProfileServiceFactory` follows the current `DatabaseRuntime`, so restore
and relocation replace the effective database without capturing a stale engine.

### 3.4 UI

- `app/ui/viewmodels/business_profile_viewmodel.py` imports QtCore only and emits
  one immutable snapshot.
- `app/ui/views/business_profile_view.py` renders labels, fields, inline errors,
  empty/status states, and save/discard buttons. It contains no validation or
  persistence logic.
- `AppContext` exposes `business_profile_factory`; `MainWindow` passes it to the
  Settings view and rebuilds that view after a database change.
- The Settings navigation subtitle no longer claims a Phase 7 placeholder.

## 4. Files added

- `app/domain/business_profile.py`
- `app/infrastructure/database/models/__init__.py`
- `app/infrastructure/database/models/business_profile.py`
- `app/infrastructure/database/business_profile_repository.py`
- `app/services/business_profile_service.py`
- `app/ui/viewmodels/business_profile_viewmodel.py`
- `app/ui/views/business_profile_view.py`
- `migrations/versions/0002_business_profile.py`
- `tests/test_business_profile_domain.py`
- `tests/test_business_profile_service.py`
- `tests/test_business_profile_migration.py`
- `tests/test_business_profile_ui.py`
- `Reports/PHASE_07A_REPORT.md`

## 5. Files updated

Gate and planning documents:

- `docs/PHASE_07_OWNER_DECISION_WORKSHEET.md`
- `docs/PHASE_07_FIRST_MODULE_SPECIFICATION.md`
- `docs/PHASE_07_IMPLEMENTATION_READINESS.md`
- `docs/OPEN_DECISIONS.md`
- `docs/DEVELOPMENT_ROADMAP.md`

Implementation and current-state documents:

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/BUSINESS_REQUIREMENTS.md`
- `docs/DATABASE_SCHEMA.md`
- `migrations/env.py`
- `app/app_context.py`
- `app/main.py`
- `app/ui/main_window.py`

Tests updated for the new Alembic head:

- `tests/test_database_migrations.py`
- `tests/test_setup_service.py`
- `tests/test_startup.py`
- `tests/test_backup_infrastructure.py`
- `tests/test_backup_service.py`

Lint-only import fixes were also applied by Ruff to new files.

## 6. Verification

Commands run from the repository root with the available launcher:

- `py -m ruff check app tests migrations --fix` — fixed import ordering and modern typing imports.
- `py -m ruff check app tests migrations` — all checks passed.
- `py -m pytest -q tests/test_business_profile_domain.py tests/test_business_profile_service.py tests/test_business_profile_migration.py tests/test_business_profile_ui.py tests/test_database_migrations.py tests/test_setup_service.py tests/test_startup.py tests/test_main_window.py` — 73 passed.
- `py -m pytest -q` — 470 passed in 40.38s.

`scripts/check.ps1` was not used because no `.venv` exists in this environment;
it requires `.venv\Scripts\python.exe`. The equivalent `py -m ruff` and
`py -m pytest` commands were run directly.

## 7. Safety and boundary checks

- Only `0002_business_profile` was added; `0001_baseline` was not modified.
- `SCHEMA_USER_VERSION` remains `1`; file identity remains owned by the baseline.
- Startup still never migrates automatically.
- Backup restore eligibility now uses `0002_business_profile` as the application
  head; tests read the head dynamically.
- A simulated storage failure rolled back and preserved the previous profile.
- The invalid-save UI test confirms inline errors and no modal decision dialog.
- No seed data, sample business, or second profile is created.

## 8. Outstanding

- Owner demo/acceptance of the implemented profile screen is still pending and is
  deliberately not marked complete.
- All owner decisions outside the approved minimal profile slice remain open in
  `docs/OPEN_DECISIONS.md`.
- No master-data or transaction phase may begin until a new explicit owner
  decision approves it.
