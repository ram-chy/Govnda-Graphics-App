# Phase 7C — Business Profile Acceptance & Windows Integration Verification

## Role

Act as a Senior Windows Desktop Application QA Engineer, Python/PySide6
Developer, SQLite Engineer, and Software Quality Auditor.

Your task is to perform Phase 7C of the **Gobindas Graphics Business Management
System**.

This phase verifies the actual Windows behavior and integration of the Business
Profile functionality implemented in:

- Phase 7A — Initial Business Profile implementation
- Phase 7B — Business Profile requirements correction
- Phase 7B-1 — Audit retention and append-only protection

Read the existing phase reports and project documentation before starting.

## 1. Primary Objective

Verify that the implemented Business Profile functionality is reliable, safe,
and consistent with the owner's approved requirements.

The verification must cover:

1. Business Profile creation and editing.
2. Mandatory and optional field validation.
3. Logo upload, replacement, and storage.
4. Business Profile version history.
5. Permanent audit event retention.
6. Backup and restore integration.
7. Logo preservation during backup and restore.
8. Database relocation and asset preservation.
9. Windows application startup and recovery behavior.
10. Overall Business Profile acceptance readiness.

Do not assume that automated tests alone prove Windows integration is working.

## 2. Mandatory Pre-Verification Inspection

Before running anything:

1. Inspect the repository structure.
2. Read:
   - `docs/BLUEPRINT.md`
   - `docs/ARCHITECTURE.md`
   - `docs/DATABASE_SCHEMA.md`
   - `docs/UI_UX_BLUEPRINT.md`
   - `docs/BACKUP_STRATEGY.md`
   - `docs/SECURITY_AND_DATA_PROTECTION.md`
   - `docs/BUSINESS_REQUIREMENTS.md`
   - `docs/BUSINESS_WORKFLOWS.md`
   - `docs/MODULE_SPECIFICATIONS.md`
   - `docs/BUSINESS_RULES.md`
   - `docs/OPEN_DECISIONS.md`
   - `docs/PHASE_07_FIRST_MODULE_SPECIFICATION.md`, if present
   - `Reports/PHASE_07A_REPORT.md`, if present
   - `Reports/PHASE_07B_REPORT.md`
   - `Reports/PHASE_07B_1_REPORT.md`
3. Inspect the current Git status and preserve all existing modifications and
   untracked files.
4. Identify the actual Windows Python environment, application entry point,
   database location, backup location, and available test commands.
5. Inspect the migration state and relevant Business Profile, audit, backup,
   restore, and relocation services.

Do not assume paths or filenames. Discover the actual implementation.

If any required report or documentation file is missing, record it rather than
inventing its contents.

## 3. Owner-Approved Business Profile Requirements

The following requirements are authoritative.

### Mandatory fields

- Business Name
- Address
- Phone
- Email
- Logo
- Footer Message

### Optional fields

- Secondary Phone
- Website
- Registration Number

Website and Registration Number must remain optional. Do not remove them or
change their status.

### Logo requirements

- PNG
- JPG/JPEG
- Maximum file size: 5 MB
- Logo stored inside the application data folder.
- Safe generated filenames and relative asset references.
- Invalid uploads must not damage the currently saved profile.

### Profile history

- One Business Profile per application installation.
- Previous profile versions must be retained.
- Users must be able to view previous versions.
- Viewing history must not change the active profile.
- Previous versions must not be silently modified or deleted.

### Audit requirements

- Record all significant changes.
- Retain audit records indefinitely.
- Audit records must be append-only.
- Business Profile creation, meaningful updates, logo replacement, and history
  viewing must be recorded as implemented.
- Failed operations must not create misleading successful-operation audit
  events.
- Backup and restore must preserve audit history.

## 4. Critical Data Safety Rules

These rules are mandatory throughout this phase.

### Never use the live business database for destructive testing.

Use a separate isolated verification environment with:

- A dedicated temporary database.
- A dedicated temporary data directory.
- A dedicated temporary backup directory.
- Clearly identified synthetic test records.
- Test-only logo files.

Never overwrite, delete, reset, relocate, restore, or migrate the owner's real
business database during verification.

Do not run database downgrade commands against the real database.

Do not create sample business data in the live application.

Do not run seeders.

Do not delete existing backups.

Do not change Git history, commit, push, or stage files.

If the application is already configured to use a real business database, verify
its location and leave it untouched.

If an operation cannot be safely isolated, mark it BLOCKED and explain why.

## 5. Verification Checklist

### A. Windows Application Startup

Launch the application in the actual Windows environment.

Verify:

- Application starts without an unexpected exception.
- Existing database is detected correctly.
- Business Profile settings screen opens.
- No unexpected database initialization occurs.
- No automatic destructive migration occurs.
- Missing data drive or unavailable database does not silently create a
  replacement database.
