# SECURITY AND DATA PROTECTION — Gobindas Graphics Business Management System

| Field | Value |
| --- | --- |
| Document | SECURITY_AND_DATA_PROTECTION.md |
| Version | 1.3 |
| Date | 2026-11-14; Phase 7B controls added 2026-11-20 |
| Status | Phase 3 setup/location, Phase 4 backup/restore, and Phase 7B profile/logo controls implemented |
| Related | ARCHITECTURE.md, BACKUP_STRATEGY.md, DATABASE_SCHEMA.md |

## Phase 7B protection controls (authoritative)

Protected business data now includes `<data_root>\Logos\`, `business_profile_versions`, and `audit_events`. Profile logo files use generated names, PNG/JPG/JPEG content validation, a 5 MB limit, and safe `Logos/...` relative references; absolute paths and `..` traversal are rejected.

Profile audit events are durable, retained indefinitely in this slice, written with actor `system/unauthenticated`, enforced immutable by database triggers, and have no ordinary UI. Backups can embed logo bytes in sidecar `managed_assets` with SHA-256 verification; restore and relocation preserve logo assets and roll back on failure. General attachments remain governed by the still-open Q-24 decision and are not part of this profile slice.

## 1. Scope and honesty about limits

This is a local, single-user desktop application. It does not have a server, network API, or cloud account. Security therefore depends primarily on:

- the physical and Windows account security of the workstation;
- the permissions of the chosen data folder;
- whether the disk is encrypted;
- the integrity of the application build;
- disciplined handling of backups and exports.

The application can reduce accidental loss and make tampering harder, but it **cannot** protect data from a Windows administrator, malware running as the user, physical disk theft without disk encryption, or a ransomware process that can write to the data folder. The documentation and UI must not overstate protection.

## 2. Assets to protect

| Asset | Location | Sensitivity |
| --- | --- | --- |
| Business database | `<data_root>\Database\BusinessManagement.db` | High: customers, prices, finances |
| WAL/SHM files | Same folder, while running | High (contains recent data) |
| Backups | `<data_root>\Backups\**` | High (full copy) |
| Attachments | `<data_root>\Attachments\` | Medium–high (invoices, receipts, IDs) |
| Exports | `<data_root>\Exports\` and user-chosen folders | High when financial |
| Configuration | `%APPDATA%\GobindasBMS\config.json` | Medium: paths, settings |
| Logs | `%LOCALAPPDATA%\GobindasBMS\logs\` | Low–medium: operational metadata |
| Credentials (if auth) | Database, hashed | High |
| Build artifacts | Dev machine / release share | High (supply chain) |

## 3. Threat model

| ID | Threat | Vector | Impact | Primary controls |
| --- | --- | --- | --- | --- |
| T-01 | Disk failure or corruption | Hardware | Data loss | Backups, `integrity_check`, `synchronous=FULL` |
| T-02 | Accidental deletion | User error, cleanup tools | Data loss | Confirmations, no auto-delete of data, retention guards, rollback copies |
| T-03 | Ransomware / malware | Email, downloads, compromised account | Data theft/loss | BitLocker, least privilege, offline backups, up-to-date Windows |
| T-04 | Theft of PC or drive | Physical | Confidentiality loss | BitLocker, Windows account password, no plaintext secrets |
| T-05 | Another local user reads data | Weak NTFS ACLs, shared PC | Confidentiality loss | Per-user data folder ACLs, separate Windows accounts |
| T-06 | Power loss during write | Power/outage | Corruption/loss | WAL, `synchronous=FULL`, transaction boundaries, backup |
| T-07 | SQL injection | Malicious input | Data disclosure/corruption | SQLAlchemy parameterization, no string-built SQL |
| T-08 | Path traversal / unsafe file write | Attachment names, export paths | Overwrite/escape | Canonical path validation, generated names, allowlists |
| T-09 | Excel formula injection | Customer/product names in exports | Code execution on open | Prefix dangerous leading characters, escape |
| T-10 | Backup tampering | Local user edits backup | Restore wrong/corrupt data | SHA-256 sidecar, integrity check, audit record |
| T-11 | Unauthorized app use | Shared unlocked PC | Confidentiality/integrity | Optional login/idle lock (Q-04), Windows lock |
| T-12 | Supply-chain compromise | Malicious dependency/build | Full compromise | Pinned versions, review, trusted sources, signed release |
| T-13 | Log leakage | PII/financial data in logs | Confidentiality loss | Logging policy and review |
| T-14 | Wrong database attached | User picks another business DB | Data confusion/loss | `application_id`, business-profile identity check |
| T-15 | Destructive migration | Bad schema change | Data loss | Safety backup, review, batch migrations, prior-release test |

Out of scope: remote network attacks (no listener), multi-tenant isolation, protection from a local administrator, formal PCI/tax certification.

## 4. Trust boundaries

```text
[User keyboard/mouse] → [Qt UI] → [Application services] → [Repositories] → [SQLite file]
                                     │
                                     ├→ [Backup runner] → [Backup files]
                                     └→ [Exporters] → [PDF/Excel files]

