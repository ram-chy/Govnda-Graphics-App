# PHASE 08B REPORT — Authentication, Local User Accounts, Roles & Permissions Implementation

| Field | Value |
| --- | --- |
| Phase | 8B — implementation |
| Date | 2026-11-23 |
| Authorization | Owner explicitly authorized Phase 8B implementation on 2026-11-22 |
| Status | Implementation complete; owner personally tested Windows app and formally accepted Phase 8B on 2026-11-23 |
| Related prompt | `Prompt/Phase 8B — Authentication, Local User Accounts, Roles & Permissions Implementation.md` |

## 1. Phase Overview and Implementation Scope

Phase 8B implemented the owner-approved Phase 8A authentication design only. The delivered slice covers local native accounts, first-run Owner/Admin creation, username-only login, exactly four approved roles, centralized service-layer authorization, failed-login throttling, an in-memory session with idle lock, password change and administrative reset, append-only audit integration, UI dialogs, migration `0004_authentication`, tests, documentation, and this report.

Deliberately out of scope and **not implemented**: new business modules, accounting functionality, approval workflows or amount thresholds, new roles, `P`/`O` permissions, cloud/remote authentication, email/OTP recovery, default or seeded users, in-app recovery backdoors, multi-company/multi-tenant support, audit editing/deletion, database reset or destructive migration, and unrelated UI redesign.

## 2. Repository State Before and After

- **Branch:** `main`
- **Head commit:** `c84724b Implement Phase 7B-1 audit retention policy correction`
- **Before:** the worktree was already dirty with preserved Phase 7C/7D/8A work and untracked planning/report files. No files were staged and no commits or pushes had been made for that work.
- **After:** the same head commit remains checked out. The worktree contains 30 modified tracked entries and 33 untracked entries, including this report. No files are staged; no commit, push, or history rewrite was performed.
- **Data protection:** all automated tests used isolated temporary databases and temporary `APPDATA`/`LOCALAPPDATA` paths. The owner's configured database at `D:\Development\test db\Database\BusinessManagement.db` was not opened, migrated, seeded, or modified for testing.

## 3. Architecture and Implementation Details

- **Domain** (`app/domain/auth.py`): `RoleKey`, `PermissionKey`, the approved role-permission map, username/password validation, non-secret account/session value objects, actor labels, and authentication/administration event names. The module has no Qt, database, or filesystem dependencies.
- **Infrastructure** (`app/infrastructure/security/`, `app/infrastructure/database/`): Argon2id/scrypt password hashing, ORM records and repositories for `roles`, `users`, and `login_throttles`, plus integration with the existing append-only `audit_events` table.
- **Services** (`app/services/`): `SessionService`, `AuthorizationService`, `AuthenticationService`, `UserAccountService`/`PasswordService`, `AuthAuditService`, `AuthServices`, and `SensitiveOperationService`. `AppContext` composes one shared auth graph and passes it to backup, restore, relocation, schedule, and Business Profile services.
- **Live database resolution:** auth services resolve the current database through `DatabaseRuntime`, so restore and relocation cannot leave stale authorization or audit connections.
- **Presentation** (`app/ui/`): native Qt first-run, login, lock/unlock, password-change, and local-user-management dialogs; TopBar account controls; session status; main-window event filter/timer and close handling. `app/ui/auth/session_guard.py` provides a reusable idle-lock implementation; the active main window currently installs its own equivalent idle monitor/lock flow.

UI hiding/disabling is advisory only. All protected operations are enforced through service-layer authorization checks.

## 4. Database Migration and Schema Changes

Migration `migrations/versions/0004_authentication.py` (revision `0004_authentication`, down revision `0003_business_profile_requirements`) adds only new tables:

| Table | Schema and safeguards |
| --- | --- |
| `roles` | `key` primary key and `display_name`; four idempotent reference rows only: `owner_admin`, `operator`, `accountant_reviewer`, `viewer`. |
| `users` | Integer `id`; unique `username_key` for case-insensitive identity; display `username`; optional `email`; self-describing `password_hash`; 0/1 `is_active` flag; `role_key` foreign key constrained to the four approved roles; `created_at`/`updated_at`; indexes on role and active status. |
| `login_throttles` | `username_key` primary key, non-negative `failed_count`, `first_failed_at`, and nullable `cooldown_until`, persisting the five-attempt/15-minute cooldown across restarts. |

No existing table, Business Profile record, historical audit row, or backup setting was changed. No user is seeded. There is no `user_roles` table and no session table. Downgrade from this revision is refused while user accounts or audit history exist.

## 5. Authentication Implementation

- **First run:** production startup with no accounts shows `FirstRunDialog` and requires explicit Owner/Admin creation before the main window. No default username or password exists.
- **Login:** username-only, case-insensitive, with optional email used only as contact data. Success starts the single in-memory session.
- **Generic failures:** invalid username, wrong password, and deactivated accounts all return `GENERIC_AUTH_FAILURE` (`"The username or password is incorrect."`) without disclosing account existence.
- **Throttling:** five failed attempts start a 15-minute cooldown (`FAILED_ATTEMPT_LIMIT = 5`, `COOLDOWN_SECONDS = 900`) persisted in `login_throttles`. Cooldown expiry permits a new attempt; successful login clears the throttle.
- **Password change:** self-service change verifies the current password and applies the approved password policy.
- **Administrative reset:** Owner/Admin enters a new password with confirmation in an explicit dialog; the old password is never revealed.
- **Smoke mode:** `--smoke-test` skips the interactive auth gate and does **not** create or authenticate a known test account. Automated smoke tests use isolated temporary config/database paths.

## 6. Password Hashing Implementation and Exact Parameters Used

`app/infrastructure/security/password_hasher.py` fails closed if no approved algorithm is available and never logs plaintext passwords, hashes, salts, or reset secrets.

**Primary — Argon2id via `argon2-cffi` 25.1.0:**

- `time_cost = 3`
- `memory_cost = 65536` KiB (64 MiB)
- `parallelism = 1`
- `hash_len = 32`
- random 16-byte salt
- PHC-formatted string storage
- verification through `argon2-cffi`; rehash check through `check_needs_rehash`

**Fallback — `hashlib.scrypt`:**

- `N = 2**17`
- `r = 8`
- `p = 1`
- `dklen = 32`
- random 16-byte salt
- explicit `maxmem = 140000000` (above 128 MiB)
- self-describing `scrypt$N=...,r=8,p=1,dklen=32$<salt>$<digest>$` storage
- constant-time digest verification with `hmac.compare_digest`

A real defect was corrected during implementation: `argon2-cffi` exposes `check_needs_rehash`, not `needs_rehash`; without the fix every freshly created Argon2id hash was incorrectly flagged for rehash.

## 7. Role and Permission Implementation

Exactly four roles are implemented: `owner_admin`, `operator`, `accountant_reviewer`, and `viewer`.

- **Owner/Admin:** every approved role-grantable permission, i.e. every `PermissionKey` except `auth.login`.
- **Operator, Accountant/Reviewer, Viewer:** only `auth.logout`, `auth.unlock`, and `auth.password_change_self`.
- **`auth.login`:** an unauthenticated entry point, intentionally absent from all role grants.
- **`audit.modify`:** not defined or granted to any role.
- **`P`/`O` permissions:** deliberately absent from the enum and denied by default.

`AuthorizationService.has_permission()`/`require()` re-read the live account role and active status on each check. Role changes and deactivation therefore take effect at the next authorization check. Locked sessions deny protected operations. Sensitive restore, relocation, schedule/settings, and Business Profile operations call the service-layer gates directly.

## 8. Session and Idle-Lock Implementation