- Existing setup and recovery behavior remains intact.

Record Windows version, Python version, application version, and test
environment.

### B. Business Profile Form

Using the isolated verification environment:

Test the mandatory fields individually.

Verify:

- Business Name cannot be empty.
- Address cannot be empty.
- Phone cannot be empty.
- Email cannot be empty.
- Logo cannot be missing.
- Footer Message cannot be empty.

Test valid input for all mandatory fields.

Test optional fields:

- Secondary Phone
- Website
- Registration Number

Verify that all optional fields can remain empty without preventing a valid
save.

Test reasonable invalid inputs, including invalid email format and
whitespace-only values where applicable.

Do not invent new validation rules. Compare results with the existing approved
specification.

### C. Logo Upload and Replacement

Test:

1. Valid PNG upload.
2. Valid JPG upload.
3. Invalid file extension.
4. Invalid image content with a valid image extension.
5. File larger than 5 MB.
6. File at or near the 5 MB boundary.
7. Replacing an existing logo.
8. Selecting an image from an inaccessible or missing path.
9. Simulated storage failure.
10. Simulated database or audit failure during a profile save.

Verify:

- Valid logos are stored under the application data folder.
- Stored references are relative and safe.
- The active profile displays the correct logo.
- Replacing a logo preserves the previous profile version.
- Invalid or failed operations do not corrupt the active profile.
- Failed operations do not leave misleading successful audit entries.
- Temporary files are handled safely.

Do not delete the active logo during testing.

### D. Business Profile Version History

Perform a sequence of saves using synthetic test data.

Verify:

- Initial profile creation creates the expected history.
- Meaningful updates create new versions.
- Historical records preserve their original values.
- Version numbering is consistent.
- Historical versions can be viewed.
- Viewing an older version does not overwrite the active profile.
- History remains available after application restart.
- Historical records cannot be modified or deleted through supported application
  operations.

### E. Audit Event Persistence

Verify the following in the isolated database:

- Initial Business Profile creation.
- Meaningful profile updates.
- Logo replacement.
- Historical version viewing.
- Correct event ordering and timestamps.
- Actor information as supported by the current implementation.
- Failed operations do not generate false success events.
- Audit events survive application restart.

Test append-only enforcement using isolated test data:

1. Attempt an ORM update.
2. Attempt an ORM delete.
3. Attempt direct SQL UPDATE.
4. Attempt direct SQL DELETE.
5. Attempt the supported migration downgrade path with audit records present.

Expected result:

- Supported application paths reject audit modification/deletion.
- SQLite triggers reject direct UPDATE/DELETE.
- The supported MigrationManager refuses destructive downgrade when audit
  records exist.
- No audit history is lost.

Do not use direct Alembic downgrade against the live database.

Record the documented limitation that direct Alembic execution outside the
supported MigrationManager can bypass the application-level downgrade guard.

### F. Manual Backup Verification

Use the isolated verification database.

Test:

1. Create a Business Profile.
2. Upload a logo.
3. Generate audit events.
4. Create a manual backup.
5. Verify backup integrity.
6. Verify metadata and SHA-256.
7. Verify managed logo assets are included.
8. Confirm that the backup can be recognized by the restore workflow.

Do not assume that a successful backup file creation proves its contents are
valid.

### G. Restore Verification

Use only the isolated verification database and its test backups.

Test:

1. Create a backup containing profile version A and its audit events.
2. Make additional changes, producing profile version B and additional audit
   events.
3. Restore the earlier backup.
4. Verify the expected restored profile.
5. Verify that current audit history is preserved according to the implemented
   audit-merge behavior.
6. Verify that required logo assets are present and valid.
7. Restart the application and verify the restored state.

Failure scenarios:

- Corrupted backup.
- Missing audit table or required triggers.
- Missing logo asset.
- Invalid managed asset metadata.
- Simulated failure during restore replacement.
- Simulated rollback failure, if safely testable.

Expected behavior:

- Invalid backups are rejected before replacement.
- A safety backup is created as designed.
- Failed restores preserve the previous working database and its audit history.
- If rollback fails, the application enters its documented recovery-required
  state rather than silently opening an uncertain database.

### H. Database Relocation Verification

Use a separate isolated data directory.

Test relocation to another available local Windows folder or drive.

Verify:

- Database integrity before and after relocation.
- All Business Profile data remains intact.
- All profile history remains intact.
- Audit events remain intact.
- Logo files are copied and verified.
- Configuration is updated only after successful validation.
- The old database is not prematurely deleted.
- Failed relocation does not leave the application pointing to an invalid
  destination.
- Restart after relocation works correctly.

Do not use the owner's real data directory for this test.

### I. Windows Scheduled Backup Integration

