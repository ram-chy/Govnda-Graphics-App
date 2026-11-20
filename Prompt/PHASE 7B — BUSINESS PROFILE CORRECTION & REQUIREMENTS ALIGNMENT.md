# PHASE 7B — BUSINESS PROFILE CORRECTION & REQUIREMENTS ALIGNMENT

## Objective

Correct the existing Phase 7A Business Profile implementation so it fully
matches the owner's previously approved requirements.

Phase 7A is implemented but has NOT received owner acceptance. Treat Phase 7B as
a corrective implementation phase, not a new business module.

Work carefully. Inspect the repository, documentation, migrations, tests, and
Git status before modifying anything. Do not rush.

---

## 1. Mandatory Development Rules

1. Inspect the entire relevant existing implementation before making changes.
2. Read:
   - `Reports/PHASE_07A_REPORT.md`
   - `docs/PHASE_07_OWNER_DECISION_WORKSHEET.md`
   - `docs/PHASE_07_FIRST_MODULE_SPECIFICATION.md`
   - `docs/PHASE_07_IMPLEMENTATION_READINESS.md`
   - `docs/OPEN_DECISIONS.md`
   - `docs/ARCHITECTURE.md`
   - `docs/DATABASE_SCHEMA.md`
   - `docs/BACKUP_STRATEGY.md`
   - `docs/SECURITY_AND_DATA_PROTECTION.md`
   - `docs/DEVELOPMENT_ROADMAP.md`
3. Inspect the existing Phase 7A code, migration history, database runtime,
   backup/restore system, application context, Settings view, and tests.
4. Inspect `git status`, current branch, and existing changes before editing.
5. Preserve unrelated user changes. Never discard, reset, overwrite, or clean
   unrelated work.
6. Do not commit, push, amend, rebase, or change Git history.
7. Do not run seeders or insert sample business data.
8. Do not delete or recreate the user's existing database.
9. Do not silently modify existing business records.
10. Do not introduce unnecessary dependencies.
11. Follow the existing modular-monolith architecture and coding conventions.
12. Use the existing Python, PySide6, SQLAlchemy 2, SQLite, Alembic, Pydantic,
    and pytest stack.
13. Business rules must remain independent of PySide6.
14. Use `Decimal` for calculations and integer minor units for persisted
    monetary values where applicable. Never use floating-point financial
    calculations.
15. Create a detailed report at `Reports/PHASE_07B_REPORT.md`.

If an approved requirement cannot be implemented safely without an additional
owner decision, document the blocker and stop that specific part rather than
inventing a policy.

---

## 2. Authoritative Owner-Approved Business Profile Requirements

These decisions are authoritative. Do not replace them with Phase 7A's narrower
field specification.

### 2.1 Business profile structure

- Exactly one business profile per application installation.
- Profile identity remains stable.
- No multiple business profiles.
- The profile must persist in the selected application database.
- The application must never create a sample business automatically.

### 2.2 Mandatory fields

The following fields are mandatory:

1. Business name
2. Address
3. Phone
4. Email
5. Logo
6. Footer message

Required text fields must reject empty or whitespace-only values.

The logo must be present for a profile to be considered complete.

### 2.3 Optional fields

- Secondary phone

Other previously discussed optional candidates were not approved. Do not add
them unless they are already part of the explicitly approved implementation
specification or the owner approves them separately.

### 2.4 Logo requirements

- Supported formats: PNG, JPG, JPEG.
- Maximum upload size: 5 MB.
- Store uploaded logo files inside the application data folder.
- Do not store arbitrary absolute paths that break after database relocation.
- Use a safe, application-managed relative storage reference.
- Validate actual file content where practical; do not trust only the filename
  extension or MIME type.
- Reject unsupported formats, oversized files, empty files, and invalid image
  content.
- Protect against path traversal and unsafe filenames.
- Do not overwrite an existing valid logo before a replacement has been
  validated and safely stored.
- Handle failed database saves and failed file operations without leaving the
  profile pointing to a missing or incomplete file.
- Ensure database relocation, backup, and restore behavior is consistent with
  the actual logo storage design.

**Important:** Existing backup and relocation behavior was originally designed
around SQLite database files. Inspect whether the application data folder and
backup process currently include managed logo files. Extend the
backup/restore/relocation system safely if necessary. Do not claim that logo
files are protected by backups unless verified by implementation and tests.

### 2.5 Business Profile history

The owner approved:

- Keep previous Business Profile versions.
- Allow viewing previous versions.
- Allow viewing current details.
- Preserve historical profile information rather than silently replacing it.

Implement immutable profile-version snapshots.

At minimum:

- Creating the first profile creates its initial version.
- Each successful meaningful profile update creates a new version.
- Historical versions must not be modified when the current profile changes.
- Failed saves must not create history versions.
- The current profile must remain identifiable.
- Historical logo references must remain valid for as long as their historical
  versions are retained.