[Windows Task Scheduler] → [Backup runner] (same user, same files)
```

- The UI is untrusted input: everything is validated at the service boundary.
- The database file is trusted only after identity and integrity checks.
- Backup files are untrusted until verified.
- Imported files (Excel/CSV) are untrusted.
- Configuration is untrusted; it is validated and never grants code execution.

## 5. Windows permissions and deployment

### 5.1 Recommended folder permissions

- The data root should be owned by the Windows user running the app.
- ACL: that user has Modify; `Administrators` may have Full Control; `Users` should not have access unless the business explicitly shares the PC.
- The app must not require administrator rights at daily runtime.
- Prefer per-user installation under `%LOCALAPPDATA%\Programs\GobindasBMS` to avoid writing to `Program Files`; if per-machine is chosen, the installer needs elevation but the app still runs as the user.

### 5.2 Folder checks

At setup and relocation, verify:

- the path is absolute, syntactically valid, and names a folder rather than a
  drive root or a file;
- the folder is not inside the application installation directory (executable
  directory, PyInstaller bundle directory, or repository root);
- the path is not a UNC network path and the drive is not a mapped network
  drive; optical and unavailable drives are refused;
- the location is not a protected Windows system, program, or program-data
  folder;
- an existing folder is readable, or its nearest existing ancestor is readable
  and writable so the chosen folder can be created;
- the user can create, write, flush, close, remove, and verify a uniquely named
  test file; the probe never overwrites a user file;
- free space can be inspected and meets the configured minimum, with the actual
  value shown to the user;
- a removable drive is allowed with an explicit warning that it must remain
  connected whenever the application runs;
- warnings are shown for OneDrive/Dropbox/Google Drive sync paths, because live
  SQLite files can corrupt under sync clients. Phase 3 does not yet detect sync
  clients automatically; the setup text and this document warn against live
  sync. Offer to proceed only with an explicit warning and guidance to sync
  backups instead. Automatic detection is a later hardening item.

### 5.3 Disk encryption

- Strongly recommend BitLocker (or Windows Device Encryption) on the drive holding the data.
- The app cannot verify BitLocker reliably in all editions; where it can, show a recommendation, not a hard block.
- A drive letter (`D:`) is not encryption and not a separate physical disk.

## 6. Application-level access control (conditional)

Authentication is **not invented**. It is conditional on Q-04. If approved:

- Use per-user accounts with a unique username and a salted password hash.
- Preferred algorithm: **Argon2id** (`argon2-cffi`) with a calibrated work factor; fallback: `hashlib.scrypt` with documented parameters if adding a dependency is rejected.
- Never store plaintext, reversible encryption, MD5, SHA-1, or unsalted hashes.
- Enforce a minimum password length and reject common passwords; do not impose arbitrary complexity rules.
- Session lives in memory; idle lock after a configurable period; re-authentication for destructive actions (restore, relocation, user management).
- Roles are explicit and few: e.g., Owner/Admin, Operator, Viewer. Final role names and permissions are Q-04.
- Permission checks occur in application services, not only in the UI.
- The first admin is created by the setup wizard; no default password.
- Password reset by a local admin is a controlled action that is audited; it does not reveal the old password.
- If the only admin password is lost, recovery requires access to the database/backups and is documented as a manual, high-risk procedure.
- Do not implement "security questions" or email-based reset (no server).

If single-user is chosen, the app relies on the Windows account and should still offer an optional idle lock screen (decision pending).

## 7. Application build and update security

- Build only from the pinned environment recorded in ARCHITECTURE.md.
- Install dependencies from PyPI over HTTPS; review new packages before adding.
- Do not vendor unreviewed binaries.
- Generate a SHA-256 checksum for installers and publish it with the release.
- Sign the executables and installer if a certificate is available (Q-19); otherwise explain the SmartScreen warning.
- Do not implement silent auto-update in v1. Updates are explicit installs over the existing version, with the data folder untouched.
- Before an upgrade, the app creates a verified safety backup (ADR-007).
- Keep a reproducible build script; no manual steps that cannot be repeated.

## 8. Database security

- Use SQLAlchemy for parameterized SQL. Raw SQL is allowed only for reviewed, static statements with bound parameters; never string interpolation of user input.
- Enable `PRAGMA foreign_keys=ON` and `trusted_schema=OFF` where compatible.
- Validate identifiers used in dynamic sorting/column selection against an allowlist (never pass UI strings into SQL).
- Run as a normal user, not administrator.
- Do not expose a network listener or a local HTTP API.
- Do not attach arbitrary databases via SQL; open only validated paths.
- Treat SQLite as unencrypted by default. Do not claim otherwise.
- Encryption at rest (SQLCipher) is deferred pending Q-18; it requires a custom SQLite build, key management, backup coverage, and a recovery plan. It is not a checkbox feature.

Phase 2 implementation:

- The database path is injected as an absolute path and never derived from the
  current directory. Parent existence and write permission are checked before a
  new database is created; startup never creates, switches, or deletes a file.
- Every connection applies and then verifies `foreign_keys=ON`,
  `journal_mode=WAL`, `synchronous=FULL`, `busy_timeout`,
  `wal_autocheckpoint=1000`, `temp_store=MEMORY`, and `trusted_schema=OFF`.
- `PRAGMA application_id = 1195525971` rejects an unrelated SQLite file. Alembic's
  revision is compared with the application head; newer or unknown schemas are
  refused.
- Driver failures are translated at the infrastructure boundary into
  `DatabaseUnavailableError`/`MigrationError` with safe user messages. SQL,
  absolute internal details, and file content are not shown in dialogs; technical
  detail goes to the log.
- Health checks never delete, recreate, or repair a file. A write-capability check
  takes `BEGIN IMMEDIATE` and immediately rolls back without changing data.

## 9. Financial integrity controls

- Exact integer/Decimal arithmetic only (DATABASE_SCHEMA.md §4).
- One use case = one short transaction; no partial financial documents.
- Posted documents are voided, never hard-deleted; corrections are explicit and audited.
- Database constraints enforce uniqueness, non-negativity, and status values.
- Reconciliation checks for invoice payments, stock movements, and journal debits/credits.
- Number sequences allocated atomically.
- Imports are staged, validated, previewed, and committed in one transaction; no silent overwrite.
- Reports read the same stored totals as documents; they do not recompute with a different rounding path.

## 10. Audit logging

Audit records live in the database (`audit_logs`) and answer **who did what, when, to which record**.

Record at minimum:

| Action | Examples |
| --- | --- |
| Document lifecycle | create, post, void, restore, renumber |
| Payments | create, allocate, void |
| Inventory | adjustment, valuation change |
| Master data | create, update, deactivate, merge |
| Settings | currency, fiscal year, numbering, backup schedule |
| Security | login success/failure, role change, password reset |
| Data protection | backup create/delete, restore, relocation, integrity check |

Fields: UTC timestamp, actor (Windows user or app user), action, entity type/ID, correlation ID, concise summary, redacted details JSON.

Rules:

- Audit writes share the business transaction when the action affects data.
- No passwords, full personal data, or full document payloads in audit details.
- The UI can view audit history for a record (permission permitting).
- Append-only in the application; there is no edit/delete path.
- Local administrators can modify the file; this is a limitation, not a guarantee. For higher assurance, export audit summaries to an external location periodically.
- Retention is indefinite by default (Q-22); pruning, if ever added, requires an explicit policy.

## 11. Logging and diagnostics

Allowed:

- Timestamps, severity, module, correlation ID, action names, entity IDs, durations, sizes, error codes, file paths of the data root (no customer data), schema/app versions.

Prohibited:

- Passwords, hashes, tokens, encryption keys.
- Full names, phone numbers, emails, addresses, or notes.
- Complete invoice/payment payloads or SQL parameter dumps.
- Backup file contents.

Controls:

- Rotating logs, 5 MB × 5 per process.
- Logs in `%LOCALAPPDATA%`, not in the data root (so they are not backed up with business data).
- Support bundles, if added later, must redact and preview before export.
- A global excepthook logs the traceback but shows only a correlation ID and a safe message to the user.

## 12. Backup security and restore safety

- Backups are full copies of the database and inherit the folder's ACL. Protect them like the live database.
- Every backup is verified with `integrity_check` and `foreign_key_check` before publish; a SHA-256 is recorded in a sidecar.
- Retention never deletes the last or newest valid backup; manual and safety backups are protected.
- Restore always verifies the source, creates a safety backup (or requires typed confirmation when impossible), closes connections, stages, swaps, and verifies before reopening.
- Restore never runs against the live file; stale `-wal`/`-shm` files are removed only after the live file is moved aside and connections are closed.
- A failed restore keeps the original database and the rollback copy.
- Backups are not off-site. The UI must recommend a periodic copy to a separate physical device kept offline.
- Do not sync a live database via cloud folders; sync verified backups only, with the app closed.
- If encryption is added later, both the live database and backups must be encrypted, with a tested key-recovery procedure.

See BACKUP_STRATEGY.md for the operational detail.

## 13. File handling: attachments and exports

### 13.1 Attachments

- Allowlist extensions and verify MIME type/signature where practical (PDF, JPG, PNG; Q-24).
- Maximum size per file (default 10 MB) and per record (configurable).
- Store under a generated path; never use the user's filename as the only path component; strip separators and reserved Windows names.
- Store a SHA-256 and size; detect duplicates if useful.
- Never execute or preview with a browser engine; use the OS default viewer only on explicit user action.
- Deleting an attachment is logical; orphan cleanup is an explicit maintenance action.
- Reject paths that resolve outside the data root (path traversal).

### 13.2 Exports

- Write to a temporary file in the destination folder, then atomically rename; never partially overwrite an existing export.
- If the target exists, ask before replacing.
- Sanitize filenames: remove `<>:"/\|?*`, control characters, and trailing dots/spaces; enforce a length limit.
- Excel: prefix cells starting with `=`, `+`, `-`, `@`, tab, or CR with an apostrophe so they are treated as text (formula injection defense), while keeping numeric cells numeric.
- PDF/Excel metadata must not include machine paths or secrets.
- Exports are business data: the UI reminds the user to store them securely.

