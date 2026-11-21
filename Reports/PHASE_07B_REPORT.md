# PHASE 07B REPORT — Business Profile correction and requirements alignment

| Field | Value |
| --- | --- |
| Report | PHASE_07B_REPORT.md |
| Date | 2026-11-20 |
| Phase | 7B — Business Profile correction and requirements alignment |
| Status | Implemented; owner demo/acceptance pending |
| Authority | `Prompt/PHASE 7B — BUSINESS PROFILE CORRECTION & REQUIREMENTS ALIGNMENT.md` |
| Scope | Business Profile only; no unrelated business modules or sample data |

## 1. Outcome

Phase 7B corrects the Phase 7A Business Profile slice to match the owner-approved requirements. The application now requires `business_name`, `address`, `phone`, `email`, `footer_message`, and a managed logo. `secondary_phone`, `website`, and `registration_number` are optional. The single active profile is clearly identified, and meaningful saves create immutable version snapshots.

The implementation is intentionally small and confined to profile fields, logo storage, history, audit, and the backup/restore/relocation behavior needed to keep managed logo files consistent. No seeders were run, no sample business data was inserted, and no existing database was deleted or recreated.

## 2. Requirements coverage

| Requirement | Implemented behavior |
| --- | --- |
| Mandatory text fields | Empty or whitespace-only values for `business_name`, `address`, `phone`, `email`, and `footer_message` are rejected inline and prevent writes. |
| Optional fields | `secondary_phone`, `website`, and `registration_number` are accepted when supplied. |
| Managed logo | PNG/JPG/JPEG only, at most 5 MB, signature/content validation, generated filename, safe `Logos/...` relative reference. |
| Logo failure safety | The current profile is preserved when validation, storage, save, versioning, or audit fails; only a newly stored logo is discarded. |
| History | `business_profile_versions` stores immutable snapshots and version numbers; the Settings view can select a prior version for viewing without changing the active profile. |
| Audit | `audit_events` durably records profile saves and history views with actor `system/unauthenticated`; no ordinary audit UI was added. Indefinite retention and append-only enforcement were confirmed and corrected by Phase 7B-1. |
| Current profile identity | The profile view shows current/draft status, completion state, version, and validation messages. |
| Backup | Sidecars may include `managed_assets` with `relative_path`, `size_bytes`, `sha256`, and base64 `content`; sidecars without assets remain compatible. |
| Restore | Managed assets are validated and staged, the database is verified, `Logos/` is replaced, and any failure rolls back database and assets. |
| Relocation | The complete `Logos/` directory is copied to the new data root and the copied assets are verified. |
| Migration | `0003_business_profile_requirements` adds columns and tables, creates immutability triggers, and backfills version/audit records without changing existing profile values. |

## 3. Files added

- `app/domain/audit.py`
- `app/domain/business_logo.py`
- `app/domain/backup_assets.py`
- `app/services/logo_storage_service.py`
- `migrations/versions/0003_business_profile_requirements.py`
- `tests/test_business_profile_assets.py`
- `Reports/PHASE_07B_REPORT.md`

## 4. Files updated

- Domain and validation: `app/domain/business_profile.py`
- Layout/constants: `app/core/constants.py`, `app/infrastructure/filesystem/layout.py`
- Database: `app/infrastructure/database/models/business_profile.py`, `app/infrastructure/database/models/__init__.py`, `app/infrastructure/database/business_profile_repository.py`, `migrations/env.py`
- Application services/wiring: `app/services/business_profile_service.py`, `app/app_context.py`
- UI: `app/ui/viewmodels/business_profile_viewmodel.py`, `app/ui/views/business_profile_view.py`, `app/ui/main_window.py`
- Backup/restore/relocation: `app/infrastructure/backup/metadata.py`, `app/services/backup_service.py`, `app/services/backup_workspace.py`, `app/services/restore_service.py`, `app/services/relocation_service.py`
- Tests: `tests/conftest.py`, `tests/test_business_profile_domain.py`, `tests/test_business_profile_service.py`, `tests/test_business_profile_migration.py`, `tests/test_business_profile_ui.py`, `tests/test_database_migrations.py`, `tests/test_setup_viewmodel.py`
- Documentation: `README.md`, `docs/BUSINESS_REQUIREMENTS.md`, `docs/PHASE_07_OWNER_DECISION_WORKSHEET.md`, `docs/PHASE_07_FIRST_MODULE_SPECIFICATION.md`, `docs/PHASE_07_IMPLEMENTATION_READINESS.md`, `docs/OPEN_DECISIONS.md`, `docs/ARCHITECTURE.md`, `docs/DATABASE_SCHEMA.md`, `docs/BACKUP_STRATEGY.md`, `docs/SECURITY_AND_DATA_PROTECTION.md`, `docs/DEVELOPMENT_ROADMAP.md`, `Reports/PHASE_07A_REPORT.md`

## 5. Verification

Commands run from the repository root:

```powershell
py -m ruff check app tests migrations
py -m pytest -q
```

Result:

```text
All checks passed!
487 passed in 45.99s
```

Targeted asset verification also passed during remediation:

```text
7 passed in 1.36s
```

## 6. Safety and boundary checks

- No unrelated business modules were added.
- No sample or seed data was inserted.
- No existing database was deleted or recreated.
- No Git history was rewritten.
- `migrations/versions/0002_business_profile.py` was left unchanged.
- Existing profile values are preserved by the backfill in `0003_business_profile_requirements`.
- Version and audit rows are immutable through database triggers.
- Logo references are relative, constrained to `Logos/`, and reject traversal and absolute paths.
- Backup sidecars remain readable when `managed_assets` is absent.
- Restore failures roll back both database state and managed logo files.

## 7. Outstanding

- Owner demo/acceptance is still pending.
- General attachment rules, print/document rules, roles, customers, suppliers, catalogue, and transactions remain outside this slice and unchanged by this report. Audit retention was corrected by Phase 7B-1 (`Reports/PHASE_07B_1_REPORT.md`); general audit visibility remains outside this slice.
- Manual Windows integration drills for backup/restore/relocation were not executed in this session; automated coverage was executed and passed.
