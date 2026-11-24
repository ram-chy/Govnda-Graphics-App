# Phase 10 Report — Product & Service Catalogue Management

## 1. Summary

Implemented the approved Phase 10 Product & Service catalogue master-data slice in the existing PySide6 + SQLite application. The slice adds a shared `catalogue_items` table for products and services, service-layer authorization and validation, duplicate warnings with explicit confirmation, activate/deactivate lifecycle, append-only audit events, and a forward-only Alembic migration. No inventory/stock, variants, barcodes, multiple price lists, tax, discounts/commissions, transactions, invoices, payments, accounting, or hard-delete workflow was added.

## 2. Approved Decisions Implemented

- **Scope:** Products and Services included.
- **Data model:** Shared `catalogue_items` table with `kind = product | service`.
- **Required field:** `name` (trimmed, non-empty, max 200 chars).
- **Optional fields:** `description` (max 500), `unit` (simple text, max 100), `default_sale_price_minor` (optional integer INR paise, >= 0, reference/default only; no tax/discount/stock calculation), `is_active`.
- **Duplicate policy:** Warn on case-insensitive normalized name within the same kind; save only after explicit confirmation.
- **Lifecycle:** Activate/deactivate supported; no hard delete in normal UI/service API.
- **Validation:** Minimal sensible validation as approved; kind restricted to product/service; `is_active` boolean.
- **Permissions:** `catalogue.view`, `catalogue.create`, `catalogue.edit` (edit includes activate/deactivate). Owner/Admin and Operator: view/create/edit. Accountant/Reviewer and Viewer: view-only. No delete permission.
- **Exclusions preserved:** No inventory/stock/variants/barcodes, no tax/discount/commission, no transactions/invoices/payments/accounting.

## 3. Files Changed / Created

### Phase 10 code changes

- `app/domain/catalogue.py` — catalogue domain model, normalization, validation, duplicate warning types, audit event constants.
- `app/domain/auth.py` — added `CATALOGUE_VIEW`, `CATALOGUE_CREATE`, `CATALOGUE_EDIT` permissions and role grants per approved matrix.
- `app/infrastructure/database/models/catalogue.py` — `CatalogueItemRecord` SQLAlchemy model.
- `app/infrastructure/database/models/__init__.py` — exported `CatalogueItemRecord`.
- `app/infrastructure/database/catalogue_repository.py` — catalogue persistence, search, duplicate lookup.
- `app/services/catalogue_service.py` — service-layer authz, validation, duplicate warning/confirmation, create/update/activate-deactivate, audit events.
- `app/ui/viewmodels/catalogue_viewmodel.py` — catalogue screen state/actions.
- `app/ui/views/catalogue_view.py` — Products/Services UI with search, include-inactive filter, create/edit form, duplicate confirmation, activate/deactivate.
- `app/app_context.py` — wired `CatalogueServiceFactory`.
- `app/ui/main_window.py` — added Catalogue navigation group (`products`, `services`) and view wiring.
- `app/main.py` — passed `catalogue_factory` into `MainWindow`.
- `migrations/env.py` — registered `CatalogueItemRecord` for Alembic metadata.
- `migrations/versions/0006_catalogue_master.py` — forward-only catalogue master migration.

### Tests

- `tests/test_catalogue_phase10.py` — domain validation/normalization, repo CRUD/search/duplicates, service create/update/duplicate confirmation/activate-deactivate, role authz, audit event smoke, no-delete API check, migration smoke.
- `tests/test_database_migrations.py` — updated expected migration files, head table set, and revision history for `0006_catalogue_master`.
- `tests/test_auth_authorization.py` — updated expected role grants to include owner-approved Phase 10 catalogue permissions.
- `tests/test_auth_phase8b.py` — updated expected grant matrix to include owner-approved Phase 10 catalogue permissions.
- `tests/test_main_window.py` — updated expected navigation keys to include `products` and `services`.

### Docs/report

- `docs/AUTHORIZATION_MATRIX.md` — added Phase 10 catalogue permission keys and role grants; clarified future-module section.
- `docs/DATABASE_SCHEMA.md` — documented implemented `catalogue_items` table and updated schema status/baseline.
- `docs/OPEN_DECISIONS.md` — marked B6-13 partially resolved for the approved minimal catalogue slice; broader catalogue decisions remain open.
- `docs/DEVELOPMENT_ROADMAP.md` — added Phase 10 catalogue status and DoD; noted reports/dashboard remain future scope.
- `Reports/PHASE_10_REPORT.md` — this report.

## 4. Migration / Schema / Audit Behavior

- Added Alembic migration `migrations/versions/0006_catalogue_master.py` (`down_revision = 0005_party_master`).
- Creates `catalogue_items` table with columns: `id`, `kind`, `name`, `name_key`, `description`, `unit`, `default_sale_price_minor`, `is_active`, `created_at`, `updated_at`.
- Constraints: kind check (`product`, `service`), trimmed-name non-empty, boolean active check, non-negative price when present.
- Indexes: `(kind, name_key)`, `(kind, is_active)`.
- Downgrade refuses if catalogue rows exist to prevent accidental data destruction.
- Audit events written as append-only `audit_events` rows with `entity_type='catalogue'`: `catalogue.created`, `catalogue.updated`, `catalogue.activated`, `catalogue.deactivated`.

