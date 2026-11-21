# PHASE 7B-1 — AUDIT RETENTION POLICY CORRECTION

## Objective

Correct the Phase 7B implementation so that the application's audit history
follows the owner's explicitly approved retention policy:

**Record all significant changes and retain audit history indefinitely.**

The current Phase 7B report (`Reports/PHASE_07B_REPORT.md`) identifies
audit-event persistence but lists audit retention as outside the completed
scope. This discrepancy must be resolved.

This is a narrowly scoped corrective task. Do not redesign or unnecessarily
modify the existing Business Profile implementation.

---

## 1. Authoritative Owner Decisions

Preserve these approved requirements:

### Business Profile fields

Mandatory:

- Business name
- Address
- Phone
- Email
- Logo
- Footer message

Optional:

- Secondary phone
- Website
- Registration number

Do not remove Website or Registration Number. The owner has explicitly chosen to
retain them as optional fields.

### Business Profile history

- Preserve previous versions.
- Allow viewing previous and current details.
- Historical snapshots must remain immutable.
- Do not invent a retention limit.

### Audit history

- Record all significant changes.
- Retain audit history indefinitely.
- No automatic deletion, expiration, or retention-based cleanup.
- Ordinary application users must not be able to modify or delete audit records.
- A general-purpose audit log viewer is not required in this task.

---

## 2. Mandatory Repository Inspection

Before modifying anything:

1. Inspect Git status and current branch.
2. Read `Reports/PHASE_07B_REPORT.md`.
3. Inspect:
   - `app/domain/audit.py`
   - Audit-event database model and repository.
   - Business Profile service and audit integration.
   - Database migrations, including `0003_business_profile_requirements`.
   - Backup and restore implementation.
   - Existing audit-related tests.
   - Relevant security and data-protection documentation.
4. Search the entire repository for:
   - Audit-event deletion.
   - Audit-event cleanup.
   - Retention policies.
   - Expiration timestamps.
   - Scheduled cleanup jobs.
   - Cascade deletion affecting audit events.
   - Database triggers affecting audit records.
   - Any automatic pruning or purging logic.

Do not assume the current implementation is safe merely because audit records
are described as immutable.

---

## 3. Implementation Requirements

### 3.1 Indefinite retention

Enforce the following:

- No automatic audit-event expiration.
- No scheduled audit-event cleanup.
- No maximum audit-event age.
- No retention-based row deletion.
- No automatic truncation or pruning.
- No ordinary application operation that deletes audit history.

Do not implement a configurable retention period. The approved policy is
indefinite retention.

### 3.2 Immutability

Audit events must remain append-only.

Verify that:

- Existing immutability protections work.
- Application services cannot update or delete existing audit records.
- Database constraints or triggers protect against accidental
  modification/deletion where supported.
- Existing foreign-key relationships do not silently cascade-delete audit
  events.
- Future entity deletion cannot erase historical audit records.

If a current database relationship conflicts with this requirement, design a
safe migration that preserves existing audit history.

### 3.3 Significant change coverage

Inspect existing Business Profile audit coverage.

Ensure the following operations generate appropriate audit events:

- Initial profile creation.
- Meaningful profile updates.
- Logo replacement.
- Relevant administrative actions involving Business Profile history.

Do not generate misleading success events for failed operations.

Keep audit events consistent with successful database transactions.

Do not log passwords, secrets, or unnecessary sensitive information.

### 3.4 Actor attribution

Authentication is not yet implemented.

Continue using the explicit `system/unauthenticated` actor representation where
appropriate.

Do not invent user identities or IDs.

Design the audit foundation so authenticated actor attribution can be integrated
later without weakening existing records.

### 3.5 Backup and restore

Verify that audit history is included in normal database backups and restored
correctly.

Add tests proving:

- Existing audit records survive backup and restore.
- Restore does not silently omit audit history.
- Historical events remain immutable after restore.
- Failed restore preserves the pre-restore audit records.

Do not weaken existing backup safety behavior.

---

## 4. Database and Migration Safety

- Do not modify already-applied migrations.
- Create a new Alembic migration only if a schema change is genuinely necessary.
- Preserve all existing Business Profile data.
- Preserve all existing audit events.
- Do not delete or recreate the user's database.
- Ensure migration upgrade and downgrade behavior is explicitly documented.
- Never make downgrade silently destroy audit history.

If a downgrade cannot safely preserve audit data, document the restriction and
implement a safe refusal rather than destructive behavior.

---

## 5. Testing Requirements

Add or update automated tests for:

1. Audit-event insertion.
2. Audit-event immutability.
3. Rejection of update attempts.
4. Rejection of delete attempts.
5. No automatic retention cleanup.
6. No scheduled audit purge.
7. Audit persistence after successful Business Profile operations.
8. No success event after failed operations.
9. Preservation of audit records during backup.
10. Preservation of audit records during restore.
11. Preservation of audit records during applicable migrations.
12. Existing Business Profile behavior remains unchanged.

Run:

```powershell
py -m ruff check app tests migrations
py -m pytest -q
```

Run targeted audit and Business Profile tests during implementation.

Report actual results. Never claim that an unexecuted test passed.

---

## 6. Documentation Updates

Update relevant documents:

- `docs/SECURITY_AND_DATA_PROTECTION.md`
- `docs/DATABASE_SCHEMA.md`
- `docs/ARCHITECTURE.md`
- `docs/OPEN_DECISIONS.md`
- `docs/PHASE_07_FIRST_MODULE_SPECIFICATION.md`
- `Reports/PHASE_07B_REPORT.md`

Explicitly document:

- Indefinite audit retention.
- Append-only audit behavior.
- No automatic cleanup.
- Backup and restore preservation.
- Current unauthenticated actor representation.
- Remaining limitations, if any.

Do not mark unrelated open decisions as resolved.

---

## 7. Strictly Out of Scope

Do not implement:

- Authentication.
- User or role management.
- Permission matrix.
- General-purpose audit log viewer.
- Customers or suppliers.
- Catalogue.
- Quotations or orders.
- Invoices or payments.
- Expenses.
- Inventory.
- Accounting.
- Tax/GST.
- Cloud synchronization.
- Any new retention configuration.

Do not remove or change the approved optional Website and Registration Number
fields.

Do not redesign the Business Profile interface.

---

## 8. Git and Data Safety

- Preserve all existing user changes.
- Do not reset, clean, or discard unrelated files.
- Do not delete existing business data.
- Do not run seeders.
- Do not commit or push.
- Do not rewrite Git history.
- Report the final Git status.

---

## 9. Required Completion Report

Create:

`Reports/PHASE_07B_1_REPORT.md`

Include:

1. Summary.
2. Owner-approved retention requirement.
3. Initial audit implementation findings.
4. Files added and modified.
5. Database migration details, if applicable.
6. Append-only enforcement.
7. Retention-cleanup inspection results.
8. Backup and restore verification.
9. Test commands and actual results.
10. Remaining limitations.
11. Manual Windows verification still required.
12. Git status and confirmation that no commits were made.

Update `Reports/PHASE_07B_REPORT.md` only where necessary to accurately
reference this corrective work.

## 10. Completion Criteria

This task is complete only when:

- Audit history is retained indefinitely.
- Audit events cannot be modified or deleted through ordinary application
  operations.
- No automatic retention cleanup exists.
- Business Profile audit events are recorded consistently.
- Backup and restore preserve audit history.
- Existing Business Profile functionality remains intact.
- All applicable tests pass.
- Documentation reflects the actual implementation.

**Final instruction:** Complete only Phase 7B-1. Do not start another business
module. Leave the application ready for owner review and acceptance.