- The UI must allow the owner to inspect the current profile and previous
  versions.

Do not implement historical editing or restoration unless an existing approved
document explicitly authorizes it. Do not invent a version-retention limit.

### 2.6 Audit history

The owner approved:

- Record all significant changes.
- Retain audit history indefinitely.

Implement a durable audit-event foundation appropriate to the existing
architecture.

At minimum, significant Business Profile operations must generate audit events,
including:

- Initial profile creation.
- Profile updates.
- Logo changes.
- Relevant administrative actions involving profile history.

Audit events should identify the event type, timestamp, relevant entity, and
actor when an authenticated user exists.

Requirements:

- No automatic expiration or deletion of audit events.
- No ordinary application UI for editing or deleting audit events.
- Audit events must be written consistently with the operation they describe.
- Failed operations must not create misleading success events.
- Avoid storing passwords, secrets, or unnecessary sensitive data in audit
  payloads.
- Preserve historical audit records through normal backup and restore
  operations.

**Important:** The application does not yet have completed authentication. Do
not invent fake user IDs or pretend anonymous actions have a verified user
identity. Use an explicit system/unauthenticated actor representation where
appropriate until the authentication layer is implemented.

Keep Business Profile version history separate from the general audit-event
system. Both are required and serve different purposes.

---

## 3. Correct the Existing Phase 7A Implementation

Review and correct the current implementation rather than replacing it
unnecessarily.

Existing relevant files include:

- `app/domain/business_profile.py`
- `app/infrastructure/database/models/business_profile.py`
- `app/infrastructure/database/business_profile_repository.py`
- `app/services/business_profile_service.py`
- `app/ui/viewmodels/business_profile_viewmodel.py`
- `app/ui/views/business_profile_view.py`
- `migrations/versions/0002_business_profile.py`
- `migrations/env.py`

Preserve the existing architecture and working behavior wherever possible.

### 3.1 Domain layer

Update the Business Profile domain model and validation rules.

Implement:

- Correct mandatory field validation.
- Optional secondary phone.
- Profile completeness assessment based on all required fields, including logo
  availability.
- Safe normalization of text fields.
- Clear field-specific validation errors.
- Immutable historical snapshot representation.

Do not add unsupported phone, email, tax, or other validation rules without
approval.

### 3.2 Database layer

Inspect the existing schema and migration history.

Add new Alembic migrations for required schema changes. Do not modify an
already-applied migration such as `0002_business_profile.py`.

Design the schema to support:

- The single current Business Profile.
- Immutable Business Profile versions.
- Audit events.
- Safe references to managed logo files.
- Appropriate foreign-key and integrity constraints.

Use transactions and database constraints where appropriate.

Do not add authentication tables or role-management functionality in this phase.

### 3.3 Application services

Implement or extend services for:

- Loading the current profile.
- Creating the initial profile.
- Updating the profile.
- Validating and storing a logo.
- Creating immutable history snapshots.
- Retrieving profile history.
- Recording audit events.

Ensure that database transactions, file operations, rollback behavior, and
failure handling are coordinated safely.

Use the existing `DatabaseRuntime` abstraction. Do not capture a stale database
engine in long-lived service instances.

### 3.4 User interface

Improve the existing Settings > Business Profile interface.

It must support:

- Current profile display.
- Editing all approved fields.
- Clear mandatory-field indicators.
- Inline validation errors.
- Logo upload with PNG/JPG/JPEG restrictions and a 5 MB limit.
- Logo preview where appropriate.
- Secondary phone as optional.
- Save and discard actions.
- Clear empty, incomplete, and complete states.
- A Business Profile History section or view.
- Viewing historical and current profile versions.

Maintain the approved visual design:

- Native PySide6 Qt Widgets.
- Calm green-based Light Mode.
- Professional Dark Mode.
- Clean, minimal interface.
- Accessible labels and keyboard navigation.
- No fake business data.
- No unnecessary modal dialogs.

Do not build unrelated business modules or dashboard metrics.

---

## 4. Data Safety, Backup, Restore & Relocation

This section is mandatory because Business Profile now includes external logo
files and historical snapshots.

Inspect the existing Phase 4 backup, restore, and relocation implementation
before changing it.

Verify that:

1. Logo files are included in verified backups.
2. Historical logo files remain available after backup and restore.
3. Database and managed file references remain consistent.
4. Relocation preserves the complete managed profile-file directory.
5. Restore does not leave the database pointing to missing logo files.
6. Failed relocation does not destroy the original data.
7. Failed restore can safely roll back to the pre-restore state.
8. Existing backup verification and safety-backup behavior remain intact.
9. Missing data drives continue to trigger the existing recovery behavior.
10. No replacement database is silently created.