## 5. Tests Run

Commands run in `.venv` from `D:\Development\Gobindas Graphics`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_catalogue_phase10.py tests/test_database_migrations.py tests/test_auth_authorization.py tests/test_auth_phase8b.py -q
.\.venv\Scripts\python.exe -m ruff check . --fix
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest -q
```

## 6. Exact Results

- `pytest tests/test_catalogue_phase10.py tests/test_database_migrations.py tests/test_auth_authorization.py tests/test_auth_phase8b.py -q` → **107 passed in 28.80s**
- `ruff check . --fix` → fixed 2 import-sorting issues; 3 E501 line-length issues remained in `tests/test_catalogue_phase10.py` and were corrected manually.
- `ruff check .` (after fixes) → **All checks passed!**
- `pytest -q` (full suite) → **629 passed in 77.97s (0:01:17)**

## 7. Manual Windows Verification Checklist

Owner/QA can verify on Windows:

- [ ] Launch app; login works as before.
- [ ] Navigate to Products and Services; both screens load.
- [ ] Create a product with required name only; save succeeds.
- [ ] Create product with optional description/unit/default sale price; values persist after refresh/reopen.
- [ ] Enter invalid default sale price (negative or more than 2 decimals); UI shows validation feedback and save is blocked.
- [ ] Create duplicate-name product in same kind; warning appears; save proceeds only after explicit confirmation.
- [ ] Edit product; changes persist after refresh/reopen.
- [ ] Deactivate product; record shown as inactive; Activate restores it.
- [ ] Search filters by name/description/unit. “Show inactive” toggle includes/excludes inactive records.
- [ ] Repeat key checks for Services; confirm duplicate warning is scoped within the same kind.
- [ ] Operator can view/create/edit catalogue; Accountant/Reviewer and Viewer can view but cannot create/edit.
- [ ] No hard delete action is present.
- [ ] Existing customers/suppliers, backup/profile/auth flows still work.

## 8. Known Limitations / Follow-up Items

- No stock quantities, movements, opening stock, variants, barcodes, categories master, managed units, multiple price lists, tax, discounts/commissions, or transaction integration — intentionally out of Phase 10 scope.
- Default sale price is a reference/default INR paise value only; it is not used by sales/purchase/invoice calculations (those modules are not implemented).
- No CSV import/export, merge, or advanced dedupe workflow.
- No hard delete; referenced-record protection is policy-level for now because transaction modules are not implemented yet.
- Duplicate warning is based on normalized name within the same kind; it is not fuzzy matching.
- The default sale price field in the UI is parsed as a decimal rupee amount with up to 2 decimal places and stored as integer paise; invalid input is blocked client-side before save.

## 9. Documentation Updates

- Updated `docs/AUTHORIZATION_MATRIX.md` (Phase 10 catalogue permissions and role grants).
- Updated `docs/DATABASE_SCHEMA.md` (implemented `catalogue_items` table; schema version/baseline/status updated).
- Updated `docs/OPEN_DECISIONS.md` (B6-13 partially resolved for minimal catalogue slice).
- Updated `docs/DEVELOPMENT_ROADMAP.md` (Phase 10 catalogue status/DoD; reports/dashboard moved to future scope note).
- Added `Reports/PHASE_10_REPORT.md`.

## 10. Git Status Summary

Worktree is dirty and contains pre-existing/unrelated changes; no unrelated files were reverted or cleaned up. Phase 10 implementation changes are present but **not committed** and **not pushed**.

Current branch: `main` (per prior checkpoint context).  
`git status --short` captured after Phase 10 implementation:

```text
 M "Prompt/Phase 9 — Customer & Supplier Management.md"
 M app/app_context.py
 M app/domain/auth.py
 M app/infrastructure/database/models/__init__.py
 M app/main.py
 M app/ui/main_window.py
 M docs/AUTHORIZATION_MATRIX.md
 M docs/DATABASE_SCHEMA.md
 M docs/DEVELOPMENT_ROADMAP.md
 M docs/OPEN_DECISIONS.md
 M migrations/env.py
 M tests/test_auth_authorization.py
 M tests/test_auth_phase8b.py
 M tests/test_database_migrations.py
 M tests/test_main_window.py
?? "Prompt/Phase 10 — Product & Service Catalogue Management.md"
?? Reports/PHASE_10_REPORT.md
?? app/domain/catalogue.py
?? app/infrastructure/database/catalogue_repository.py
?? app/infrastructure/database/models/catalogue.py
?? app/services/catalogue_service.py
?? app/ui/viewmodels/catalogue_viewmodel.py
?? app/ui/views/catalogue_view.py
?? migrations/versions/0006_catalogue_master.py
?? tests/test_catalogue_phase10.py
```

## 11. Confirmation

- No live business database was used for destructive tests. Automated tests used isolated temporary databases/fixtures.
- No existing data/audit history was deleted, reset, or rewritten by Phase 10 code.
- No commit or push was performed during Phase 10 implementation.
- Before any commit/push, files should be reviewed explicitly because the worktree contains unrelated/pre-existing changes.
- Approved Phase 10 exclusions remain enforced: no inventory/stock, variants, barcodes, multiple price lists, tax, discounts/commissions, transactions/invoices/payments/accounting, and no hard delete.