Verify the existing Windows Task Scheduler integration.

Check:

- Scheduled task registration.
- Task execution configuration.
- Daily schedule.
- Backup runner invocation.
- Exit status and logging.
- Behavior when the GUI application is closed.
- Behavior when the data drive is unavailable.
- Startup catch-up behavior, if applicable.

Confirm that backup retention applies to backup files only and does not remove
live audit events.

Do not create duplicate scheduled tasks unnecessarily. Inspect existing task
configuration before changing anything.

Any task creation or modification must use the isolated verification environment
or be explicitly approved by the owner.

## 6. Defect Handling

This is a verification-only phase.

If a defect is found:

1. Record the exact reproduction steps.
2. Record expected behavior.
3. Record actual behavior.
4. Capture the relevant exception or log output.
5. Identify the likely affected component.
6. Classify severity:
   - Critical
   - High
   - Medium
   - Low
7. Recommend a correction.

Do not silently expand Phase 7C into a development phase.

Do not modify application code to hide a failed test.

Do not make unrelated refactors.

If a correction is necessary, prepare a separate proposed Phase 7C-1 correction
scope and stop for owner approval.

Only non-destructive test setup and verification artifacts are permitted without
additional approval.

## 7. Automated Verification

Run the existing test suite in the correct project environment.

Run:

- Full pytest suite.
- Relevant Business Profile tests.
- Audit append-only tests.
- Backup and restore tests.
- Relocation tests.
- Ruff checks.
- Application startup smoke test, where practical.

Compare results with the latest Phase 7B-1 baseline:

- 496 pytest tests passed.
- Ruff passed.

Do not claim these historical results as current results.

Record the exact command, environment, result, and any failures.

Do not modify dependencies simply to make tests pass.

If the correct Python environment or required tools are unavailable, record
BLOCKED and explain what is needed.

## 8. UI Acceptance Review

Inspect the actual Windows UI.

Verify:

- Business Profile screen is visually consistent with Phase 5 UI guidelines.
- Calm green Light Mode remains intact.
- Professional Dark Mode remains intact.
- Form labels and required-field indicators are clear.
- Validation messages are understandable.
- Logo preview and replacement behavior are clear.
- History navigation is understandable.
- No accidental data loss occurs when navigating away.
- Keyboard navigation works.
- Dialogs and notifications are readable.
- No unexpected layout clipping occurs at 100%, 125%, and 150% display scaling,
  where the environment permits.

Do not claim screen-reader or visual acceptance without actually testing it.

## 9. Acceptance Classification

Every verification item must have one of these statuses:

- PASS — Tested successfully with evidence.
- FAIL — Tested and did not meet expected behavior.
- BLOCKED — Could not be tested because of a specific dependency or environment
  limitation.
- NOT RUN — Not attempted.

Never mark BLOCKED or NOT RUN as PASS.

Distinguish clearly between:

- Automated verification.
- Windows integration verification.
- Manual owner verification.
- Owner acceptance.

The owner alone decides whether the Business Profile module is accepted.

## 10. Required Deliverables

Create:

`Reports/PHASE_07C_REPORT.md`

The report must include:

1. Phase overview.
2. Environment details.
3. Repository and Git status before and after.
4. Documentation inspected.
5. Verification scope.
6. Detailed test checklist with PASS/FAIL/BLOCKED/NOT RUN.
7. Automated test results.
8. Windows integration results.
9. Backup and restore results.
10. Audit retention verification.
11. Logo and asset verification.
12. Database relocation results.
13. UI acceptance observations.
14. Defects and severity classifications.
15. Evidence locations and relevant logs.
16. Outstanding limitations.
17. Owner acceptance checklist.
18. Recommendation for the next phase.

Update `docs/DEVELOPMENT_ROADMAP.md` only if necessary to accurately reflect
Phase 7C verification status. Do not mark the module owner-accepted.

## 11. Phase Completion Conditions

Phase 7C may be reported as verification-complete only when all required
verification activities have either:

- Passed with evidence, or
- Been explicitly recorded as BLOCKED/NOT RUN with a clear reason and owner
  action required.

A failed test must remain visible in the report.

Owner acceptance must remain pending until the owner explicitly approves it.

Do not begin authentication, user management, permissions, or the next business
module as part of this phase.

## 12. Final Response

After completing the work, provide:

- A concise implementation-independent verification summary.
- Exact automated test results.
- Windows integration results.
- Any defects found.
- Any blocked manual checks.
- The report path.
- Git status and confirmation that no commit or push was performed.

If actual Windows GUI interaction is unavailable, state that clearly. Do not
fabricate screenshots, test results, or successful manual verification.

**Start with repository and documentation inspection. Proceed carefully,
preserve existing work, and prioritize business-data safety over completing
every test.**