If the existing backup format must be extended, maintain compatibility with
existing backups. Document any compatibility limitations and migration behavior.

Do not weaken the existing backup safety gates to make this phase easier.

---

## 5. Testing Requirements

Add comprehensive tests.

### Domain tests

- Mandatory field validation.
- Whitespace-only rejection.
- Optional secondary phone.
- Profile completion assessment.
- Snapshot immutability.
- Normalization.

### Logo tests

- PNG acceptance.
- JPG/JPEG acceptance.
- Unsupported format rejection.
- Oversized file rejection.
- Invalid image-content rejection.
- Safe filename and path handling.
- Replacement failure safety.
- Missing logo detection.
- Historical logo retention.

### Database and migration tests

- Existing database migration from the Phase 7A schema.
- Single-profile constraint.
- Initial version creation.
- New version on meaningful update.
- No version on failed save.
- Historical snapshot preservation.
- Audit-event persistence.
- Indefinite-retention behavior (no automatic cleanup).

### Service tests

- Create, load, update.
- Transaction commit and rollback.
- Storage failure.
- File-operation failure.
- Audit-event consistency.
- DatabaseRuntime replacement.
- History retrieval.

### UI tests

- Mandatory indicators.
- Inline validation.
- Logo selection and preview.
- Save/discard behavior.
- Current profile display.
- History navigation.
- Historical snapshot display.
- Light and Dark Mode compatibility.

### Backup, restore, and relocation tests

- Backup contains managed profile assets.
- Restore restores assets and database consistently.
- Relocation preserves managed assets.
- Failed operations preserve the original data.
- Historical logo references remain valid.

Run:

```powershell
py -m ruff check app tests migrations
py -m pytest -q
```

Also run relevant targeted tests during implementation.

If a command cannot run, report the exact limitation. Never claim an unexecuted
check passed.

---

## 6. Documentation Updates

Update the relevant existing documents to reflect the implemented reality:

- `docs/ARCHITECTURE.md`
- `docs/DATABASE_SCHEMA.md`
- `docs/BUSINESS_REQUIREMENTS.md`
- `docs/PHASE_07_FIRST_MODULE_SPECIFICATION.md`
- `docs/PHASE_07_IMPLEMENTATION_READINESS.md`
- `docs/OPEN_DECISIONS.md`
- `docs/DEVELOPMENT_ROADMAP.md`
- `README.md`

Do not mark unrelated open decisions as resolved.

Keep authentication, role permission matrices, customer/supplier modules,
catalogue, transactions, tax, accounting, and reporting outside this corrective
phase unless an existing approved dependency makes a narrow change absolutely
necessary.

---

## 7. Explicitly Out of Scope

Do NOT implement:

- User registration or login.
- User management.
- Role or permission management.
- Customer or supplier modules.
- Product/service catalogue.
- Quotations or orders.
- Invoices or payments.
- Purchases or expenses.
- Inventory.
- Accounting or ledger.
- Tax/GST configuration.
- Currency configuration.
- Print/PDF output.
- General-purpose audit log viewer.
- Cloud synchronization.
- Cloud backup.
- Any sample business data.

The audit-event foundation and Business Profile history UI are in scope. A
general audit log viewer is not.

---

## 8. Completion Criteria

Phase 7B is complete only when:

1. All previously approved Business Profile fields and mandatory rules are
   implemented.
2. Logo validation and storage work safely.
3. Immutable Business Profile history works.
4. Historical and current versions can be viewed.
5. Significant Business Profile changes generate durable audit events.
6. Audit history is retained indefinitely.
7. Backup, restore, and relocation safely preserve all managed profile assets.
8. Existing database contents remain intact.
9. All applicable automated tests pass.
10. Ruff checks pass.
11. Documentation accurately describes the implementation.
12. A detailed report exists at `Reports/PHASE_07B_REPORT.md`.

The report must include:

- Summary and implementation status.
- Owner-approved requirements compliance table.
- Files created and modified.
- Database migration details.
- Logo storage design.
- Profile history design.
- Audit-event design.
- Backup/restore/relocation changes.
- Test commands and actual results.
- Any unresolved limitations.
- Manual Windows verification still required.
- Git status and confirmation that no commits or history changes were made.

---

## 9. Stop Conditions

If any requirement conflicts with existing architecture, database safety, backup
compatibility, or an undocumented business rule:

1. Stop the affected implementation.
2. Preserve existing data and working functionality.
3. Document the conflict.
4. Explain the available safe alternatives in `Reports/PHASE_07B_REPORT.md`.
5. Do not invent an owner decision.

Do not proceed to customers, suppliers, catalogue, or transaction modules after
completing this phase.

**Final instruction:** Complete Phase 7B only. Leave the application ready for
owner demonstration and acceptance. Do not declare owner acceptance yourself.
