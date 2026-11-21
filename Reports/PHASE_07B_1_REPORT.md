# PHASE 07B-1 REPORT — Audit Retention Policy Correction

| Field | Value |
| --- | --- |
| Report | PHASE_07B_1_REPORT.md |
| Date | 2026-11-21 |
| Phase | 7B-1 — Audit retention policy correction |
| Status | Implemented; owner demo/acceptance pending |
| Authority | `Prompt/PHASE 7B-1 — AUDIT RETENTION POLICY CORRECTION.md` |
| Scope | Audit retention, append-only enforcement, Business Profile audit coverage verification, backup/restore preservation; no new business module |
| Branch | `main` (tracking `origin/main`) |

## 1. Summary

Phase 7B-1 resolves the discrepancy in `Reports/PHASE_07B_REPORT.md`, which described audit-event persistence but left retention outside the completed scope. The application now explicitly implements the owner-approved policy: **record all significant changes and retain audit history indefinitely**.

The existing Business Profile schema and migration were not redesigned. No new Alembic migration was needed because the schema already had an append-only `audit_events` table with no expiry column, no foreign keys, and protective SQLite triggers. The corrective work adds application-level append-only guards, a safe downgrade refusal, and audit-history preservation during verified restore.

## 2. Owner-approved retention requirement

- Record all significant changes.
- Retain audit history indefinitely.
- No automatic deletion, expiration, or retention-based cleanup.
- No configured retention period.
- Ordinary users cannot modify or delete audit records.
- General-purpose audit log viewer remains out of scope.
- Approved Business Profile fields remain unchanged: mandatory `business_name`, `address`, `phone`, `email`, `logo`, `footer_message`; optional `secondary_phone`, `website`, `registration_number`.

## 3. Initial audit implementation findings

Repository inspection was performed before changes. Git status was clean apart from the untracked Phase 7B-1 prompt file. Initial findings:

- `app/domain/audit.py` defines `system/unauthenticated`, profile entity type, event types, and the immutable `AuditEvent` value object.
- `migrations/versions/0003_business_profile_requirements.py:80-89` creates `audit_events` with only `id`, `event_type`, `entity_type`, `entity_id`, `actor`, `created_at`, and `payload`: no expiry, age, or retention column.
- `migrations/versions/0003_business_profile_requirements.py:125-128` creates `BEFORE UPDATE` and `BEFORE DELETE` triggers that abort direct changes to audit rows.
- `app/infrastructure/database/business_profile_repository.py:93-126` exposes only `add()` and `list()` for audit events.
- `app/services/business_profile_service.py:107-119` and `:208-252` write audit events in the same committed transaction as successful profile operations.
- `audit_events` has no foreign keys, so no cascade path can delete audit rows. The profile-version foreign key at `migrations/versions/0003_business_profile_requirements.py:49-54` has no `ON DELETE CASCADE`.

Risks found and corrected:

1. `migrations/versions/0003_business_profile_requirements.py:131-140` drops the audit table and its triggers on downgrade. This has been guarded at the supported migration entry point so a downgrade that would remove audit rows is refused.
2. `app/infrastructure/database/repository.py:37-38` exposed a generic `delete()` that could be used with any mapped model. It now refuses models marked `IMMUTABLE`.

Cleanup/retention inspection results:

- No production SQL `DELETE FROM audit_events`, `TRUNCATE audit_events`, `UPDATE audit_events`, or `DROP TABLE audit_events` exists outside the historical 0003 downgrade.
- No audit expiry timestamps, retention periods, scheduled audit purge, audit pruning job, or automatic truncation exists.
- Windows Task Scheduler integration only runs the daily backup runner (`app/core/constants.py:104-106`, `app/services/schedule_service.py`, `app/infrastructure/backup/task_scheduler.py`).
- Backup retention (`app/services/retention_service.py`, `app/infrastructure/backup/retention.py`, `app/core/config.py`) deletes only managed automatic backup files and rollback copies. It does not delete audit rows from the live database. A static test now enforces that these modules contain no audit logic.
- `PRAGMA wal_checkpoint(TRUNCATE)` in restore is a WAL checkpoint, not row truncation.
- `docs/DATABASE_SCHEMA.md:647` mentions future "audit indexes and pruning" only as a Q-22 dependency; no pruning code exists.

## 4. Files added

- `app/infrastructure/database/audit_history.py`
- `tests/test_audit_retention.py`
- `Reports/PHASE_07B_1_REPORT.md`

## 5. Files modified

- Append-only enforcement: `app/infrastructure/database/base.py`, `app/infrastructure/database/models/business_profile.py`, `app/infrastructure/database/repository.py`
- Migration safety: `app/infrastructure/database/migrations.py`
- Backup/restore preservation: `app/services/restore_service.py`
- Tests: `tests/test_business_profile_service.py`
- Documentation: `docs/SECURITY_AND_DATA_PROTECTION.md`, `docs/DATABASE_SCHEMA.md`, `docs/ARCHITECTURE.md`, `docs/OPEN_DECISIONS.md`, `docs/PHASE_07_FIRST_MODULE_SPECIFICATION.md`
- Prior report correction: `Reports/PHASE_07B_REPORT.md`

## 6. Database migration details

No new Alembic migration was created. Migration `0003_business_profile_requirements` was not modified.

