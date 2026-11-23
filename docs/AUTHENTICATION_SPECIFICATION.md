# AUTHENTICATION SPECIFICATION — Local Desktop Accounts

| Field | Value |
| --- | --- |
| Document | AUTHENTICATION_SPECIFICATION.md |
| Phase | 8A specification; 8B implementation |
| Version | 1.0 (owner-approved specification 2026-11-22); 8B implementation note added 2026-11-23 |
| Date | 2026-11-22 |
| Status | SPECIFICATION APPROVED 2026-11-22 — IMPLEMENTED IN PHASE 8B, owner review pending |
| Related | AUTHORIZATION_MATRIX.md, USER_ACCOUNT_WORKFLOWS.md, SESSION_AND_IDLE_LOCK_SPECIFICATION.md, PHASE_08_OWNER_DECISION_WORKSHEET.md, PHASE_08_IMPLEMENTATION_READINESS.md, SECURITY_AND_DATA_PROTECTION.md, ARCHITECTURE.md, OPEN_DECISIONS.md |

This document specifies the approved native Windows desktop authentication design. It was written as specification-only in Phase 8A; the approved portions were implemented in Phase 8B after explicit owner authorization on 2026-11-22. Requirements marked proposed (`P`) or owner decision (`O`) remain unimplemented. See `Reports/PHASE_08B_REPORT.md` for the implementation record.

## Phase 8B implementation status (authoritative)

Implemented: Argon2id hashing via `argon2-cffi` with the exact approved parameters and a self-describing scrypt fallback; first-run owner creation; local accounts with case-insensitive unique usernames; generic failed-login messages with five-attempt/15-minute throttling in `login_throttles`; in-memory-only sessions; password change and administrative reset; append-only authentication audit events; startup first-run/login gate; native Qt dialogs. Migration `0004_authentication` adds `roles`, `users`, and `login_throttles` and seeds only the four approved role reference rows — no user account is seeded.

Not implemented: cloud/remote identity, email/OTP recovery, default accounts, in-app recovery backdoors, and every proposed (`P`) or open (`O`) permission. Historical Phase 8A statements that describe the system as unimplemented are retained as the approved design record and are superseded by this section where they conflict.

## 1. Scope and confirmed decisions

Confirmed by the Phase 8A owner instruction:

- Multiple **local user accounts** belong to the local installation.
- No cloud identity provider, remote authentication, email recovery, OTP, web server, or web authentication framework.
- Role-based access control with exactly four approved role names: Owner/Admin, Operator, Accountant/Reviewer, Viewer.
- Password recovery is manually managed by Owner/Admin; no self-service recovery.
- Password changes and administrative resets are distinct audit events.
- Automatic idle lock after 15 minutes, configurable; password required to unlock; lock/unlock events recorded.
- Authentication is a native PySide6 desktop feature.

Not confirmed, and therefore not implementation-ready:

- Password length/complexity, throttling/expiry, administrator administration limits, Accountant/Reviewer and Viewer permission scopes, Operator module-specific sensitive permissions, and session edge cases. Account identity is fully resolved (`P8A-01`, 2026-11-22): login identity is a **username only**, with email as an optional contact field, case-insensitive uniqueness, and Owner/Admin-only username rename. See `PHASE_08_OWNER_DECISION_WORKSHEET.md`.

## 2. Architecture placement

Authentication must follow the existing modular-monolith boundaries:

| Layer | Proposed responsibility | Constraint |
| --- | --- | --- |
| Domain | `UserAccount`, `RoleKey`, `PermissionKey`, `PasswordHash` value object, authentication result types, audit event definitions | No Qt, SQLAlchemy, or filesystem dependencies; consistent with `tests/test_architecture.py` import boundaries. |
| Application | `AuthenticationService`, `UserAccountService`, `PasswordChangeService`, `AdministrativePasswordResetService`, `SessionService`, `AuthorizationService`, `ActorProvider` | All sensitive operations enforce authorization here, never only in the UI. |
| Infrastructure | User/role/permission repositories, password hasher, auth audit event sink, auth settings repository | SQLAlchemy transactions only; schema changes require a future reviewed Alembic migration. |
| Presentation | Login, first-run owner creation, user management, password change/reset, locked/unlock screens | Views call application services; no credential logic in widgets. |