- One in-memory session only; nothing auth-related is written to `QSettings` or any session table.
- Default idle timeout is 15 minutes (`900` seconds), configurable through positive-integer `AppConfig.idle_timeout_seconds`.
- Deliberate keyboard, mouse, wheel, and touch events reset the timer; timer ticks and non-interaction events do not.
- The timeout continues while modal dialogs are open because lock evaluation is driven by wall-clock idle time on the main timer.
- On timeout the session locks and an application-modal `LockDialog` requires the locked-in user's password.
- Esc/close cannot dismiss the lock screen silently; an explicit **Exit application** control ends the session and quits. Closing the main window while locked also ends the session.
- Hot switching is not supported: logout ends the session and requires a fresh login.
- Lock/unlock state blocks service-layer authorization as well as UI controls.

## 9. Audit Integration

The existing append-only `audit_events` table, repository guards, immutable ORM protection, and SQLite update/delete triggers remain unchanged. New append-only events cover owner creation, login success/failure, logout, lock/unlock, self password change, administrative password reset, user create/update/activate/deactivate, role assignment, settings changes, backup restore, database relocation, and access denial where explicitly emitted.

Authenticated actions use a non-secret actor such as `user:1:Owner`; pre-authentication events use `system/unauthenticated`. Historical Phase 7B audit rows were not edited. No plaintext password, hash, salt, or reset secret is written to any audit payload. Migration downgrade protection prevents removal of authentication data or append-only audit history.

## 10. UI Screens and Workflows

- **FirstRunDialog:** validates username and password with confirmation before creating the initial Owner/Admin.
- **LoginDialog:** username/password login with generic failure feedback and cooldown feedback.
- **LockDialog:** application-modal unlock screen with explicit exit path.
- **PasswordChangeDialog:** current-password verification plus policy-checked new password and confirmation.
- **UserManagementDialog:** create user, edit identity/rename, assign role, activate/deactivate, and administrative password reset.
- **MainWindow/TopBar:** Users, Password, and Logout controls are shown only when permitted and authenticated; a session status label shows the signed-in user. Restore/move/schedule controls are advisory-disabled by permission while services remain authoritative.

## 11. Tests Executed and Exact Results

Executed with the project virtual environment on 2026-11-23 (latest verification run after doc/report cleanup):

```text
.venv/Scripts/python.exe -m pytest tests/test_auth_phase8b.py -q
65 passed in 22.04s

.venv/Scripts/python.exe -m pytest -q
602 passed in 74.96s (0:01:14)

.venv/Scripts/python.exe -m ruff check .
All checks passed!
```

Previous recorded Phase 8B verification in this same worktree also included: `pytest --tb=short -q` → `602 passed in 81.37s (0:01:21)`, focused auth suite `106 passed in 41.03s`, and startup smoke `13 passed in 25.11s` with exit code `0`, `Main window shown`, and no `CRITICAL`/`Traceback` entries. Focused Phase 8B coverage includes password policy and hashing parameters, first-run owner creation, duplicate/case-insensitive usernames, login success/failure, deactivated accounts, cooldown and expiry, throttle persistence, no account-existence leak, password change/reset, role-permission matrix, service-layer bypass attempts, last-active-admin protection, deactivation and role-change effects, idle lock/unlock, locked-service denial, audit events and actor attribution, append-only protection, no plaintext in audit payloads, and service authorization for restore/relocation/schedule.

## 12. Ruff/Static-Check Results

```text
.venv/Scripts/python.exe -m ruff check app migrations tests --output-format concise
All checks passed!
```

Python compilation was also checked during implementation with `compileall`; no syntax errors were found.

## 13. Regression Results

- Full suite: **602 passed**; no failures.
- Existing Phase 1–7 behaviour remained green, including startup, backup, restore, relocation, schedule, Business Profile, audit retention, and migration tests.
- `tests/test_database_migrations.py` was updated to expect the new `0004_authentication` revision and its three tables.
- `tests/test_audit_retention.py` was updated to recognize that Phase 8B intentionally adds audited settings/administrative events; destructive-SQL and append-only checks still pass.
- Startup smoke tests still log `Main window shown` and exit `0` with isolated configuration and no seeded account.

## 14. Known Limitations and Deferred Items

