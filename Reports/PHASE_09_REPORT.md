# Phase 9 Report — Customer & Supplier Management

## 1. Summary

Implemented the approved Phase 9 Customer & Supplier master-data slice in the existing PySide6 + SQLite application. The slice adds basic party records for customers and suppliers, service-layer authorization and validation, duplicate warnings with explicit confirmation, activate/deactivate lifecycle, append-only audit events, and a forward-only Alembic migration. No financial ledger, opening balance, credit limit, tax, transaction, or hard-delete workflow was added.

Phase 8B owner acceptance was recorded in `Reports/PHASE_08B_REPORT.md` before this implementation, per the Phase 9 prompt. No historical Phase 8B test result was changed.

## 2. Implemented Scope

- **Party master records (Customer/Supplier):** required `name`; optional `phone`, `email`, `address`, `contact_person`, `notes`, `is_active`.
- **Duplicate policy (owner-approved 2026-11-23):** warn on possible duplicate; allow save only after explicit confirmation. Duplicate match: case-insensitive normalized name; also warn on matching phone for an existing active record when phone is provided.
- **Lifecycle (owner-approved 2026-11-23):** activate/deactivate supported. No hard delete in normal UI; referenced records must never be unsafely deleted. `PartyService` exposes no delete API.
- **Permissions (owner-approved 2026-11-23, Option 2A):** `party.view`, `party.create`, `party.edit` added to the approved matrix; `party.edit` includes activate/deactivate. `party.delete` remains denied/not implemented. Owner/Admin and Operator can view/create/edit; Accountant/Reviewer and Viewer can view.
- **UI:** Customers and Suppliers navigation entries now open dedicated Party views (search, include inactive, create/edit form, save, activate/deactivate, duplicate confirmation prompt).
- **Audit:** append-only `audit_events` records written for `party.created`, `party.updated`, `party.activated`, `party.deactivated`.
- **Migration:** `0005_party_master` creates `parties` table and indexes; downgrade refuses when party rows exist.

## 3. Files Changed / Created

### Phase 9 code changes

- `app/domain/party.py` — party domain model, normalization, validation, duplicate warning types, audit event constants.
- `app/domain/auth.py` — added `PARTY_VIEW`, `PARTY_CREATE`, `PARTY_EDIT` permissions and role grants per approved matrix.
- `app/infrastructure/database/models/party.py` — `PartyRecord` SQLAlchemy model.
- `app/infrastructure/database/models/__init__.py` — exported `PartyRecord`.
- `app/infrastructure/database/party_repository.py` — party persistence, search, duplicate lookup.
- `app/services/party_service.py` — service-layer authz, validation, duplicate warning/confirmation, create/update/activate-deactivate, audit events.
- `app/ui/viewmodels/party_viewmodel.py` — party screen state/actions.
- `app/ui/views/party_view.py` — customer/supplier UI.
- `app/app_context.py` — wired `PartyServiceFactory`.
- `app/ui/main_window.py` — added party factory wiring and Customers/Suppliers views.
- `app/main.py` — passed `party_factory` into `MainWindow`.
- `migrations/env.py` — registered `PartyRecord` for Alembic metadata.
- `migrations/versions/0005_party_master.py` — forward-only party master migration.

### Tests

- `tests/test_party_phase9.py` — domain validation/normalization, repo CRUD/search/duplicates, service create/update/duplicate confirmation/activate-deactivate, role authz, audit event smoke, no-delete API check, migration table smoke.
- `tests/test_database_migrations.py` — updated expected migration files, head table set, and revision history for `0005_party_master`.
- `tests/test_auth_authorization.py` — updated expected role grants to include owner-approved Phase 9 party permissions.
- `tests/test_auth_phase8b.py` — updated expected grant matrix to include owner-approved Phase 9 party permissions.

### Docs/report

- `docs/OPEN_DECISIONS.md` — marked B6-13 partially resolved for customers/suppliers; catalogue remains open.
- `docs/AUTHORIZATION_MATRIX.md` — added Phase 9 party permission keys and role grants.
- `docs/DATABASE_SCHEMA.md` — documented implemented `parties` table and noted proposed customer/supplier future shape.
- `docs/DEVELOPMENT_ROADMAP.md` — added Phase 9 status; noted master-data candidate partially implemented.
- `Reports/PHASE_08B_REPORT.md` — recorded owner formal acceptance before Phase 9 implementation.
- `Reports/PHASE_09_REPORT.md` — this report.