Application services must receive an authenticated actor or the explicit system actor from a centralized `ActorProvider`. Hardcoded role-name comparisons distributed across services and views are prohibited.

## 3. Password storage

### 3.1 Algorithm

Owner-approved design (2026-11-22): **Argon2id through `argon2-cffi`** with a calibrated work factor; `hashlib.scrypt` fallback if the new dependency is rejected. No dependency or hashing code was added in Phase 8A.

- **Argon2id** through `argon2-cffi`, with a calibrated work factor.
- Starting parameters approved by the owner, subject to final security review before implementation:
  - `time_cost = 3`
  - `memory_cost = 65536` KiB (64 MiB)
  - `parallelism = 1`
  - `hash_len = 32` bytes
  - 16-byte cryptographically random salt per password
  - Store a single PHC-formatted string containing algorithm, parameters, salt, and hash.

Owner-approved fallback if adding a dependency is rejected (**final values confirmed 2026-11-22 after security review**):

- `hashlib.scrypt` with `N = 2**17`, `r = 8`, `p = 1`, `dklen = 32`, and a 16-byte cryptographically random salt.
- `hashlib.scrypt` must be called with an explicit `maxmem` above 128 MiB; the OpenSSL default 32 MiB limit rejects `N = 2**17`.
- Store algorithm identifier, parameters, salt, and derived key in a self-describing encoded string so parameters can be upgraded later.

The algorithm/design and dependency direction are owner-approved (2026-11-22). The final parameter security review was completed 2026-11-22; see §3.1.1. This phase does not add a dependency.

### 3.1.1 Final parameter security review (2026-11-22)

Reference: OWASP Password Storage Cheat Sheet (accessed 2026-11-22). It gives Argon2id minimum configurations of 19 MiB/`t=2`/`p=1` or 12 MiB/`t=3`/`p=1`, scrypt minimum configurations including `N=2^17, r=8, p=1` and `N=2^14, r=8, p=5`, a target of under one second per hash, and recommends the modular PHC string format for parameter upgrades.

| Item | Specified value | Review result |
| --- | --- | --- |
| Argon2id parameters | `m=65536` KiB (64 MiB), `t=3`, `p=1`, `hash_len=32` | **Accept.** Above the cited OWASP minimums. Benchmark on target hardware during Phase 8B; acceptance target under one second per verification. |
| Salt | 16-byte cryptographically random, unique per password | **Accept.** Consistent with guidance. |
| Storage format | Self-describing PHC string | **Accept.** OWASP recommends a standard format so parameters can be upgraded later. |
| Originally proposed scrypt fallback | `n=2^14`, `r=8`, `p=1`, `dklen=32`, 16-byte salt | **Deficiency:** at `N=2^14` the cited OWASP minimum is `p=5`; `p=1` is below it. Local benchmark ~0.053 s. Superseded. |
| Final scrypt fallback (**owner-approved 2026-11-22**) | `N=2^17`, `r=8`, `p=1`, `dklen=32`, 16-byte salt, explicit `maxmem` above 128 MiB | OWASP minimum configuration; local benchmark ~0.365 s. Replaces the deficient starting values. |
| Python `hashlib.scrypt` limit | — | `N=2^17` fails with OpenSSL's default 32 MiB limit ("memory limit exceeded"); implementation must pass an explicit `maxmem` above 128 MiB. |
| Pepper | Not specified | Optional defense-in-depth only; no change. Would require a separate owner decision and secret-management design. |
| Unicode passwords | — | Phase 8B must pass full Unicode input without lossy normalization or truncation; verify the chosen library accepts it. |