## 14. Data-loss prevention controls

| Control | Implementation |
| --- | --- |
| Destructive confirmation | Named object + consequence; typed confirmation for restore/delete |
| Void instead of delete | Financial documents keep history; no hard delete |
| Soft-deactivate | Masters use `is_active`; history remains |
| Transaction atomicity | UoW commit/rollback; no partial postings |
| Migration safety | Pre-upgrade verified backup; refuse newer schema; rollback on failure |
| Phase 4 migration reality | Pending/newer/unknown schemas refuse startup; maintenance schema changes require a verified safety-backup gate; normal startup never auto-migrates |
| Restore safety | Pre-restore safety backup; staged swap; rollback copy |
| Backup retention guards | Never delete last/newest valid; manual/safety untouched |
| Missing drive | Blocking error; no fallback; no auto-create |
| Single instance | Prevent two writers |
| Backup lock | Prevent overlapping jobs |
| Free-space checks | Before backup, restore, relocation, export |
| Disk-full handling | Abort cleanly; keep original |
| Crash recovery | Detect interrupted restore/backup markers; never auto-complete blindly |
| Config safety | Atomic writes; corrupt config preserved; business data untouched |
| Log/report safety | Redaction rules; no secrets |

## 15. Incident response (owner-facing)

### 15.1 Suspected database corruption