- **Upgrade (already implemented in 0003):** adds the approved profile columns, creates `business_profile_versions` and `audit_events`, creates immutability triggers for both tables, and backfills version 1 plus one audit event for an existing profile without changing its values.
- **Downgrade (now guarded):** `MigrationManager.downgrade()` in `app/infrastructure/database/migrations.py` determines whether the requested target would remove the audit-event table. If `audit_events` contains any row, the downgrade is refused before Alembic runs and the database is unchanged. Downgrade of an empty audit table remains permitted for development/test use.
- Direct Alembic downgrade outside the application's supported migration manager remains unsupported because it bypasses this guard; this limitation is documented in `docs/DATABASE_SCHEMA.md` and `docs/SECURITY_AND_DATA_PROTECTION.md`.

## 7. Append-only enforcement

Audit events are now protected at four layers:

1. `AuditEventRepository` exposes only insertion and listing.
2. `AuditEventRecord` and `BusinessProfileVersionRecord` are marked `IMMUTABLE`; `Repository.delete()` refuses them.
3. A SQLAlchemy `before_flush` listener rejects any ORM update or delete of immutable records before SQL is emitted.
4. SQLite `BEFORE UPDATE` and `BEFORE DELETE` triggers abort direct SQL updates/deletes and remain present after backup and restore.

Business Profile audit coverage was verified for initial creation, meaningful updates, logo replacement, and history views. Audit writes remain inside the successful database transaction; failed saves produce no success event. Actor attribution remains `system/unauthenticated`; no identities were invented. Audit payloads contain changed field names or version numbers only—no passwords, secrets, or full profile content.

## 8. Backup and restore verification

- Normal database backups copy the whole SQLite file, including `audit_events`; tests read audit rows directly from the published backup file.
- `RestoreService.prepare()` now refuses a backup whose audit table or immutability triggers are missing.
- `RestoreService._restore()` verifies the staged backup, closes the live database, preserves audit history with `merge_audit_history()`, re-verifies the staged database, then replaces the live file.
- `merge_audit_history()` appends only events missing from the staged copy. It never updates, deletes, or renumbers existing events. If an ID collides with different content, the missing event is appended with a new unused ID, retaining its original actor and timestamp.
- Failed restores still roll back to the pre-restore database and its audit history; an explicit test covers an asset-replacement failure after audit preservation.
- Backup-file retention and rollback-copy cleanup remain file-level operations only and do not alter audit rows in the live database.

## 9. Test commands and actual results

Commands run from the repository root:

```powershell
py -m ruff check app tests migrations
py -m pytest -q
```

Final actual results:

```text
All checks passed!
496 passed in 43.78s
```

Targeted implementation run (before the final full run):

```text
51 passed in 4.92s
```

Targeted files: `tests/test_audit_retention.py`, `tests/test_business_profile_service.py`, `tests/test_business_profile_migration.py`, `tests/test_database_migrations.py`, `tests/test_business_profile_assets.py`.

New and updated automated coverage includes: audit insertion, schema immutability triggers, ORM update rejection, ORM delete rejection, generic-repository delete refusal, absence of expiry columns, no automatic cleanup or scheduled purge, downgrade refusal with existing audit rows, upgrade preservation, backup preservation, restore preservation, failed-restore rollback preservation, post-restore immutability, profile creation/update/logo/history-view audit events, and unchanged failed-save behavior.

## 10. Remaining limitations

- A local Windows administrator or malware running with sufficient file access can still edit the SQLite file directly. The database triggers make this difficult but not impossible against a determined privileged process; regular application users have no supported edit/delete path.
- There is still no general-purpose audit log viewer. The Business Profile service exposes audit events internally for verification only.
- Authenticated actor attribution remains unavailable because authentication was not implemented. The explicit `system/unauthenticated` representation is retained so future authentication can add actor identity without weakening existing records.
- Backup retention deletes old managed backup files; this does not delete live audit history, but it remains a separate file-retention policy.
- Direct Alembic downgrade bypasses the application-level guard. Use `MigrationManager`, `UpgradeService`, or `python -m app.tools.migrate` for schema changes.

## 11. Manual Windows verification still required

The following manual checks were not executed in this session and remain for owner review:

1. Create a real database through the Windows setup flow, perform profile saves, and confirm audit rows persist in `BusinessManagement.db`.
2. Run a manual backup, create additional profile audit events, restore the older backup through the UI, and confirm all audit events remain present.
3. Confirm a failed restore (for example, by interrupting an asset or verification step) leaves the previous database and audit history intact.
4. Attempt a downgrade through the supported maintenance tool with audit rows present and confirm the safe refusal message.
5. Confirm Windows Task Scheduler still runs only the daily backup task and no audit cleanup task appears.

## 12. Git status and commit confirmation

Final status from `git status --short --branch`:

```text
## main...origin/main
 M Reports/PHASE_07B_REPORT.md
 M app/infrastructure/database/base.py
 M app/infrastructure/database/migrations.py
 M app/infrastructure/database/models/business_profile.py
 M app/infrastructure/database/repository.py
 M app/services/restore_service.py
 M docs/ARCHITECTURE.md
 M docs/DATABASE_SCHEMA.md
 M docs/OPEN_DECISIONS.md
 M docs/PHASE_07_FIRST_MODULE_SPECIFICATION.md
 M docs/SECURITY_AND_DATA_PROTECTION.md
 M tests/test_business_profile_service.py
?? "Prompt/PHASE 7B-1 \342\200\224 AUDIT RETENTION POLICY CORRECTION.md"
?? Reports/PHASE_07B_1_REPORT.md
?? app/infrastructure/database/audit_history.py
?? tests/test_audit_retention.py
```

The untracked Phase 7B-1 prompt file was pre-existing and was preserved unchanged. No files were staged, no commits were made, no history was rewritten, no database was deleted, no seeders were run, and no business data was removed.