Verdict: Argon2id parameters are accepted unchanged. The owner approved the final scrypt fallback `N=2^17, r=8, p=1` (with explicit `maxmem`) on 2026-11-22, replacing the deficient starting values. Benchmarks were measured on this Windows development machine with Python's standard library; they do not replace target-hardware validation in Phase 8B.

### 3.2 Prohibitions

- Never store plaintext, reversible encryption, MD5, SHA-1, or unsalted hashes.
- Never log passwords, password hashes, salts, reset tokens, or any authentication secret.
- Never place passwords in exception messages, dialogs, config files, audit payloads, or user-visible status messages.
- Never pre-fill or retain a typed password after a failed or successful operation.
- Do not implement security questions, email recovery, OTP, or self-service reset.

Verification must use constant-time comparison supplied by the hashing library. On successful authentication, if stored parameters differ from the current policy, the hash may be transparently rehashed with the new parameters within the same operation; this rehash is an internal credential update and must not be exposed as a password change event.

### 3.3 Password rules

Approved rules so far under `P8A-02` (owner decisions 2026-11-22): **minimum password length of 8 characters**; **at least one uppercase letter, one lowercase letter, and one digit**; and password confirmation at first-run account creation (password and confirmation must match). Failed logins trigger a **temporary cooldown after 5 consecutive failed attempts for 15 minutes** with auditing (owner decision 2026-11-22). **Users may change their own password at any time** after verifying the current one (no forced first-login change), and **passwords do not expire** (owner decisions 2026-11-22). No symbol requirement and no permanent/manual-unlock lockout are approved.

## 4. Core operations

Each operation below is a specification of future application services. Authorization checks are permission-based and enforced in the application layer.

### 4.1 First-run owner creation

See `USER_ACCOUNT_WORKFLOWS.md`. Key rules: explicit setup workflow only; no seeded/default account; password confirmation; duplicate-account prevention; interruption must not leave an installation with no active Owner/Admin account. Account identity is resolved (`P8A-01`, 2026-11-22): the login identity is a username; email is optional and not mandatory; uniqueness is case-insensitive; username rename is Owner/Admin-only.

Audit event: `auth.owner_account_created` with actor `system/unauthenticated`, because no authenticated user exists yet. No secret in payload.

### 4.2 Login

1. Present native login screen before the main window is shown.
2. Resolve the account by username with case-insensitive matching (approved identity rule, `P8A-01` 2026-11-22).
3. Verify the password hash.
4. On failure, return a generic user message that does not reveal whether the identity exists.
5. On success, create an in-memory authenticated session with user ID, stable identity label, role assignment snapshot, login timestamp, and last-activity timestamp.
6. Record `auth.login_succeeded`.
7. Failed login may record `auth.login_failed` with identity label only if the owner approves failed-login auditing scope; the Phase 8A prompt permits “where appropriate”. No password or hash is ever recorded.

### 4.3 Logout

- Explicit logout clears the in-memory session, returns to the login screen, and records `auth.logout`.
- Logout must revoke any pending privileged re-authentication state.
- Closing the application while locked does not create a persisted session; see `SESSION_AND_IDLE_LOCK_SPECIFICATION.md`.

### 4.4 Password change (self-service)

- Requires the current authenticated user and the existing password.
- New password and confirmation must match and satisfy the approved `P8A-02` policy (minimum 8 characters; uppercase + lowercase + digit).
- On success, write a new hash, record `auth.password_changed`, and invalidate other in-memory privileged state.
- The current session may remain authenticated unless the owner decides otherwise; re-authentication for sensitive operations is preserved.

### 4.5 Administrative password reset

- Owner/Admin-only permission `user.reset_password`.
- The administrator sets a new temporary or replacement password through an explicit dialog; the old password is never displayed, derived, or logged.
- Record `auth.password_reset_admin`, distinct from `auth.password_changed`.
- Immediately invalidate the target user's authenticated session and privileged re-authentication state. If the target is the current user, require re-login.
- The reset procedure is approved (`P8A-08`, 2026-11-22): an Owner/Admin enters a new password with confirmation in an explicit dialog; no generated temporary password. If all admin credentials are unavailable, a documented offline owner procedure is followed (`P8A-08`, 2026-11-22); there is no in-app backdoor or recovery key.