- No dedicated Owner/Admin audit viewer/export UI was added; `audit.view`/`audit.export` permissions and the `audit.exported` event name exist, but an export workflow is deferred.
- No dedicated settings UI for the idle timeout; it is configurable and validated through `AppConfig`.
- `AuthEventType.ACCESS_DENIED` exists, but centralized automatic emission for every denied `require()` was not added; denials raise safe `AuthorizationError` without noisy duplicate audit semantics.
- Target-hardware Argon2id benchmarking remains an acceptance check; no unsupported performance claim is made.
- Manual Windows visual/functional verification and owner acceptance are pending.
- Offline recovery for total Owner/Admin credential loss remains a documented manual procedure; there is no in-app backdoor, recovery key, email, or OTP flow.
- Proposed (`P`) and open (`O`) permissions, including Business Profile permission refinements, remain unapproved and untouched.
- A dedicated contract for suspending future data-surfacing background workers while locked should be enforced as those modules are added; current service-layer checks and application-modal lock prevent protected data access.

## 15. Manual Windows Verification Checklist

- [ ] Fresh install with no accounts shows first-run Owner/Admin setup before any business data.
- [ ] First-run validation enforces username rules, password policy, and confirmation mismatch.
- [ ] Login success works; wrong password, unknown username, and deactivated account all show the same generic message.
- [ ] Five failed attempts produce a 15-minute cooldown that survives application restart.
- [ ] Idle lock appears after the configured timeout, including while a modal dialog is open, and unlock requires the locked-in user's password.
- [ ] Lock-screen Esc/close cannot expose data; the explicit exit control ends the session and quits.
- [ ] Closing the main window while locked ends the session; the next launch requires login.
- [ ] Owner/Admin can create, rename/edit, activate/deactivate, assign roles to, and reset passwords for local users; the last active Owner/Admin is protected.
- [ ] Self-service password change requires the current password and enforces policy.
- [ ] Operator, Accountant/Reviewer, and Viewer UI controls are advisory-limited and direct service calls are denied.
- [ ] Restore, relocation, schedule/settings, and Business Profile save require the approved permission and record authenticated audit events.
- [ ] Native Windows smoke test exits `0` and logs `Main window shown` with isolated config/database paths.
- [ ] UI renders correctly at 100%, 125%, and 150% scaling in both themes.

## 16. Security Considerations

- Plaintext passwords are never persisted, logged, displayed, or audited; hashes are not exposed through account DTOs or dialogs.
- Argon2id is preferred with exact approved parameters; scrypt fallback uses an explicit safe `maxmem`; verification is constant-time and hashing fails closed.
- Generic authentication failures and per-username throttling reduce account enumeration and brute-force risk.
- The session is memory-only, idle-locks, and cannot be resumed after process exit or close-while-locked.
- Service-layer authorization is authoritative and re-evaluates live role/status; UI visibility is advisory only.
- Audit history remains append-only with authenticated or explicit `system/unauthenticated` actors and no mutation path.
- Only approved `A` permissions exist; `P`/`O` permissions and `audit.modify` are absent.
- Auth and audit services follow the live database through `DatabaseRuntime` after restore/relocation.
- Smoke mode does not seed a known credential and must not be run against the owner's configured database.
- Local Windows administrators and malware remain outside the application trust boundary; BitLocker/full-disk encryption is recommended separately.

## 17. Git Status and Confirmation

- **Branch:** `main`; **head:** `c84724b`; unchanged from before Phase 8B work.
- **No files staged** (`git diff --cached --name-only` was empty).
- **No commits created.**
- **No pushes performed.**
- **No Git history rewritten.**
- Worktree remains intentionally dirty with preserved pre-existing work plus Phase 8B changes. Owner review is required before any staging, commit, push, or shutdown action.

## 18. Owner Review and Acceptance Status

- **Status: ACCEPTED (owner-reviewed).**
- Owner personally tested the Windows application and formally accepted Phase 8B on **2026-11-23**.
- This acceptance records owner review; it does not alter historical automated test results or claim additional automated verification beyond what is recorded above. Phase 9 may proceed only after its own required owner-approved decisions are resolved.