1. Do not keep writing to the same file.
2. Close the app.
3. Copy the entire `Database\` folder (including WAL/SHM) somewhere safe for diagnosis.
4. Open the app and use **Restore** with the newest verified backup; note the safety backup created.
5. If no recent backup exists, contact support with the logs and the folder copy.
6. Never run third-party "SQLite repair" tools on the only copy.

### 15.2 Ransomware or malware

1. Disconnect the PC from the network.
2. Do not pay; do not run cleanup tools that may delete backups.
3. Use a known-good device to check the offline backup copy.
4. Restore on a clean Windows installation using a verified backup.
5. Rotate any credentials that were stored on the machine.

### 15.3 Lost or stolen device

1. If BitLocker was enabled, follow the recovery-key process.
2. Assume the data is exposed if the disk was unencrypted.
3. Restore business operations from an offline backup on a new device.
4. Change Windows account passwords and any related business passwords.

### 15.4 Restored the wrong backup

1. The pre-restore safety backup is retained; restore it.
2. Check the audit log and backup history to confirm which file was used.
3. Record the incident; review the confirmation step if user error was easy.

## 16. Security acceptance checklist

- [ ] App runs without administrator rights.
- [ ] Data root is outside the installation directory and validated.
- [ ] UNC/live-sync paths are blocked or explicitly warned.
- [ ] No plaintext passwords or secrets in config, logs, exports, or code.
- [ ] Password hashing is salted and slow, if authentication exists.
- [ ] All SQL is parameterized; dynamic identifiers use allowlists.
- [ ] Money arithmetic uses exact types only.
- [ ] Every backup is verified; retention guards tested.
- [ ] Restore safety backup test passed; rollback test passed.
- [ ] Attachment paths cannot escape the data root.
- [ ] Excel exports neutralize formula injection.
- [ ] Destructive actions are explicit and confirmed.
- [ ] Audit events cover security and financial operations.
- [ ] Logs contain no sensitive payloads (reviewed sample).
- [ ] Build is reproducible; dependencies pinned; checksums published.
- [ ] Code signing decision recorded (Q-19).
- [ ] Encryption-at-rest decision recorded (Q-18).
- [ ] The limitations of local backups and unencrypted SQLite are visible in the UI/help.

## 17. Open security decisions

| ID | Decision | Default until answered |
| --- | --- | --- |
| Q-04 | Single user vs multi-user auth/roles | Single user, no login |
| Q-18 | Encrypt database and backups? | No; recommend BitLocker + offline copy |
| Q-19 | Code signing certificate | No; document SmartScreen |
| Q-21 | Off-site backup requirement | Recommend manual periodic copy |
| Q-22 | Audit retention and visibility | Keep indefinitely; owner-visible |
| Q-24 | Attachment types and size limits | PDF/JPG/PNG, 10 MB |
| SQ-01 | Idle-lock when no login is used? | Off until approved |
| SQ-02 | Support-bundle export feature? | Not in v1 |
| SQ-03 | Password reset recovery procedure (if auth) | Manual, documented, audited |

## 18. Phase 2 database protection record (2026-11-13)

### 18.1 Permissions and location

- Configuration lives in `%APPDATA%\GobindasBMS\config.json`; logs in
  `%LOCALAPPDATA%\GobindasBMS\logs`; the database is wherever the owner configures
  an absolute path through the Phase 3 setup wizard (see §19).
- A missing drive or parent folder is a blocking error. The application never
  falls back to `C:`, the project directory, or another existing file.
- Before creation, the folder is probed with a uniquely named temporary file that
  is removed immediately. The existing database file is not touched.
- Creation requires an explicit `migrate init`; startup never creates a file.

### 18.2 Corruption and unavailable-file handling

- A corrupt, locked, permission-denied, or missing file produces a specific
  `DatabaseHealthStatus` and an actionable message. The application does not
  delete, recreate, truncate, or repair it automatically.
- A wrong `application_id` is refused as "not a Gobindas Graphics database".
- A newer/unknown schema is refused; this version never downgrades it.
- Full `PRAGMA integrity_check` is opt-in for support/maintenance because it scans
  the file. Normal startup only checks accessibility, identity, and revision.
- `PRAGMA quick_check` and `PRAGMA foreign_key_check` are reusable diagnostics.

### 18.3 Connection safety

- One bounded `QueuePool` (two connections, no overflow) and short-lived sessions.
- `UnitOfWork` never commits implicitly; a missing commit or an exception rolls
  back. Sessions always close and connections return to the pool.
- Shutdown checkpoints WAL best-effort then disposes the engine. Failures during
  checkpoint are logged, not hidden.
- WAL sidecars are not backed up independently and do not expose business data
  beyond the same user-account permissions as the main file.

### 18.4 Residual risks

- SQLite files are unencrypted; permissions and Windows account security are the
  primary controls. Q-18 remains open.
- Any process running as the same Windows user can read or modify the database.
- Backups, restore, and destructive confirmations are not implemented yet; their
  controls remain described in BACKUP_STRATEGY.md.

## 19. Phase 3 setup and location protection record (2026-11-14)

### 19.1 Folder permissions and validation

- The owner selects one absolute business data root. The application never
  derives it from the working directory, the installation directory, or `C:`.
- The location must be a named folder on a local fixed, removable, or
  unknown-with-warning drive. Drive roots, UNC paths, mapped network drives,
  optical drives, protected Windows/program folders, and installation paths are
  refused before anything is created.
- An existing folder must be readable. A missing folder may be created only when
  its nearest existing ancestor is readable and writable.
- Write access is proven with a uniquely named probe file created, written,
  flushed, closed, removed, and checked. No user file is touched.
- Free space is read from the drive and shown to the user. The initial check
  requires a small documented minimum; it is not presented as a capacity
  forecast.
- Removable drives are accepted with a warning that removing the drive blocks
  startup. The warning does not claim that a drive letter identifies a physical
  disk.

### 19.2 Drive availability and UNC policy

- The live SQLite database is local-only. UNC and mapped network drives are
  rejected at setup and at startup.
- If the configured drive is absent at startup, the application does not create
  folders, create a database, or change the saved path. The recovery dialog
  explains the reason and offers Retry, Locate existing data, Start a new setup,
  or Exit.
- Locating existing data validates the Gobindas `application_id`, Alembic
  revision, and database health before the connection is accepted.
- The status bar distinguishes unconfigured and configured databases, and the
  dashboard shows the verified data root and database path.

### 19.3 Configuration protection

- The configuration file remains outside the business data root in
  `%APPDATA%\GobindasBMS\config.json`.
- The complete configuration is written to a temporary file in the same
  directory, flushed, fsynced, validated, and atomically replaced. The saved
  file is then re-read and compared with the verified setup result.
- The existing settings are preserved: INR (`INR`, `₹`, 2 decimals, Indian
  grouping), theme, logging, and schema version. Regression tests assert this.
- A corrupt configuration is preserved as `config.corrupt-<timestamp>.json`;
  defaults are used for diagnosis and the recovery dialog is shown. The original
  file is never silently deleted.
- Logs record path decisions and failure reasons but not business payloads,
  credentials, or full file contents.

### 19.4 Database overwrite prevention

- Setup never overwrites, truncates, migrates, or replaces an existing database.
- An existing file is opened through the Phase 2 verification path. Only a
  healthy Gobindas database at the expected revision is adopted. Unknown,
  corrupt, uninitialized, and newer databases are refused with an explanation.
- Database creation goes through `MigrationManager.create_database()`. No
  `Base.metadata.create_all()` and no manual Alembic revision insert is used.
- The location is persisted only after identity, revision, and full health checks
  pass.
- If configuration persistence fails, the verified database is kept and the
  user can retry the save; it is not deleted to make the error disappear.

### 19.5 Setup recovery behavior

- Cancelling before initialization leaves no database, no data-root folder, and
  no saved location. The next launch offers setup again.
- A failed scaffold or initialization removes only empty directories created by
  that attempt and preserves every pre-existing file and folder.
- The recovery dialog never creates a replacement database, never changes the
  saved path silently, and never opens an empty database.
- Restore is implemented in Phase 4 as a staged, verified workflow with a
  mandatory safety backup and rollback (available from the Backup view for
  verified managed backups). The startup recovery dialog does not yet expose a
  direct restore action; it blocks unsafe states and points to recovery using
  verified safety backups when required.

### 19.6 Residual risks

- SQLite files and backups are unencrypted; Windows account security and
  BitLocker remain the primary controls (Q-18).
- Any process running as the same Windows user can read or modify the database.
- Sync-client folders are not detected automatically in Phase 3.
- Backup, restore, retention, and relocation controls are implemented in
  Phase 4 as staged, verified workflows (Online Backup API, checksums/metadata,
  cross-process locking, safety backups, and rollback/recovery markers). Manual
  Windows integration drills remain necessary before release reliance.