### 4.6 Unlock

- Password of the locked-in user is required.
- Successful unlock resets the idle timer and records `auth.unlock`.
- Failed unlock is treated as a failed authentication attempt and counts toward the approved 5-attempt/15-minute cooldown (`P8A-02`).
- Unlock does not create a new identity; it resumes the existing in-memory session.

## 5. Actor attribution and audit integration

Existing Business Profile events use `system/unauthenticated`. That behavior must be preserved; historical rows must not be edited.

New authentication and sensitive-operation events must use an actor derived from the authenticated session:

- stable user ID and non-sensitive identity label,
- role snapshot at event time,
- no password, hash, salt, token, or full personal data.

Events occurring before authentication (setup, migration, failed login when no identity is established, first-run owner creation) use `system/unauthenticated`.

All new events must use the existing append-only `audit_events` table and its established protections: insertion-only repository API, immutable ORM records, SQLAlchemy `before_flush` guard, and SQLite `BEFORE UPDATE`/`BEFORE DELETE` triggers. Indefinite retention remains in force. No new retention setting or cleanup path may be added.

## 6. Session state

Persisted:

- User accounts, password hashes, status, role assignments, and authentication settings (if any) after a future approved migration.
- Audit events in the existing append-only table.

In-memory only:

- Authenticated user ID and role snapshot.
- Login and last-activity timestamps.
- Privileged re-authentication state for destructive actions.
- Lock state.

Not persisted:

- Passwords, hashes in config, session tokens, unlock tokens, or reset secrets in logs/config/audit payloads.

`QSettings` currently stores window geometry and navigation only; it must not be repurposed for authentication state.

## 7. Security boundaries

- UI visibility is advisory only; every sensitive view model or application service call must call `AuthorizationService.require(permission_key)`.
- Hiding a menu item, button, or navigation entry is not authorization.
- Locked state must block navigation, view creation, dialogs, and service calls — not merely cover the window with a widget.
- Backup restore, database relocation, schedule changes, user management, role/permission changes, and application-wide settings require explicit permissions and audit events.
- Permission checks must be centralized; do not scatter role-name string comparisons.
- The application remains offline and must not open a network listener or local HTTP API.
- A local Windows administrator or sufficiently privileged malware can still bypass application controls; documentation must not claim otherwise.

## 8. Future schema direction (no migration in Phase 8A)

Phase 8A does not create tables or migrations. A future approved phase will propose:

- `users` with stable ID, identity fields, password hash string, status, creation/update metadata.
- `roles` with the four approved role keys.
- `permissions` with centralized permission keys.
- `role_permissions` assignment table.
- `user_roles` assignment table with strategy resolved by owner decision `P8A-03` (2026-11-22): multiple Owner/Admin accounts allowed and exactly one role per user.
- Authentication settings only if genuinely persistent; idle timeout may live in config if approved.

The final schema must follow `DATABASE_SCHEMA.md` naming, constraint, timestamp, and Alembic-only migration rules. No session table is proposed unless an owner decision requires persistent sessions, which this specification does not recommend.

## 9. Implementation readiness

This specification and the authorization matrix were **explicitly approved by the owner on 2026-11-22** (documentation approval only). Phase 7D owner acceptance was recorded 2026-11-22 (`Reports/PHASE_07D_ACCEPTANCE.md`), the hashing-parameter review was completed, and the final scrypt fallback values were owner-approved 2026-11-22 (§3.1.1). The owner explicitly authorized Phase 8B implementation on 2026-11-22; Phase 8B implemented the approved `A`-marked scope and left `P`/`O` permissions unimplemented. Owner review/acceptance of the implementation remains pending. See `PHASE_08_IMPLEMENTATION_READINESS.md` and `Reports/PHASE_08B_REPORT.md`.