## 4. Tests Run

Commands run in `.venv` from `D:\Development\Gobindas Graphics`:

```powershell
./.venv/Scripts/python.exe -m pytest tests/test_party_phase9.py tests/test_database_migrations.py -q
./.venv/Scripts/python.exe -m ruff check .
./.venv/Scripts/python.exe -m pytest -q
```

## 5. Exact Results

- `pytest tests/test_party_phase9.py tests/test_database_migrations.py -q` → **31 passed in 2.72s**
- `ruff check .` → **All checks passed!**
- `pytest -q` (full suite) → **614 passed in 74.91s (0:01:14)**

Notes:
- Initial focused run exposed a test data issue (`"op"` username too short for auth validation) and ruff style issues; both were fixed before the passing results above.
- Full suite initially had 9 failures in existing auth-matrix tests because they hardcoded pre-Phase-9 role grants. These tests were updated to reflect the owner-approved Phase 9 permission additions; no historical Phase 8B test result was edited.

## 6. Migration / Schema Changes

- Added Alembic migration `migrations/versions/0005_party_master.py` (`down_revision = 0004_authentication`).
- Creates `parties` table with columns: `id`, `party_kind`, `name`, `name_key`, `phone`, `email`, `address`, `contact_person`, `notes`, `is_active`, `created_at`, `updated_at`.
- Constraints: kind check, trimmed-name non-empty, boolean active check.
- Indexes: `(party_kind, name_key)`, `(party_kind, phone)`, `(party_kind, is_active)`.
- Downgrade refuses if party rows exist to prevent accidental data destruction.

## 7. Manual Verification Checklist

Owner/QA can verify on Windows:

- [ ] Launch app; login works as before.
- [ ] Navigate to Customers and Suppliers; both screens load.
- [ ] Create customer with required name only; save succeeds.
- [ ] Create duplicate-name customer; warning appears; save proceeds only after confirmation.
- [ ] Edit customer; changes persist after refresh/reopen.
- [ ] Deactivate customer; record shown as inactive; Activate restores it.
- [ ] Search filters by name/phone/email/contact/address.
- [ ] “Show inactive” toggle includes/excludes inactive records.
- [ ] Operator can view/create/edit parties; Accountant/Reviewer and Viewer can view but cannot create/edit.
- [ ] No hard delete action is present.
- [ ] Existing backup/profile/auth flows still work.

## 8. Known Limitations

- No customer/supplier detail history UI beyond audit events in DB.
- No CSV import/export, merge, or advanced dedupe workflow.
- No financial fields (opening balance, credit limit, tax IDs, ledger links) — intentionally out of Phase 9 scope.
- No hard delete; referenced-record protection is policy-level for now because transaction modules are not implemented yet.
- Duplicate warning is based on normalized name and exact normalized phone for active records; it is not fuzzy matching.
- Party permissions are role-mapped per approved Option 2A; fine-grained per-user overrides are not implemented.

## 9. Documentation Updates

- Updated `docs/OPEN_DECISIONS.md` (B6-13 partially resolved for customers/suppliers).
- Updated `docs/AUTHORIZATION_MATRIX.md` (Phase 9 party permissions and role grants).
- Updated `docs/DATABASE_SCHEMA.md` (implemented `parties` table).
- Updated `docs/DEVELOPMENT_ROADMAP.md` (Phase 9 status and master-data partial implementation note).
- Added `Reports/PHASE_09_REPORT.md`.

## 10. Git Status Summary

Worktree is dirty with pre-existing modified/untracked files from prior phases/user work. Phase 9 changes are present but **not committed** and **not pushed**. No unrelated files were reverted or cleaned up.

Current branch: `main`  
Remote: `origin https://github.com/ram-chy/Govnda-Graphics-App.git`

`git status --short` was captured during reporting; it includes both pre-existing work and Phase 9 files.

## 11. Confirmation

- No live business database was used for destructive tests. Automated tests used isolated temporary databases/fixtures.
- No existing data/audit history was deleted, reset, or rewritten by Phase 9 code.
- No commit or push was performed during Phase 9 implementation.
- Before any commit/push, files should be reviewed explicitly because the worktree contains unrelated pre-existing changes.
